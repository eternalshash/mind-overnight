#include <Arduino.h>
#include <PID_v1.h>
#include "config.h"
#include "hal_sensors.h"
#include "thermal_comfort.h"

// ============================================================================
// ECE 441 Smart HVAC Control - Primary Arduino Uno / Uno R4 Firmware
// File: src/main.cpp
//
// Hardware Pinout (Aligned 1:1 with Andy Tran & Kaleb Cowgur's 10-26-29 Report):
//   - Pin 9 : IRLZ44N Logic-Level N-Channel MOSFET Gate (PWM Fan Control)
//   - Pin 8 : 12V PTC Heating Element Relay Trigger (IN)
//   - A4    : Bosch BME280 I2C SDA
//   - A5    : Bosch BME280 I2C SCL
//   - 5V    : Bosch BME280 VIN & 5V Fan Rail
//   - GND   : Dedicated Arduino GND to BME280 GND (isolated from Fan return)
//
// Serial Telemetry & Interactive Commands (115200 baud):
//   FAN <0-100> | PWM <0-255> | SET <15-30> | HEAT ON | HEAT OFF | AUTO
// ============================================================================

SensorHAL hal;

// Closed-Loop PID State
double Setpoint = DEFAULT_SETPOINT_C;
double Input    = 20.5;
double Output   = 0.0;
PID hvacPID(&Input, &Output, &Setpoint, PID_KP, PID_KI, PID_KD, DIRECT);

// Actuator & Telemetry State
int current_fan_pwm    = FAN_MIN_Circulation_PWM;
int manual_fan_pwm     = -1; // -1 = AUTO (PID controlled), 0..255 = Manual speed override
int manual_heater_mode = -1; // -1 = AUTO (PID controlled), 0 = Force OFF, 1 = Force ON
int current_heater_pwm = 0;
bool heater_relay_on   = false;
bool bme_sensor_ok     = false;
long last_command_seq  = -1;

unsigned long last_control_ms   = 0;
unsigned long last_telemetry_ms = 0;
char serial_rx_buf[192];
uint8_t serial_rx_len = 0;

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
        CircuitMetrics cm = hal.computeCircuitMetrics(heater_relay_on, current_fan_pwm);
        Serial.println(F("{\"ack\":\"heater_forced_on\",\"relay_pin_8\":1}"));
        printMultimeterSummary(cm);
        return;
    }
    if (strncasecmp(line, "HEAT OFF", 8) == 0) {
        manual_heater_mode = 0;
        heater_relay_on = false;
        digitalWrite(PIN_HEATER_RELAY, LOW);
        CircuitMetrics cm = hal.computeCircuitMetrics(heater_relay_on, current_fan_pwm);
        Serial.println(F("{\"ack\":\"heater_forced_off\",\"relay_pin_8\":0}"));
        printMultimeterSummary(cm);
        return;
    }
    if (strncasecmp(line, "FAN ", 4) == 0) {
        float pct = (float)strtod(line + 4, nullptr);
        pct = constrain(pct, 0.0f, 100.0f);
        manual_fan_pwm = (int)((pct / 100.0f) * 255.0f + 0.5f);
        current_fan_pwm = manual_fan_pwm;
        analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        CircuitMetrics cm = hal.computeCircuitMetrics(heater_relay_on, current_fan_pwm);
        Serial.print(F("{\"ack\":\"manual_fan_speed\",\"fan_speed_pct\":"));
        Serial.print(pct, 1);
        Serial.print(F(",\"fan_pwm\":"));
        Serial.print(manual_fan_pwm);
        Serial.println(F("}"));
        printMultimeterSummary(cm);
        return;
    }
    if (strncasecmp(line, "PWM ", 4) == 0) {
        int pwm = (int)strtol(line + 4, nullptr, 10);
        manual_fan_pwm = constrain(pwm, 0, 255);
        current_fan_pwm = manual_fan_pwm;
        analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        CircuitMetrics cm = hal.computeCircuitMetrics(heater_relay_on, current_fan_pwm);
        Serial.print(F("{\"ack\":\"manual_fan_pwm\",\"fan_pwm\":"));
        Serial.print(manual_fan_pwm);
        Serial.println(F("}"));
        printMultimeterSummary(cm);
        return;
    }
    if (strncasecmp(line, "SET ", 4) == 0) {
        float sp = (float)strtod(line + 4, nullptr);
        if (sp >= MIN_SETPOINT_C && sp <= MAX_SETPOINT_C) {
            Setpoint = (double)sp;
            Serial.print(F("{\"ack\":\"setpoint_updated\",\"setpoint_c\":"));
            Serial.print(Setpoint, 2);
            Serial.println(F("}"));
        }
        return;
    }

    float seqF = -1.0f;
    if (extractJsonFloat(line, "command_seq", seqF)) {
        long seq = (long)seqF;
        if (seq <= last_command_seq && last_command_seq >= 0) return;
        last_command_seq = seq;
    }

    float fanPct = -1.0f;
    float fanPwmF = -1.0f;
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
            Setpoint = (double)spC;
        }
    } else if (fanPct < 0.0f && fanPwmF < 0.0f) {
        char* endPtr = nullptr;
        float plainSp = (float)strtod(line, &endPtr);
        if (endPtr != line && plainSp >= MIN_SETPOINT_C && plainSp <= MAX_SETPOINT_C) {
            Setpoint = (double)plainSp;
        }
    }
}

static void pollSerialInput() {
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
}

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);

    pinMode(PIN_FAN_MOSFET, OUTPUT);
    pinMode(PIN_HEATER_RELAY, OUTPUT);
    pinMode(PIN_STATUS_LED, OUTPUT);

    analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
    digitalWrite(PIN_HEATER_RELAY, LOW);
    digitalWrite(PIN_STATUS_LED, HIGH);

    bme_sensor_ok = hal.init();

    hvacPID.SetMode(AUTOMATIC);
    hvacPID.SetOutputLimits(0, 255);
    hvacPID.SetSampleTime(CONTROL_LOOP_MS);

    Serial.println(F("================================================================================"));
    Serial.println(F("ECE 441 SMART HVAC BENCH CONTROLLER (Arduino Uno R4 + IRLZ44N MOSFET + BME280)"));
    Serial.println(F("Commands: FAN <0-100> | PWM <0-255> | SET <15-30> | HEAT ON | HEAT OFF | AUTO"));
    Serial.println(F("================================================================================"));
}

void loop() {
    pollSerialInput();

    unsigned long now = millis();
    if (now - last_control_ms >= CONTROL_LOOP_MS) {
        last_control_ms = now;

        float temp_c = 0.0f, rh_pct = 0.0f, press_hpa = 0.0f;
        hal.pollSensor(temp_c, rh_pct, press_hpa, bme_sensor_ok);

        float air_vel = hal.estimateAirVelocity(current_fan_pwm);
        float feels_like_c = ThermalComfort::calculateApparentTemp(temp_c, rh_pct, air_vel);

        Input = (double)feels_like_c;
        hvacPID.Compute();

        // Heater Relay control (12V PTC Element via Relay on Pin 8)
        current_heater_pwm = (int)Output;
        if (manual_heater_mode >= 0) {
            heater_relay_on = (manual_heater_mode == 1);
        } else {
            heater_relay_on = (current_heater_pwm >= 64);
        }
        digitalWrite(PIN_HEATER_RELAY, heater_relay_on ? HIGH : LOW);

        // IRLZ44N MOSFET PWM Fan Control on Pin 9
        if (manual_fan_pwm >= 0) {
            current_fan_pwm = manual_fan_pwm;
        } else {
            float cooling_deficit = feels_like_c - (float)Setpoint;
            if (cooling_deficit > 0.3f) {
                int cool_pwm = (int)constrain(cooling_deficit * 85.0f, (float)FAN_MIN_Circulation_PWM, 255.0f);
                current_fan_pwm = cool_pwm;
            } else {
                current_fan_pwm = max((int)FAN_MIN_Circulation_PWM, (int)(Output * 0.85));
            }
        }
        analogWrite(PIN_FAN_MOSFET, current_fan_pwm);
        digitalWrite(PIN_STATUS_LED, bme_sensor_ok ? HIGH : LOW);

        if (now - last_telemetry_ms >= TELEMETRY_INTERVAL_MS) {
            last_telemetry_ms = now;
            CircuitMetrics cm = hal.computeCircuitMetrics(heater_relay_on, current_fan_pwm);

            Serial.print(F("{\"device_id\":\"" DEVICE_ID "\",\"temp_c\":"));
            Serial.print(temp_c, 2);
            Serial.print(F(",\"humidity\":"));
            Serial.print(rh_pct, 1);
            Serial.print(F(",\"pressure_hpa\":"));
            Serial.print(press_hpa, 1);
            Serial.print(F(",\"feels_like_c\":"));
            Serial.print(feels_like_c, 2);
            Serial.print(F(",\"setpoint_c\":"));
            Serial.print(Setpoint, 2);
            Serial.print(F(",\"fan_pwm\":"));
            Serial.print(current_fan_pwm);
            Serial.print(F(",\"fan_speed_pct\":"));
            Serial.print((current_fan_pwm * 100.0f) / 255.0f, 1);
            Serial.print(F(",\"fan_mode\":\""));
            Serial.print(manual_fan_pwm >= 0 ? F("MANUAL") : F("AUTO"));
            Serial.print(F("\",\"heater_pwm\":"));
            Serial.print(current_heater_pwm);
            Serial.print(F(",\"heater_relay\":"));
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
            Serial.print(bme_sensor_ok ? 1 : 0);
            Serial.println(F("}"));

            printMultimeterSummary(cm);
        }
    }
}
