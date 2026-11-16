
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>
#include <math.h>
#include <ctype.h>

// =======================================
// SMART HVAC DEMO V5
// Arduino UNO R4 WiFi
// BME688 ONLY
// =======================================

// HARDWARE
const uint8_t RELAY_PIN = 10;
const uint8_t FAN_PIN = 9;

// Active-HIGH relay
const uint8_t RELAY_ON = HIGH;
const uint8_t RELAY_OFF = LOW;

// TIMING
const unsigned long HEAT_TIME_MS = 5000;
const unsigned long COOLDOWN_MS = 30000;
const unsigned long SENSOR_INTERVAL_MS = 2000;

// SAFETY LIMITS
const float MAX_TEMP_C = 40.0;
const float MIN_TEMP_C = -40.0;

// Atmospheric reference
const float SEA_LEVEL_HPA = 1013.25;

// Gas resistance baseline
const int GAS_BASELINE_SAMPLES = 20;

// =======================================
// BME688 SENSOR
// =======================================

Adafruit_BME680 bme688(&Wire);

bool sensorFound = false;
bool sensorValid = false;

uint8_t sensorAddress = 0;

// Sensor readings
float temperatureC = NAN;
float humidity = NAN;
float pressureHPA = NAN;
float gasKOhms = NAN;

// Gas baseline
float gasTotal = 0;
float gasBaseline = 0;

int gasCount = 0;
bool gasReady = false;

// =======================================
// SYSTEM STATE
// =======================================

bool heaterOn = false;
bool cooldownActive = false;
bool safetyLockout = false;

uint8_t fanPWM = 0;

unsigned long heaterStart = 0;
unsigned long cooldownStart = 0;
unsigned long lastSensorRead = 0;

const char* lockoutReason = "None";
const char* lastError = "None";

// =======================================
// RELAY CONTROL
// =======================================

void relayOff() {
  digitalWrite(RELAY_PIN, RELAY_OFF);
  heaterOn = false;
}

void relayOn() {
  digitalWrite(RELAY_PIN, RELAY_ON);
  heaterOn = true;
}

// =======================================
// FAN CONTROL
// =======================================

void setFan(uint8_t pwm) {
  fanPWM = pwm;
  analogWrite(FAN_PIN, pwm);
}

// =======================================
// HEATER SHUTDOWN
// =======================================

void stopHeater() {
  bool wasHeating = heaterOn;

  // Always command relay OFF
  relayOff();

  if (wasHeating) {
    cooldownActive = true;
    cooldownStart = millis();

    setFan(255);

    Serial.println();
    Serial.println("HEATER OFF");
    Serial.println("30-second fan cooldown started.");
  }
}

// =======================================
// SAFETY LOCKOUT
// =======================================

void emergencyStop(const char* reason) {
  stopHeater();
  relayOff();

  lastError = reason;

  if (!safetyLockout) {
    lockoutReason = reason;

    Serial.println();
    Serial.println("!!!!!!!!!!!!!!!!!!!!!!!!");
    Serial.println("     SAFETY LOCKOUT     ");
    Serial.println("!!!!!!!!!!!!!!!!!!!!!!!!");

    Serial.print("Reason: ");
    Serial.println(reason);
  }

  safetyLockout = true;

  // Continue airflow during lockout
  setFan(255);
}

// =======================================
// UNIT CONVERSIONS
// =======================================

float fahrenheit(float c) {
  return c * 1.8 + 32.0;
}

float dewPointC(float temp, float rh) {
  if (rh <= 0 || rh > 100) {
    return NAN;
  }

  const float a = 17.62;
  const float b = 243.12;

  float gamma =
    log(rh / 100.0) +
    (a * temp) / (b + temp);

  return (b * gamma) / (a - gamma);
}

float altitudeFeet(float pressure) {
  return 145366.45 *
    (1.0 - pow(pressure / SEA_LEVEL_HPA,
               0.190284));
}

// =======================================
// READ I2C CHIP ID
// =======================================

int readChipID(uint8_t address) {
  Wire.beginTransmission(address);
  Wire.write(0xD0);

  if (Wire.endTransmission(false) != 0) {
    return -1;
  }

  if (Wire.requestFrom(address, (uint8_t)1) != 1) {
    return -1;
  }

  return Wire.read();
}

// =======================================
// INITIALIZE BME688
// =======================================

void initializeSensor() {
  // Ensure heater is OFF during initialization
  relayOff();

  sensorFound = false;
  sensorValid = false;

  Serial.println();
  Serial.println("===== BME688 DETECTION =====");

  const uint8_t addresses[] = {0x76, 0x77};

  for (int i = 0; i < 2; i++) {
    uint8_t addr = addresses[i];

    int chipID = readChipID(addr);

    Serial.print("Address 0x");
    Serial.print(addr, HEX);
    Serial.print(": ");

    if (chipID < 0) {
      Serial.println("NO RESPONSE");
      continue;
    }

    Serial.print("Chip ID 0x");
    Serial.println(chipID, HEX);

    if (chipID == 0x61) {
      if (bme688.begin(addr)) {
        sensorFound = true;
        sensorAddress = addr;

        Serial.println("BME688 INITIALIZED");
        break;
      }
      else {
        Serial.println("INITIALIZATION FAILED");
      }
    }
    else {
      Serial.println("Not a BME688/BME680");
    }
    if (strncasecmp(line, "PING", 4) == 0) {
        Serial.print(F("{\"ack\":\"pong\",\"hb_seq\":"));
        Serial.print(heartbeat_seq);
        Serial.println(F("}"));
        return;
    }
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
            // BME280 internal 20-bit Sigma-Delta ADC register equivalent & A4/A5 I2C pipeline telemetry
            long adc_raw_20b = constrain((long)((last_temp_c + 40.0f) * 8388.6f), 0L, 1048575L);
            float v_sense_mv = (adc_raw_20b / 1048575.0f) * 3300.0f;
            Serial.print(F(",\"adc_raw_20b\":"));
            Serial.print(adc_raw_20b);
            Serial.print(F(",\"v_sense_mv\":"));
            Serial.print(v_sense_mv, 1);
            Serial.print(F(",\"i2c_pins\":\"A4_SDA_A5_SCL\""));
            Serial.print(F(",\"hb_seq\":"));
            Serial.print(++heartbeat_seq);
            Serial.println(F("}"));
            printMultimeterSummary(cm);
        }
    }
}
