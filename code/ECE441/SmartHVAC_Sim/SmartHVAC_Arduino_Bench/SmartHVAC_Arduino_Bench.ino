/*
 * ============================================================================
 * ECE 441 Smart HVAC Control - Official Arduino IDE Sketch (.ino)
 * ============================================================================
 * Designed for Andy Tran & Kaleb Cowgur (Arduino IDE -> Arduino Uno R4)
 *
 * Pinout (Matches 10-26-29 Hardware Pinout Report 1:1):
 *   - Pin 9 : IRLZ44N Logic-Level N-Channel MOSFET Gate (PWM Fan Control)
 *   - Pin 8 : 12V PTC Heating Element Relay Module (IN)
 *   - A4    : Bosch BME280 SDA
 *   - A5    : Bosch BME280 SCL
 *   - 5V    : Bosch BME280 VIN & Fan +5V Rail
 *   - GND   : Dedicated Arduino GND to BME280 GND (isolated from Fan return)
 *
 * Arduino IDE Serial Monitor Commands (Set baud rate to 115200):
 *   FAN <0-100> | PWM <0-255> | SET <15-30> | HEAT ON | HEAT OFF | AUTO
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#define DEVICE_ID               "ARDUINO-R4-HVAC-G2"
#define SERIAL_BAUD_RATE        115200

#define PIN_FAN_MOSFET          9
#define PIN_HEATER_RELAY        8
#define PIN_STATUS_LED          13

#define BME280_I2C_ADDR_PRIMARY 0x76
#define BME280_I2C_ADDR_ALT     0x77

#define DEFAULT_SETPOINT_C      23.0f
#define MIN_SETPOINT_C          15.0f
#define MAX_SETPOINT_C          30.0f
#define PID_KP                  45.0f
#define PID_KI                  0.5f
#define PID_KD                  10.0f

#define CONTROL_LOOP_MS         200
#define TELEMETRY_INTERVAL_MS   1000
#define BME_RETRY_INTERVAL_MS   3000
#define FAN_MIN_CIRCULATION_PWM 51

Adafruit_BME280 bme;
bool bme_online = false;
unsigned long last_retry_ms = 0;
float last_temp_c = 20.5f;
float last_rh_pct = 48.0f;
float last_press_hpa = 1013.25f;

// Self-contained PID state (zero extra PID library installation needed in Arduino IDE!)
float setpoint_c   = DEFAULT_SETPOINT_C;
float pid_integral = 0.0f;
float prev_error   = 0.0f;
float pid_output   = 0.0f;

int current_fan_pwm    = FAN_MIN_CIRCULATION_PWM;
int manual_fan_pwm     = -1; // -1 = AUTO (PID controlled), 0..255 = Manual override
int manual_heater_mode = -1; // -1 = AUTO (PID controlled), 0 = OFF, 1 = ON
bool heater_relay_on   = false;
long last_command_seq  = -1;

unsigned long last_control_ms   = 0;
unsigned long last_telemetry_ms = 0;
char serial_rx_buf[192];
uint8_t serial_rx_len = 0;

struct CircuitMetrics {
    float v_supply_12v, v_rail_5v, v_mosfet_gs, v_fan_eff;
    float i_mcu_a, i_fan_a, i_heater_a, i_total_load_a, i_12v_bus_a;
    float p_total_w, r_fan_branch_ohm, r_5v_rail_ohm, r_total_circuit_ohm;
};

static float calculateApparentTemp(float T, float RH, float V) {
    float e = (RH / 100.0f) * 6.105f * exp(17.27f * T / (237.7f + T));
    return T + (0.33f * e) - (0.70f * V) - 4.00f;
}

static bool extractJsonFloat(const char* json, const char* key, float& outVal) {
    char pattern[40];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char* pos = strstr(json, pattern);
    if (!pos) return false;
    pos = strchr(pos + strlen(pattern), ':');
    if (!pos) return false;
    pos++;
    while (*pos == ' ' || *pos == '\t') pos++;
    char* endPtr = nullptr;
    float v = (float)strtod(pos, &endPtr);
    if (endPtr == pos) return false;
    outVal = v;
    return true;
}

static CircuitMetrics computeCircuitMetrics(bool heat_on, int fan_pwm) {
    CircuitMetrics m;
    float duty = constrain(fan_pwm, 0, 255) / 255.0f;
    m.v_supply_12v = 12.00f;
    m.v_rail_5v    = 5.00f;
    m.v_mosfet_gs  = 5.00f * duty;

    const float R_FAN_WINDING = 14.286f;
    const float R_MOSFET_ON   = 0.028f;
    const float R_PTC_HEATER  = 2.880f;
    const float BUCK_EFF      = 0.88f;

    m.i_mcu_a = 0.045f;
    if (fan_pwm > 0) {
        float i_fan_peak = m.v_rail_5v / (R_FAN_WINDING + R_MOSFET_ON);
        m.i_fan_a = duty * i_fan_peak;
        m.v_fan_eff = duty * (m.v_rail_5v - (i_fan_peak * R_MOSFET_ON));
        m.r_fan_branch_ohm = m.v_rail_5v / m.i_fan_a;
    } else {
        m.i_fan_a = 0.0f;
        m.v_fan_eff = 0.0f;
        m.r_fan_branch_ohm = -1.0f;
    }

    m.i_heater_a = heat_on ? (m.v_supply_12v / R_PTC_HEATER) : 0.0f;
    float i_5v_total = m.i_mcu_a + m.i_fan_a;
    m.i_total_load_a = i_5v_total + m.i_heater_a;
    float p_5v = m.v_rail_5v * i_5v_total;
    m.p_total_w = p_5v + (m.v_supply_12v * m.i_heater_a);
    m.i_12v_bus_a = m.i_heater_a + (p_5v / (m.v_supply_12v * BUCK_EFF));
    m.r_5v_rail_ohm = m.v_rail_5v / i_5v_total;
    m.r_total_circuit_ohm = m.v_supply_12v / m.i_12v_bus_a;
    return m;
}

static void printMultimeterSummary(const CircuitMetrics &cm) {
    Serial.print(F("[MULTIMETER] Fan="));
    Serial.print((current_fan_pwm * 100.0f) / 255.0f, 0);
    Serial.print(F("% (PWM="));
    Serial.print(current_fan_pwm);
    Serial.print(F(", V_GS="));
    Serial.print(cm.v_mosfet_gs, 2);
    Serial.print(F("V, V_fan="));
    Serial.print(cm.v_fan_eff, 2);
    Serial.print(F("V) | I_fan="));
    Serial.print(cm.i_fan_a * 1000.0f, 0);
    Serial.print(F("mA | I_heat="));
    Serial.print(cm.i_heater_a, 2);
    Serial.print(F("A | I_total="));
    Serial.print(cm.i_total_load_a, 3);
    Serial.print(F("A (12V_bus="));
    Serial.print(cm.i_12v_bus_a, 3);
    Serial.print(F("A) | P="));
    Serial.print(cm.p_total_w, 2);
    Serial.print(F("W | R_fan="));
    if (cm.r_fan_branch_ohm > 0) {
        Serial.print(cm.r_fan_branch_ohm, 2);
        Serial.print(F(" Ohm"));
    } else {
        Serial.print(F("OPEN"));
    }
    Serial.print(F(" | R_5V="));
    Serial.print(cm.r_5v_rail_ohm, 2);
    Serial.print(F(" Ohm | R_total_circuit="));
    Serial.print(cm.r_total_circuit_ohm, 2);
    Serial.println(F(" Ohm"));
}

static void handleSerialCommand(const char* line) {
    if (strncasecmp(line, "AUTO", 4) == 0 || strstr(line, "\"auto\"")) {
        manual_fan_pwm = -1;
        manual_heater_mode = -1;
        Serial.println(F("{\"ack\":\"mode_auto\",\"status\":\"Closed-loop PID restored\"}"));
        return;
    }
    if (strncasecmp(line, "HEAT ON", 7) == 0) {
        manual_heater_mode = 1;
        heater_relay_on = true;
        digitalWrite(PIN_HEATER_RELAY, HIGH);
        Serial.println(F("{\"ack\":\"heater_forced_on\",\"relay_pin_8\":1}"));
        printMultimeterSummary(computeCircuitMetrics(heater_relay_on, current_fan_pwm));
        return;
    }
    if (strncasecmp(line, "HEAT OFF", 8) == 0) {
        manual_heater_mode = 0;
        heater_relay_on = false;
        digitalWrite(PIN_HEATER_RELAY, LOW);
        Serial.println(F("{\"ack\":\"heater_forced_off\",\"relay_pin_8\":0}"));
        printMultimeterSummary(computeCircuitMetrics(heater_relay_on, current_fan_pwm));
        return;
    }
    if (strncasecmp(line, "FAN ", 4) == 0) {
        float pct = constrain((float)strtod(line + 4, nullptr), 0.0f, 100.0f);
        manual_fan_pwm = (int)((pct / 100.0f) * 255.0f + 0.5f);
        current_fan_pwm = manual_fan_pwm;
        analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        Serial.print(F("{\"ack\":\"manual_fan_speed\",\"fan_speed_pct\":"));
        Serial.print(pct, 1);
        Serial.print(F(",\"fan_pwm\":"));
        Serial.print(manual_fan_pwm);
        Serial.println(F("}"));
        printMultimeterSummary(computeCircuitMetrics(heater_relay_on, current_fan_pwm));
        return;
    }
    if (strncasecmp(line, "PWM ", 4) == 0) {
        manual_fan_pwm = constrain((int)strtol(line + 4, nullptr, 10), 0, 255);
        current_fan_pwm = manual_fan_pwm;
        analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        Serial.print(F("{\"ack\":\"manual_fan_pwm\",\"fan_pwm\":"));
        Serial.print(manual_fan_pwm);
        Serial.println(F("}"));
        printMultimeterSummary(computeCircuitMetrics(heater_relay_on, current_fan_pwm));
        return;
    }
    if (strncasecmp(line, "SET ", 4) == 0) {
        float sp = (float)strtod(line + 4, nullptr);
        if (sp >= MIN_SETPOINT_C && sp <= MAX_SETPOINT_C) {
            setpoint_c = sp;
            Serial.print(F("{\"ack\":\"setpoint_updated\",\"setpoint_c\":"));
            Serial.print(setpoint_c, 2);
            Serial.println(F("}"));
        }
        return;
    }

    // JSON command parsing (from Raspberry Pi Edge Server / SerialEdgeBridge)
    float seqF = -1.0f;
    if (extractJsonFloat(line, "command_seq", seqF)) {
        long seq = (long)seqF;
        if (seq <= last_command_seq && last_command_seq >= 0) return;
        last_command_seq = seq;
    }

    float fanPct = -1.0f, fanPwmF = -1.0f;
    if (extractJsonFloat(line, "fan_speed", fanPct)) {
        if (fanPct < 0.0f) {
            manual_fan_pwm = -1;
        } else {
            fanPct = constrain(fanPct, 0.0f, 100.0f);
            manual_fan_pwm = (int)((fanPct / 100.0f) * 255.0f + 0.5f);
            current_fan_pwm = manual_fan_pwm;
            analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        }
    } else if (extractJsonFloat(line, "fan_pwm", fanPwmF)) {
        if (fanPwmF < 0.0f) {
            manual_fan_pwm = -1;
        } else {
            manual_fan_pwm = constrain((int)fanPwmF, 0, 255);
            current_fan_pwm = manual_fan_pwm;
            analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        }
    }

    float spC = 0.0f;
    if (extractJsonFloat(line, "setpoint_c", spC) || extractJsonFloat(line, "setpoint", spC)) {
        if (spC >= MIN_SETPOINT_C && spC <= MAX_SETPOINT_C) {
            setpoint_c = spC;
        }
    }
}

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    pinMode(PIN_FAN_MOSFET, OUTPUT);
    pinMode(PIN_HEATER_RELAY, OUTPUT);
    pinMode(PIN_STATUS_LED, OUTPUT);

    analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
    digitalWrite(PIN_HEATER_RELAY, LOW);
    digitalWrite(PIN_STATUS_LED, HIGH);

    Wire.begin();
    bme_online = bme.begin(BME280_I2C_ADDR_PRIMARY);
    if (!bme_online) bme_online = bme.begin(BME280_I2C_ADDR_ALT);

    Serial.println(F("================================================================================"));
    Serial.println(F("ECE 441 SMART HVAC BENCH CONTROLLER (Arduino Uno R4 + IRLZ44N MOSFET + BME280)"));
    Serial.println(F("Commands: FAN <0-100> | PWM <0-255> | SET <15-30> | HEAT ON | HEAT OFF | AUTO"));
    Serial.println(F("================================================================================"));
}

void loop() {
    while (Serial.available() > 0) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            if (serial_rx_len > 0) {
                serial_rx_buf[serial_rx_len] = '\0';
                handleSerialCommand(serial_rx_buf);
                serial_rx_len = 0;
            }
        } else if (serial_rx_len < sizeof(serial_rx_buf) - 1) {
            serial_rx_buf[serial_rx_len++] = c;
        }
    }

    unsigned long now = millis();
    if (now - last_control_ms >= CONTROL_LOOP_MS) {
        float dt = (now - last_control_ms) / 1000.0f;
        last_control_ms = now;

        if (!bme_online && (now - last_retry_ms >= BME_RETRY_INTERVAL_MS)) {
            last_retry_ms = now;
            bme_online = bme.begin(BME280_I2C_ADDR_PRIMARY) || bme.begin(BME280_I2C_ADDR_ALT);
        }
        if (bme_online) {
            float t = bme.readTemperature();
            float h = bme.readHumidity();
            float p = bme.readPressure() / 100.0f;
            if (!isnan(t) && t > -35.0f && t < 80.0f) {
                last_temp_c = t;
                if (!isnan(h)) last_rh_pct = h;
                if (!isnan(p)) last_press_hpa = p;
            } else {
                bme_online = false;
            }
        }

        float air_vel = (current_fan_pwm / 255.0f) * 7.0f;
        float feels_like_c = calculateApparentTemp(last_temp_c, last_rh_pct, air_vel);

        float err = setpoint_c - feels_like_c;
        pid_integral = constrain(pid_integral + (err * dt * PID_KI), 0.0f, 255.0f);
        float deriv = (dt > 0.0f) ? ((err - prev_error) / dt) : 0.0f;
        prev_error = err;
        pid_output = constrain((PID_KP * err) + pid_integral + (PID_KD * deriv), 0.0f, 255.0f);

        if (manual_heater_mode >= 0) {
            heater_relay_on = (manual_heater_mode == 1);
        } else {
            heater_relay_on = (pid_output >= 64.0f);
        }
        digitalWrite(PIN_HEATER_RELAY, heater_relay_on ? HIGH : LOW);

        if (manual_fan_pwm >= 0) {
            current_fan_pwm = manual_fan_pwm;
        } else {
            float cooling_deficit = feels_like_c - setpoint_c;
            if (cooling_deficit > 0.3f) {
                current_fan_pwm = (int)constrain(cooling_deficit * 85.0f, (float)FAN_MIN_CIRCULATION_PWM, 255.0f);
            } else {
                current_fan_pwm = max((int)FAN_MIN_CIRCULATION_PWM, (int)(pid_output * 0.85f));
            }
        }
        analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        digitalWrite(PIN_STATUS_LED, bme_online ? HIGH : LOW);

        if (now - last_telemetry_ms >= TELEMETRY_INTERVAL_MS) {
            last_telemetry_ms = now;
            CircuitMetrics cm = computeCircuitMetrics(heater_relay_on, current_fan_pwm);
            Serial.print(F("{\"device_id\":\"" DEVICE_ID "\",\"temp_c\":"));
            Serial.print(last_temp_c, 2);
            Serial.print(F(",\"humidity\":"));
            Serial.print(last_rh_pct, 1);
            Serial.print(F(",\"pressure_hpa\":"));
            Serial.print(last_press_hpa, 1);
            Serial.print(F(",\"feels_like_c\":"));
            Serial.print(feels_like_c, 2);
            Serial.print(F(",\"setpoint_c\":"));
            Serial.print(setpoint_c, 2);
            Serial.print(F(",\"fan_pwm\":"));
            Serial.print(current_fan_pwm);
            Serial.print(F(",\"fan_speed_pct\":"));
            Serial.print((current_fan_pwm * 100.0f) / 255.0f, 1);
            Serial.print(F(",\"fan_mode\":\""));
            Serial.print(manual_fan_pwm >= 0 ? F("MANUAL") : F("AUTO"));
            Serial.print(F("\",\"heater_relay\":"));
            Serial.print(heater_relay_on ? 1 : 0);
            Serial.print(F(",\"air_velocity_ms\":"));
            Serial.print(air_vel, 2);
            Serial.print(F(",\"v_supply_12v\":"));
            Serial.print(cm.v_supply_12v, 2);
            Serial.print(F(",\"v_rail_5v\":"));
            Serial.print(cm.v_rail_5v, 2);
            Serial.print(F(",\"v_mosfet_gs\":"));
            Serial.print(cm.v_mosfet_gs, 2);
            Serial.print(F(",\"v_fan_eff\":"));
            Serial.print(cm.v_fan_eff, 2);
            Serial.print(F(",\"i_fan_a\":"));
            Serial.print(cm.i_fan_a, 3);
            Serial.print(F(",\"i_heater_a\":"));
            Serial.print(cm.i_heater_a, 3);
            Serial.print(F(",\"i_total_a\":"));
            Serial.print(cm.i_total_load_a, 3);
            Serial.print(F(",\"i_12v_bus_a\":"));
            Serial.print(cm.i_12v_bus_a, 3);
            Serial.print(F(",\"power_w\":"));
            Serial.print(cm.p_total_w, 2);
            Serial.print(F(",\"r_fan_ohm\":"));
            Serial.print(cm.r_fan_branch_ohm, 2);
            Serial.print(F(",\"r_5v_rail_ohm\":"));
            Serial.print(cm.r_5v_rail_ohm, 2);
            Serial.print(F(",\"r_total_circuit_ohm\":"));
            Serial.print(cm.r_total_circuit_ohm, 2);
            Serial.print(F(",\"bme_ok\":"));
            Serial.print(bme_online ? 1 : 0);
            Serial.println(F("}"));
            printMultimeterSummary(cm);
        }
    }
}
