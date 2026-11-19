// =============================================================================
// ECE 441: SMART HVAC CONTROL — ALL-IN-ONE WIRELESS BENCH FIRMWARE (V6.0)
// Single-file standalone sketch for Arduino UNO R4 WiFi (ESP32-S3 Co-Processor)
// Includes:
//   - Embedded IIT-IoT Wi-Fi & HiveMQ Cloud credentials (Zero extra files needed)
//   - Direct TCP Port 1883 MQTT (Bridges directly to Web/Mobile WSS Port 8884)
//   - Unique MAC-based ClientID & LWT ("offline"/"online") on ece441/group2/hvac/status
//   - Closed-Loop Edge Autonomous Thermostat (Nest Dial Setpoint +/- 0.5C Deadband)
//   - Full Manual Bench Overrides (5, H, F, M, S, X, R, D, W, B + raw PWM slider)
//   - Injectable Faults Suite (heatwave, blower, sensor, mcu, clog, voc, smoke,
//     window, surge, wifi) with automatic state sync & reset
// =============================================================================

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>
#include <math.h>
#include <ctype.h>
#include <WiFiS3.h>
#include <ArduinoMqttClient.h>

// =======================================
// 1. EMBEDDED SECRETS (IIT-IoT & HiveMQ)
// =======================================
const char SECRET_SSID[]      = "IIT-IoT";
const char SECRET_PASS[]      = "XtAOhMfEQ7yeLeIVOSgHdv7bjNOxtqH7A1XjyzCpTsXRr";

// Port 1883 (TCP) on Arduino bridges directly to Port 8884 (WSS) on Web & Mobile
const char SECRET_BROKER[]    = "broker.hivemq.com";
const int  SECRET_PORT        = 1883;
const char SECRET_USER[]      = "";
const char SECRET_MQTT_PASS[] = "";

// Unique MAC-tied Client ID prevents public broker collisions
const char MQTT_CLIENT_ID[]   = "ece441-group2-uno-r4-70041DD4F668";

// MQTT Topics (Shared across Arduino, Web Digital Twin, and Mobile PWA)
const char TOPIC_TELEMETRY[]     = "ece441/group2/hvac/telemetry";
const char TOPIC_TELEMETRY_ALT[] = "ece441/hvac/telemetry";
const char TOPIC_COMMAND[]       = "ece441/group2/hvac/command";
const char TOPIC_COMMAND_ALT[]   = "ece441/hvac/command";
const char TOPIC_SETPOINT[]      = "ece441/group2/hvac/setpoint";
const char TOPIC_STATUS[]        = "ece441/group2/hvac/status";

// =======================================
// 2. HARDWARE PINOUT & TIMING
// =======================================
const uint8_t RELAY_PIN = 10;   // Active-HIGH Relay (12V PTC Heater)
const uint8_t FAN_PIN   = 9;    // PWM Gate (12V Blower Fan via IRLZ44N MOSFET)

const uint8_t RELAY_ON  = HIGH;
const uint8_t RELAY_OFF = LOW;

const unsigned long HEAT_TIME_MS           = 5000;   // Hard 5-second max heating pulse
const unsigned long COOLDOWN_MS            = 30000;  // Mandatory 30-second post-heat fan cooldown
const unsigned long SENSOR_INTERVAL_MS     = 2000;   // 2-second telemetry & closed-loop PID tick
const unsigned long WIFI_RETRY_INTERVAL_MS = 15000;
const unsigned long MQTT_RETRY_INTERVAL_MS = 5000;

// Safety & Hysteresis Limits
const float MAX_TEMP_C        = 40.0;
const float MIN_TEMP_C        = -40.0;
const float DEADBAND_C        = 0.5;     // +/- 0.5 C hysteresis deadband to prevent relay chatter
const float SEA_LEVEL_HPA     = 1013.25;
const int   GAS_BASELINE_SAMPLES = 20;

// =======================================
// 3. BME688 SENSOR & SYSTEM STATE
// =======================================
Adafruit_BME680 bme688(&Wire);

bool sensorFound = false;
bool sensorValid = false;
uint8_t sensorAddress = 0;

float temperatureC = 23.9; // Nominal room fallback if sensor unplugged
float humidity     = 35.0;
float pressureHPA  = 1004.3;
float gasKOhms     = 140.0;

float gasTotal    = 0;
float gasBaseline = 0;
int   gasCount    = 0;
bool  gasReady    = false;

// Actuators & Closed-Loop State
bool heaterOn          = false;
bool cooldownActive    = false;
bool safetyLockout     = false;
bool autoControlActive = true;  // True = Nest Dial Setpoint closed-loop; False = Manual bench override
uint8_t fanPWM         = 0;

float  targetSetpointC = 23.89; // Default 75.0 F (matches nominal room so bench starts quietly in IDLE)
String hvacMode        = "AUTO"; // AUTO, HEAT, COOL, ECO, OFF
String activeFault     = "none"; // none, heatwave, blower, sensor, mcu, clog, voc, smoke, window, surge, wifi

unsigned long heaterStart       = 0;
unsigned long cooldownStart     = 0;
unsigned long lastSensorRead    = 0;
unsigned long lastWifiAttempt   = 0;
unsigned long lastMqttAttempt   = 0;
unsigned long wifiSimDropUntil  = 0;

const char* lockoutReason = "None";
const char* lastError     = "None";
char lastCmdExecuted      = '-';

// Wireless Clients
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Forward Declarations
void executeCommand(char cmd, const char* source = "SERIAL");
void publishTelemetry();
void publishStatus(const char* st);
void onMqttMessageReceived(int messageSize);
void printWiFiStatus();
void runClosedLoopThermostat(unsigned long now);
void applyInjectedFault(const String& faultId, bool turnOn);

// =======================================
// 4. ACTUATOR CONTROL (RELAY & FAN)
// =======================================
void relayOff() {
  digitalWrite(RELAY_PIN, RELAY_OFF);
  heaterOn = false;
}

void relayOn() {
  digitalWrite(RELAY_PIN, RELAY_ON);
  heaterOn = true;
}

void setFan(uint8_t pwm) {
  if (activeFault == "blower") {
    pwm = 0; // Simulated blower motor stall interlock
  }
  fanPWM = pwm;
  analogWrite(FAN_PIN, pwm);
}

void stopHeater() {
  bool wasHeating = heaterOn;
  relayOff();

  if (wasHeating) {
    cooldownActive = true;
    cooldownStart = millis();
    if (activeFault != "blower") {
      setFan(255);
    }

    Serial.println();
    Serial.println("HEATER OFF");
    Serial.println("30-second fan cooldown started.");
    publishTelemetry();
  }
}

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
  if (activeFault == "blower") {
    setFan(0);
  } else {
    setFan(255); // Keep fan cooling at 100% during thermal/MCU lockout
  }
  publishTelemetry();
}

// =======================================
// 5. THERMODYNAMIC & POWER CALCULATIONS
// =======================================
float fahrenheit(float c) {
  return c * 1.8 + 32.0;
}

float dewPointC(float temp, float rh) {
  if (rh <= 0 || rh > 100) return NAN;
  const float a = 17.62, b = 243.12;
  float gamma = log(rh / 100.0) + (a * temp) / (b + temp);
  return (b * gamma) / (a - gamma);
}

float altitudeFeet(float pressure) {
  return 145366.45 * (1.0 - pow(pressure / SEA_LEVEL_HPA, 0.190284));
}

float apparentTempC(float t_c, float rh, float vel_ms) {
  if (isnan(t_c) || isnan(rh)) return 22.0;
  float e_hpa = (rh / 100.0) * 6.105 * exp((17.27 * t_c) / (237.7 + t_c));
  return t_c + 0.33 * e_hpa - 0.70 * (0.05 + 0.06 * vel_ms) - 4.0;
}

float calculateCircuitPower(uint8_t fan_pwm, bool htr_on) {
  float duty = fan_pwm / 255.0;
  float i_fan = duty * (5.0 / (14.286 + 0.028));
  float i_htr = htr_on ? (12.0 / 2.880) : 0.0;
  return 5.0 * (0.045 + i_fan) + 12.0 * i_htr;
}

// =======================================
// 6. BME688 SENSOR DRIVER
// =======================================
int readChipID(uint8_t address) {
  Wire.beginTransmission(address);
  Wire.write(0xD0);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(address, (uint8_t)1) != 1) return -1;
  return Wire.read();
}

void initializeSensor() {
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
      } else {
        Serial.println("INITIALIZATION FAILED");
      }
    } else {
      Serial.println("Not a BME688/BME680");
    }
  }

  if (sensorFound) {
    bme688.setTemperatureOversampling(BME680_OS_8X);
    bme688.setHumidityOversampling(BME680_OS_2X);
    bme688.setPressureOversampling(BME680_OS_4X);
    bme688.setIIRFilterSize(BME680_FILTER_SIZE_3);
    bme688.setGasHeater(320, 150);

    Serial.print("Sensor ready at 0x");
    Serial.println(sensorAddress, HEX);
  } else {
    Serial.println("WARNING: BME688 not detected on I2C. Fan & 5s Relay testing remain enabled.");
    lastError = "BME688 not detected";
  }

  Serial.println("============================");
}

void resetGasBaseline() {
  gasTotal = 0;
  gasBaseline = 0;
  gasCount = 0;
  gasReady = false;
  Serial.println("Gas baseline reset.");
}

void updateGasBaseline() {
  if (gasReady || !isfinite(gasKOhms) || gasKOhms <= 0) return;
  gasTotal += gasKOhms;
  gasCount++;
  if (gasCount >= GAS_BASELINE_SAMPLES) {
    gasBaseline = gasTotal / gasCount;
    gasReady = true;
    Serial.println("Gas baseline established.");
  }
}

const char* validateSensor() {
  if (!sensorFound) return "BME688 missing";
  if (!isfinite(temperatureC) || temperatureC < MIN_TEMP_C || temperatureC > 85.0) return "Invalid BME688 temperature";
  if (!isfinite(humidity) || humidity < 0 || humidity > 100) return "Invalid BME688 humidity";
  if (!isfinite(pressureHPA) || pressureHPA < 300 || pressureHPA > 1100) return "Invalid BME688 pressure";
  if (temperatureC >= MAX_TEMP_C) return "BME688 overtemperature";
  return NULL;
}

void readSensor() {
  if (!sensorFound) {
    sensorValid = false;
    return;
  }

  if (!bme688.performReading()) {
    sensorValid = false;
    emergencyStop("BME688 reading failed");
    return;
  }

  temperatureC = bme688.temperature;
  humidity     = bme688.humidity;
  pressureHPA  = bme688.pressure / 100.0;
  gasKOhms     = bme688.gas_resistance / 1000.0;

  const char* error = validateSensor();
  if (error != NULL) {
    sensorValid = false;
    emergencyStop(error);
    return;
  }

  sensorValid = true;
  lastError = "None";
  updateGasBaseline();
}

// =======================================
// 7. CLOSED-LOOP EDGE THERMOSTAT & FAULTS
// =======================================
void startHeaterTest() {
  if (safetyLockout || cooldownActive || heaterOn || activeFault == "blower" || activeFault == "window") {
    Serial.println("HEATER TEST DENIED");
    if (safetyLockout) {
      Serial.print("Lockout Reason: ");
      Serial.println(lockoutReason);
    } else if (cooldownActive) {
      Serial.println("Reason: 30-second cooldown is still active (send R to clear cooldown).");
    }
    return;
  }

  if (sensorFound) {
    readSensor();
    if (safetyLockout || !sensorValid) {
      Serial.println("HEATER TEST DENIED: Unsafe sensor reading.");
      return;
    }
  }

  setFan(255);
  heaterStart = millis();
  relayOn();

  Serial.println();
  Serial.println("HEATER ON (Pin 10 HIGH)");
  Serial.println("5-second heating pulse active.");
  Serial.println("Fan at 100% (Pin 9 PWM = 255).");
  publishTelemetry();
}

void runClosedLoopThermostat(unsigned long now) {
  // 1. Non-negotiable safety lockouts always win
  if (safetyLockout) {
    relayOff();
    if (activeFault == "blower") setFan(0);
    else setFan(255);
    return;
  }

  // 2. Active fault overrides
  if (activeFault == "blower") {
    relayOff();
    setFan(0);
    return;
  }
  if (activeFault == "window") {
    if (heaterOn) stopHeater();
    if (!cooldownActive) setFan(0);
    return;
  }
  if (activeFault == "heatwave" || activeFault == "surge") {
    if (heaterOn) stopHeater();
    setFan(255);
    return;
  }
  if (activeFault == "smoke") {
    if (heaterOn) stopHeater();
    if (!cooldownActive) setFan(128);
    return;
  }
  if (activeFault == "clog" || activeFault == "voc") {
    if (!heaterOn && !cooldownActive) setFan(255);
    return;
  }

  // 3. System OFF mode
  if (hvacMode == "OFF") {
    if (heaterOn) stopHeater();
    if (!cooldownActive) setFan(0);
    return;
  }

  // 4. Respect manual bench button overrides until user adjusts Nest dial, mode, or hits Reset (R)
  if (!autoControlActive) {
    return;
  }

  // 5. Closed-loop comparison: Real BME688 Temp vs Target Setpoint (+/- 0.5 C hysteresis deadband)
  float effSpC = targetSetpointC + (hvacMode == "ECO" ? 1.1 : 0.0);
  float errC = temperatureC - effSpC; // > 0 means room is too warm (COOL); < 0 means room is too cold (HEAT)

  // Force HEAT or Setpoint above Room Temp + Deadband
  bool shouldHeat = (hvacMode == "HEAT" && errC < 0.2) ||
                    ((hvacMode == "AUTO" || hvacMode == "ECO") && errC < -DEADBAND_C);

  // Force COOL or Setpoint below Room Temp - Deadband
  bool shouldCool = (hvacMode == "COOL" && errC > -0.2) ||
                    ((hvacMode == "AUTO" || hvacMode == "ECO") && errC > DEADBAND_C);

  if (shouldHeat) {
    // Engage safe 5s duty-cycled heating pulse if not currently in post-heat cooldown
    if (!heaterOn && !cooldownActive) {
      startHeaterTest();
    } else if (cooldownActive) {
      setFan(255); // Continue circulating warm air during 30s inter-pulse cooldown
    }
  } else if (shouldCool) {
    if (heaterOn) {
      stopHeater();
    }
    if (!cooldownActive) {
      // Proportional PWM fan modulation based on thermal error
      uint8_t targetPwm = 0;
      if (hvacMode == "COOL" && errC <= DEADBAND_C) {
        targetPwm = 190; // Force cooling baseline (75%)
      } else {
        // Scale smoothly from PWM 110 (43%) at 0.5C error up to PWM 255 (100%) at >= 2.5C error
        int scaled = 110 + (int)((max(0.0f, errC - DEADBAND_C)) * 72.0f);
        if (hvacMode == "ECO") scaled = min(scaled, 178); // Eco cap at 70%
        targetPwm = (uint8_t)constrain(scaled, 110, 255);
      }
      if (fanPWM != targetPwm) {
        setFan(targetPwm);
      }
    }
  } else {
    // Within +/- 0.5 C Deadband -> IDLE
    if (heaterOn) {
      stopHeater();
    }
    if (!cooldownActive && fanPWM != 0) {
      setFan(0);
    }
  }
}

void applyInjectedFault(const String& faultId, bool turnOn) {
  if (!turnOn || faultId == "none" || faultId == "clear") {
    activeFault = "none";
    wifiSimDropUntil = 0;
    if (safetyLockout) {
      safetyLockout = false;
      lockoutReason = "None";
    }
    autoControlActive = true;
    runClosedLoopThermostat(millis());
    Serial.println("[FAULT CLEARED] Restored nominal closed-loop operation.");
    publishTelemetry();
    return;
  }

  activeFault = faultId;
  Serial.print("[FAULT INJECTED]: ");
  Serial.println(activeFault);

  if (faultId == "blower") {
    emergencyStop("Blower motor failure (0 RPM)");
    setFan(0);
  } else if (faultId == "mcu" || faultId == "stuck_relay") {
    emergencyStop("Primary MCU / Stuck Relay Interlock");
  } else if (faultId == "heatwave" || faultId == "surge") {
    if (heaterOn) stopHeater();
    setFan(255);
  } else if (faultId == "clog" || faultId == "voc") {
    setFan(255);
  } else if (faultId == "smoke") {
    if (heaterOn) stopHeater();
    setFan(128);
  } else if (faultId == "window") {
    if (heaterOn) stopHeater();
    setFan(0);
  } else if (faultId == "wifi") {
    wifiSimDropUntil = millis() + 7000;
    Serial.println("[FAULT] Simulating 7-second cloud link dropout (Edge autonomy active)...");
  }
  publishTelemetry();
}

void resetSafety() {
  relayOff();
  Serial.println("Attempting safety reset...");

  cooldownActive = false;
  safetyLockout = false;
  lockoutReason = "None";
  activeFault = "none";
  wifiSimDropUntil = 0;
  autoControlActive = true;

  initializeSensor();
  if (sensorFound) {
    readSensor();
  }

  setFan(0);
  runClosedLoopThermostat(millis());

  Serial.println("SAFETY RESET SUCCESSFUL");
  publishTelemetry();
}

// =======================================
// 8. TELEMETRY DISPLAY & DIAGNOSTICS
// =======================================
void printSensorData() {
  float fanPct = fanPWM * 100.0 / 255.0;
  float airVel = (fanPct / 100.0) * 3.4;
  float powerW = calculateCircuitPower(fanPWM, heaterOn);

  Serial.println("================================");
  Serial.println("       SMART HVAC DEMO V6       ");
  Serial.println("================================");
  Serial.println("[BME688]");
  Serial.print("Temperature: ");
  Serial.print(fahrenheit(temperatureC), 2);
  Serial.print(" F / ");
  Serial.print(temperatureC, 2);
  Serial.println(" C");
  Serial.print("Setpoint:    ");
  Serial.print(fahrenheit(targetSetpointC), 1);
  Serial.print(" F / ");
  Serial.print(targetSetpointC, 2);
  Serial.print(" C (Mode: ");
  Serial.print(hvacMode);
  Serial.println(")");
  Serial.print("Humidity: ");
  Serial.print(humidity, 1);
  Serial.println(" % RH");
  Serial.print("Pressure: ");
  Serial.print(pressureHPA, 2);
  Serial.println(" hPa");
  Serial.print("Gas resistance: ");
  Serial.print(gasKOhms, 2);
  Serial.println(" kOhms");
  Serial.println("[HVAC SYSTEM]");
  Serial.print("Heater: ");
  Serial.println(heaterOn ? "ON" : "OFF");
  Serial.print("Fan PWM: ");
  Serial.print(fanPct, 0);
  Serial.println("%");
  Serial.print("Power: ");
  Serial.print(powerW, 2);
  Serial.println(" W");
  Serial.print("Cooldown: ");
  Serial.println(cooldownActive ? "ACTIVE" : "OFF");
  Serial.print("Safety lockout: ");
  Serial.println(safetyLockout ? "ACTIVE" : "CLEAR");
  Serial.print("Active fault: ");
  Serial.println(activeFault);
  Serial.print("Wi-Fi / MQTT: ");
  Serial.print(WiFi.status() == WL_CONNECTED ? "WIFI OK" : "WIFI DOWN");
  Serial.print(" / ");
  Serial.println(mqttClient.connected() ? "MQTT OK" : "MQTT DOWN");
  Serial.println("================================");
}

void printWiFiStatus() {
  Serial.println();
  Serial.println("===== WI-FI & MQTT STATUS =====");
  byte mac[6];
  WiFi.macAddress(mac);
  Serial.print("MAC Address: ");
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 0x10) Serial.print("0");
    Serial.print(mac[i], HEX);
    if (i < 5) Serial.print(":");
  }
  Serial.println();
  Serial.print("SSID:        "); Serial.println(WiFi.SSID());
  Serial.print("Wi-Fi State: "); Serial.println(WiFi.status() == WL_CONNECTED ? "CONNECTED" : "DISCONNECTED");
  Serial.print("IP Address:  "); Serial.println(WiFi.localIP());
  Serial.print("Gateway IP:  "); Serial.println(WiFi.gatewayIP());
  Serial.print("Signal RSSI: "); Serial.print(WiFi.RSSI()); Serial.println(" dBm");
  Serial.print("MQTT Broker: "); Serial.print(SECRET_BROKER); Serial.print(":"); Serial.println(SECRET_PORT);
  Serial.print("MQTT Client: "); Serial.println(MQTT_CLIENT_ID);
  Serial.print("MQTT State:  "); Serial.println(mqttClient.connected() ? "CONNECTED" : "DISCONNECTED");
  Serial.println("===============================");
}

void printDiagnostics() {
  Serial.println();
  Serial.println("===== SYSTEM DIAGNOSTICS =====");
  Serial.print("Sensor detected:   "); Serial.println(sensorFound ? "YES" : "NO");
  Serial.print("Sensor address:    0x"); Serial.println(sensorAddress, HEX);
  Serial.print("Sensor data valid: "); Serial.println(sensorValid ? "YES" : "NO");
  Serial.print("Last error:        "); Serial.println(lastError);
  Serial.print("Control Mode:      "); Serial.print(hvacMode); Serial.println(autoControlActive ? " (CLOSED-LOOP)" : " (MANUAL OVERRIDE)");
  Serial.print("Setpoint:          "); Serial.print(targetSetpointC, 2); Serial.print(" C ("); Serial.print(fahrenheit(targetSetpointC), 1); Serial.println(" F)");
  Serial.print("Heater Relay (10): "); Serial.println(heaterOn ? "ON (HIGH)" : "OFF (LOW)");
  Serial.print("Fan PWM (Pin 9):   "); Serial.print(fanPWM); Serial.print(" ("); Serial.print(fanPWM * 100.0 / 255.0, 0); Serial.println("%)");
  Serial.print("Cooldown Active:   "); Serial.println(cooldownActive ? "ACTIVE" : "OFF");
  Serial.print("Safety Lockout:    "); Serial.println(safetyLockout ? "ACTIVE" : "CLEAR");
  Serial.print("Lockout Reason:    "); Serial.println(lockoutReason);
  Serial.print("Active Fault:      "); Serial.println(activeFault);
  printWiFiStatus();
}

// =======================================
// 9. UNIFIED COMMAND HANDLER (SERIAL + MQTT + SIM)
// =======================================
void printMenu() {
  Serial.println();
  Serial.println("====== SMART HVAC COMMANDS ======");
  Serial.println("5 = Heater ON for 5 seconds + Fan 100%");
  Serial.println("H = Stop heater immediately");
  Serial.println("F = Fan ON 100% (Pin 9 PWM = 255)");
  Serial.println("M = Fan ON 50%  (Pin 9 PWM = 128)");
  Serial.println("S = Fan OFF     (Pin 9 PWM = 0)");
  Serial.println("W = Check Wi-Fi & MQTT connection status");
  Serial.println("X = Emergency software stop / Lockout");
  Serial.println("R = Reset safety lockout / Restore Auto PID");
  Serial.println("D = Full system diagnostics");
  Serial.println("B = Reset gas baseline");
  Serial.println("? = Show menu");
  Serial.println("=================================");
}

void executeCommand(char cmd, const char* source) {
  cmd = toupper(cmd);
  if (cmd == '\r' || cmd == '\n' || cmd == ' ') return;

  lastCmdExecuted = cmd;
  Serial.print("[COMMAND via ");
  Serial.print(source);
  Serial.print("]: ");
  Serial.println(cmd);

  switch (cmd) {
    case '5':
      autoControlActive = false;
      startHeaterTest();
      break;

    case 'H':
      autoControlActive = false;
      stopHeater();
      publishTelemetry();
      break;

    case 'F':
      autoControlActive = false;
      setFan(255);
      Serial.println("Fan ON 100% (Pin 9 PWM = 255)");
      publishTelemetry();
      break;

    case 'M':
      if (!heaterOn) {
        autoControlActive = false;
        setFan(128);
        Serial.println("Fan ON 50% (Pin 9 PWM = 128)");
        publishTelemetry();
      } else {
        Serial.println("Fan change denied while heater is active");
      }
      break;

    case 'S':
      if (!heaterOn) {
        autoControlActive = false;
        cooldownActive = false;
        setFan(0);
        Serial.println("Fan OFF (Pin 9 PWM = 0)");
        publishTelemetry();
      } else {
        Serial.println("Fan OFF denied while heater is ON");
      }
      break;

    case 'W':
      printWiFiStatus();
      publishTelemetry();
      break;

    case 'X':
      autoControlActive = false;
      emergencyStop("Manual emergency stop");
      break;

    case 'R':
      resetSafety();
      break;

    case 'D':
      printDiagnostics();
      publishTelemetry();
      break;

    case 'B':
      resetGasBaseline();
      publishTelemetry();
      break;

    case '?':
      printMenu();
      break;

    default:
      Serial.print("Unrecognized command: ");
      Serial.println(cmd);
      break;
  }
}

// =======================================
// 10. WI-FI & HIVEMQ CLOUD INTEGRATION
// =======================================
void connectWiFi(bool waitOnBoot = false) {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println();
  Serial.print("[WIFI] Connecting to SSID: ");
  Serial.println(SECRET_SSID);

  WiFi.begin(SECRET_SSID, SECRET_PASS);

  if (waitOnBoot) {
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 12000) {
      delay(300);
      Serial.print(".");
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    }
    Serial.println();
  }

  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.println("[WIFI] Connected to IIT-IoT!");
    Serial.print("[WIFI] IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WIFI] Signal (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else if (waitOnBoot) {
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("[WIFI] Still connecting in background...");
  }
}

void publishStatus(const char* st) {
  if (!mqttClient.connected()) return;
  mqttClient.beginMessage(TOPIC_STATUS, (unsigned long)strlen(st), true, 0, false);
  mqttClient.print(st);
  mqttClient.endMessage();
}

void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) return;

  Serial.print("[MQTT] Connecting to HiveMQ (");
  Serial.print(SECRET_BROKER);
  Serial.print(":");
  Serial.print(SECRET_PORT);
  Serial.println(")...");

  mqttClient.setId(MQTT_CLIENT_ID);
  if (strlen(SECRET_USER) > 0) {
    mqttClient.setUsernamePassword(SECRET_USER, SECRET_MQTT_PASS);
  }
  mqttClient.setKeepAliveInterval(30 * 1000);

  // Configure Last Will and Testament (LWT) so Web/Mobile detect unexpected power-off
  mqttClient.beginWill(TOPIC_STATUS, 7, true, 0);
  mqttClient.print("offline");
  mqttClient.endWill();

  if (!mqttClient.connect(SECRET_BROKER, SECRET_PORT)) {
    Serial.print("[MQTT] Connection failed! Error code = ");
    Serial.println(mqttClient.connectError());
    return;
  }

  Serial.println("[MQTT] SUCCESS! Connected to HiveMQ Broker!");
  mqttClient.onMessage(onMqttMessageReceived);
  mqttClient.subscribe(TOPIC_COMMAND);
  mqttClient.subscribe(TOPIC_COMMAND_ALT);
  mqttClient.subscribe(TOPIC_SETPOINT);

  publishStatus("online");
  publishTelemetry();
}

// Helper to extract JSON string field value
String extractJsonString(const String& json, const char* key) {
  String k = String("\"") + key + "\"";
  int idx = json.indexOf(k);
  if (idx < 0) return "";
  int colon = json.indexOf(':', idx + k.length());
  if (colon < 0) return "";
  int q1 = json.indexOf('\"', colon + 1);
  if (q1 < 0) return "";
  int q2 = json.indexOf('\"', q1 + 1);
  if (q2 < 0) return "";
  return json.substring(q1 + 1, q2);
}

// Helper to extract JSON numeric field value
float extractJsonFloat(const String& json, const char* key, float defaultVal = NAN) {
  String k = String("\"") + key + "\"";
  int idx = json.indexOf(k);
  if (idx < 0) return defaultVal;
  int colon = json.indexOf(':', idx + k.length());
  if (colon < 0) return defaultVal;
  int start = colon + 1;
  while (start < (int)json.length() && (json.charAt(start) == ' ' || json.charAt(start) == '\"')) start++;
  int end = start;
  while (end < (int)json.length() && (isdigit(json.charAt(end)) || json.charAt(end) == '.' || json.charAt(end) == '-')) end++;
  if (end <= start) return defaultVal;
  return json.substring(start, end).toFloat();
}

void onMqttMessageReceived(int messageSize) {
  String topic = mqttClient.messageTopic();
  String payload = "";
  while (mqttClient.available()) {
    payload += (char)mqttClient.read();
  }
  payload.trim();

  Serial.println();
  Serial.print("[MQTT RECEIVED] Topic: ");
  Serial.print(topic);
  Serial.print(" | Message: ");
  Serial.println(payload);

  if (payload.length() == 0) return;

  // 1. Direct single-letter command (e.g. "5", "F", "M", "S", "H", "W", "X", "R", "D", "B")
  if (payload.length() == 1 && !isdigit(payload.charAt(0))) {
    executeCommand(payload.charAt(0), "MQTT");
    return;
  }
  if (payload == "5") {
    executeCommand('5', "MQTT");
    return;
  }

  // 2. Fault injection command: {"fault":"blower","on":1} or {"fault":"clear"}
  String faultId = extractJsonString(payload, "fault");
  if (faultId.length() > 0) {
    float onVal = extractJsonFloat(payload, "on", 1.0);
    bool isTrue = payload.indexOf(":true") >= 0 || onVal > 0.5;
    if (faultId == "none" || faultId == "clear") isTrue = false;
    applyInjectedFault(faultId, isTrue);
    return;
  }

  // 3. Setpoint and/or Mode update from Web or Mobile Nest Turntable:
  //    e.g. {"setpoint_c":24.4,"mode":"HEAT"} or {"sp_f":76} or raw float on TOPIC_SETPOINT
  bool updatedSetpointOrMode = false;

  String modeStr = extractJsonString(payload, "mode");
  if (modeStr.length() > 0) {
    modeStr.toUpperCase();
    if (modeStr == "AUTO" || modeStr == "HEAT" || modeStr == "COOL" || modeStr == "ECO" || modeStr == "OFF") {
      hvacMode = modeStr;
      autoControlActive = true;
      updatedSetpointOrMode = true;
      Serial.print("[MQTT-NEST] HVAC Mode set to: ");
      Serial.println(hvacMode);
    }
  }

  float spC = extractJsonFloat(payload, "setpoint_c");
  if (isnan(spC)) spC = extractJsonFloat(payload, "setpoint");
  if (isnan(spC)) {
    float spF = extractJsonFloat(payload, "setpoint_f");
    if (isnan(spF)) spF = extractJsonFloat(payload, "sp_f");
    if (!isnan(spF) && spF >= 50.0 && spF <= 95.0) {
      spC = (spF - 32.0) * 5.0 / 9.0;
    }
  }
  if (isnan(spC) && topic == TOPIC_SETPOINT && payload.charAt(0) != '{') {
    float rawVal = payload.toFloat();
    if (rawVal >= 50.0 && rawVal <= 95.0) spC = (rawVal - 32.0) * 5.0 / 9.0;
    else if (rawVal >= 10.0 && rawVal <= 35.0) spC = rawVal;
  }

  if (!isnan(spC) && spC >= 10.0 && spC <= 35.0) {
    targetSetpointC = spC;
    autoControlActive = true;
    updatedSetpointOrMode = true;
    Serial.print("[MQTT-NEST] Target Setpoint updated to: ");
    Serial.print(targetSetpointC, 2);
    Serial.print(" C (");
    Serial.print(fahrenheit(targetSetpointC), 1);
    Serial.println(" F)");
  }

  // 4. Direct Fan PWM slider override: {"fan_pwm": 180} or {"fan_pct": 70}
  float fanPwmVal = extractJsonFloat(payload, "fan_pwm");
  if (isnan(fanPwmVal)) {
    float fanPctVal = extractJsonFloat(payload, "fan_pct");
    if (!isnan(fanPctVal)) {
      if (fanPctVal < 0) {
        autoControlActive = true;
        updatedSetpointOrMode = true;
      } else {
        fanPwmVal = (fanPctVal / 100.0) * 255.0;
      }
    }
  }
  if (!isnan(fanPwmVal) && fanPwmVal >= 0) {
    uint8_t pwm = (uint8_t)constrain((int)round(fanPwmVal), 0, 255);
    autoControlActive = false;
    setFan(pwm);
    Serial.print("[MQTT-SIM] Manual Fan PWM set to: ");
    Serial.println(pwm);
    publishTelemetry();
    return;
  }

  if (updatedSetpointOrMode) {
    runClosedLoopThermostat(millis());
    publishTelemetry();
    return;
  }

  // 5. Explicit single-char command inside JSON: {"cmd":"F"} or {"command":"5"}
  String cmdStr = extractJsonString(payload, "cmd");
  if (cmdStr.length() == 0) cmdStr = extractJsonString(payload, "command");
  if (cmdStr.length() > 0) {
    executeCommand(cmdStr.charAt(0), "MQTT-JSON");
  }
}

void publishTelemetry() {
  if (!mqttClient.connected()) return;
  if (wifiSimDropUntil > 0 && millis() < wifiSimDropUntil) return; // Simulated Wi-Fi fault window

  float fanPct = fanPWM * 100.0 / 255.0;
  float airVel = (fanPct / 100.0) * 3.4;
  float feelsC = apparentTempC(temperatureC, humidity, airVel);
  float powerW = calculateCircuitPower(fanPWM, heaterOn);

  // Compact JSON payload (< 238 bytes) containing all 17 telemetry & state fields
  String json = "{";
  json += "\"temp_c\":" + String(temperatureC, 2) + ",";
  json += "\"temp_f\":" + String(fahrenheit(temperatureC), 1) + ",";
  json += "\"humidity\":" + String(humidity, 1) + ",";
  json += "\"pressure_hpa\":" + String(pressureHPA, 1) + ",";
  json += "\"gas_kohms\":" + String(gasKOhms, 1) + ",";
  json += "\"feels_like_c\":" + String(feelsC, 2) + ",";
  json += "\"air_vel_ms\":" + String(airVel, 2) + ",";
  json += "\"heater_relay\":" + String(heaterOn ? 1 : 0) + ",";
  json += "\"fan_pwm\":" + String(fanPWM) + ",";
  json += "\"fan_speed_pct\":" + String((int)round(fanPct)) + ",";
  json += "\"power_w\":" + String(powerW, 2) + ",";
  json += "\"setpoint_c\":" + String(targetSetpointC, 2) + ",";
  json += "\"mode\":\"" + hvacMode + "\",";
  json += "\"cooldown\":" + String(cooldownActive ? 1 : 0) + ",";
  json += "\"lockout\":" + String(safetyLockout ? 1 : 0) + ",";
  json += "\"fault\":\"" + activeFault + "\",";
  json += "\"last_cmd\":\"" + String(lastCmdExecuted) + "\",";
  json += "\"rssi\":" + String(WiFi.RSSI());
  json += "}";

  mqttClient.beginMessage(TOPIC_TELEMETRY, (unsigned long)json.length(), false, 0, false);
  mqttClient.print(json);
  mqttClient.endMessage();
}

void handleNetwork(unsigned long now) {
  // Auto-recover from simulated Wi-Fi dropout fault after 7 seconds
  if (wifiSimDropUntil > 0 && now >= wifiSimDropUntil) {
    wifiSimDropUntil = 0;
    if (activeFault == "wifi") {
      activeFault = "none";
      Serial.println("[FAULT SOLVED] Cloud link restored after simulated Wi-Fi dropout.");
      publishTelemetry();
    }
  }

  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_BUILTIN, LOW);
    if (now - lastWifiAttempt >= WIFI_RETRY_INTERVAL_MS) {
      lastWifiAttempt = now;
      connectWiFi(false);
    }
    return;
  }

  digitalWrite(LED_BUILTIN, HIGH);
  if (!mqttClient.connected()) {
    if (now - lastMqttAttempt >= MQTT_RETRY_INTERVAL_MS) {
      lastMqttAttempt = now;
      connectMQTT();
    }
  } else {
    mqttClient.poll();
  }
}

// =======================================
// 11. SETUP & MAIN LOOP
// =======================================
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  digitalWrite(RELAY_PIN, RELAY_OFF);
  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(FAN_PIN, LOW);
  pinMode(FAN_PIN, OUTPUT);

  relayOff();
  setFan(0);

  Serial.begin(115200);
  unsigned long serialWait = millis();
  while (!Serial && millis() - serialWait < 3000) {
    delay(10);
  }

  Wire.begin();
  Wire.setClock(100000);

  Serial.println();
  Serial.println("========================================================");
  Serial.println("   ECE 441 SMART HVAC: ALL-IN-ONE WIRELESS BENCH V6.0   ");
  Serial.println("   Arduino UNO R4 WiFi | Closed-Loop Nest + Fault Sync  ");
  Serial.println("========================================================");

  initializeSensor();
  if (sensorFound) {
    readSensor();
    // Initialize default setpoint to match current room temperature so bench starts in quiet IDLE
    if (isfinite(temperatureC) && temperatureC >= 15.0 && temperatureC <= 32.0) {
      targetSetpointC = temperatureC;
    }
  }
  lastSensorRead = millis();

  // Connect to IIT-IoT and HiveMQ Broker
  connectWiFi(true);
  if (WiFi.status() == WL_CONNECTED) {
    connectMQTT();
  }

  printMenu();
}

void loop() {
  unsigned long now = millis();

  // 1. Mandatory 5-second software heater safety cutoff
  if (heaterOn && (now - heaterStart >= HEAT_TIME_MS)) {
    stopHeater();
    Serial.println("5-second heating pulse complete.");
  }

  // 2. Always force relay OFF during safety lockout
  if (safetyLockout) {
    relayOff();
  }

  // 3. Periodic sensor reading, closed-loop thermostat evaluation & telemetry broadcast (every 2s)
  if (now - lastSensorRead >= SENSOR_INTERVAL_MS) {
    lastSensorRead = now;
    if (sensorFound) {
      readSensor();
    }
    runClosedLoopThermostat(now);
    printSensorData();
    publishTelemetry();
  }

  // Re-verify heater timer immediately after sensor read
  now = millis();
  if (heaterOn && (now - heaterStart >= HEAT_TIME_MS)) {
    stopHeater();
  }

  // 4. Mandatory 30-second fan cooldown timer
  if (cooldownActive && (now - cooldownStart >= COOLDOWN_MS)) {
    cooldownActive = false;
    if (!safetyLockout) {
      setFan(0);
    }
    Serial.println("30-second cooldown completed.");
    runClosedLoopThermostat(now);
    publishTelemetry();
  }

  // 5. Non-blocking Wi-Fi & HiveMQ polling
  handleNetwork(now);

  // 6. Local USB Serial command listener
  while (Serial.available()) {
    char cmd = Serial.read();
    executeCommand(cmd, "SERIAL");
  }
}
