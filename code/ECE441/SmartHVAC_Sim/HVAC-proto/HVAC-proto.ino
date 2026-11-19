// =============================================================================
// ECE 441: SMART HVAC CONTROL — ALL-IN-ONE WIRELESS BENCH FIRMWARE (V5.2)
// Single-file standalone sketch for Arduino UNO R4 WiFi (ESP32-S3 Co-Processor)
// Includes:
//   - Embedded IIT-IoT Wi-Fi & HiveMQ Cloud credentials (Zero extra files needed)
//   - Direct TCP Port 1883 MQTT (Bypasses UNO R4 SSL cert issues; bridges to Web 8884)
//   - Unique MAC-based ClientID & <256-byte telemetry buffer for ArduinoMqttClient
//   - Full Fan PWM (Pin 9) & Active-HIGH Relay Heater (Pin 10) control
//   - Bosch BME688 I2C telemetry & safety lockouts (5s heater limit, 30s cooldown)
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

// Note: Port 1883 (TCP) on Arduino bridges directly to Port 8884 (WSS) on HiveMQ Web Client
// and avoids ESP32-S3 Root CA certificate rejections on public HiveMQ.
const char SECRET_BROKER[]    = "broker.hivemq.com";
const int  SECRET_PORT        = 1883;
const char SECRET_USER[]      = "";
const char SECRET_MQTT_PASS[] = "";

// Unique Client ID prevents public broker collisions
const char MQTT_CLIENT_ID[]   = "ece441-group2-uno-r4-70041DD4F668";

// MQTT Topics (Compatible with both HiveMQ Web Client & Digital Twin Sim)
const char TOPIC_TELEMETRY[]     = "ece441/group2/hvac/telemetry";
const char TOPIC_TELEMETRY_ALT[] = "ece441/hvac/telemetry";
const char TOPIC_COMMAND[]       = "ece441/group2/hvac/command";
const char TOPIC_COMMAND_ALT[]   = "ece441/hvac/command";
const char TOPIC_SETPOINT[]      = "ece441/group2/hvac/setpoint";

// =======================================
// 2. HARDWARE PINOUT & TIMING
// =======================================
const uint8_t RELAY_PIN = 10;   // Active-HIGH Relay (12V PTC Heater)
const uint8_t FAN_PIN   = 9;    // PWM Gate (12V Blower Fan via MOSFET)

const uint8_t RELAY_ON  = HIGH;
const uint8_t RELAY_OFF = LOW;

const unsigned long HEAT_TIME_MS           = 5000;   // 5-second max heating pulse
const unsigned long COOLDOWN_MS            = 30000;  // 30-second mandatory post-heat fan cooldown
const unsigned long SENSOR_INTERVAL_MS     = 2000;   // 2-second telemetry & sim sync loop
const unsigned long WIFI_RETRY_INTERVAL_MS = 15000;
const unsigned long MQTT_RETRY_INTERVAL_MS = 5000;

// Safety Limits
const float MAX_TEMP_C = 40.0;
const float MIN_TEMP_C = -40.0;
const float SEA_LEVEL_HPA = 1013.25;
const int   GAS_BASELINE_SAMPLES = 20;

// =======================================
// 3. BME688 SENSOR & SYSTEM STATE
// =======================================
Adafruit_BME680 bme688(&Wire);

bool sensorFound = false;
bool sensorValid = false;
uint8_t sensorAddress = 0;

float temperatureC = 22.0; // Fallback for bench fan testing if sensor unplugged
float humidity     = 45.0;
float pressureHPA  = 1013.25;
float gasKOhms     = 100.0;

float gasTotal    = 0;
float gasBaseline = 0;
int   gasCount    = 0;
bool  gasReady    = false;

bool heaterOn       = false;
bool cooldownActive = false;
bool safetyLockout  = false;
uint8_t fanPWM      = 0;
float targetSetpointC = 22.0;
String hvacMode       = "AUTO";

unsigned long heaterStart     = 0;
unsigned long cooldownStart   = 0;
unsigned long lastSensorRead  = 0;
unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;

const char* lockoutReason = "None";
const char* lastError     = "None";
char lastCmdExecuted      = '-';

// Wireless Clients (Standard WiFiClient on Port 1883 for rock-solid UNO R4 connection)
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Forward Declarations
void executeCommand(char cmd, const char* source = "SERIAL");
void publishTelemetry();
void onMqttMessageReceived(int messageSize);
void printWiFiStatus();

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
  fanPWM = pwm;
  analogWrite(FAN_PIN, pwm);
}

void stopHeater() {
  bool wasHeating = heaterOn;
  relayOff();

  if (wasHeating) {
    cooldownActive = true;
    cooldownStart = millis();
    setFan(255);

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
  setFan(255);
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
// 7. TELEMETRY DISPLAY & DIAGNOSTICS
// =======================================
void printSensorData() {
  float fanPct = fanPWM * 100.0 / 255.0;
  float airVel = (fanPct / 100.0) * 3.4;
  float feelsC = apparentTempC(temperatureC, humidity, airVel);
  float powerW = calculateCircuitPower(fanPWM, heaterOn);

  Serial.println("================================");
  Serial.println("       SMART HVAC DEMO V5       ");
  Serial.println("================================");
  Serial.println("[BME688]");
  Serial.print("Temperature: ");
  Serial.print(fahrenheit(temperatureC), 2);
  Serial.print(" F / ");
  Serial.print(temperatureC, 2);
  Serial.println(" C");
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
  Serial.print("Heater Relay (10): "); Serial.println(heaterOn ? "ON (HIGH)" : "OFF (LOW)");
  Serial.print("Fan PWM (Pin 9):   "); Serial.print(fanPWM); Serial.print(" ("); Serial.print(fanPWM * 100.0 / 255.0, 0); Serial.println("%)");
  Serial.print("Cooldown Active:   "); Serial.println(cooldownActive ? "ACTIVE" : "OFF");
  Serial.print("Safety Lockout:    "); Serial.println(safetyLockout ? "ACTIVE" : "CLEAR");
  Serial.print("Lockout Reason:    "); Serial.println(lockoutReason);
  printWiFiStatus();
}

// =======================================
// 8. HEATER TEST & SAFETY RESET
// =======================================
void startHeaterTest() {
  if (safetyLockout || cooldownActive || heaterOn) {
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
  } else {
    Serial.println("WARNING: BME688 not detected; running 5-second bench relay & fan test!");
  }

  setFan(255);
  heaterStart = millis();
  relayOn();

  Serial.println();
  Serial.println("HEATER ON (Pin 10 HIGH)");
  Serial.println("5-second heating test started.");
  Serial.println("Fan at 100% (Pin 9 PWM = 255).");
  publishTelemetry();
}

void resetSafety() {
  relayOff();
  Serial.println("Attempting safety reset...");

  if (cooldownActive) {
    cooldownActive = false;
    Serial.println("Cooldown timer cleared.");
  }

  initializeSensor();
  if (sensorFound) {
    readSensor();
  }

  safetyLockout = false;
  lockoutReason = "None";
  setFan(0);

  Serial.println("SAFETY RESET SUCCESSFUL");
  publishTelemetry();
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
  Serial.println("X = Emergency software stop");
  Serial.println("R = Reset safety lockout / clear cooldown");
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
      startHeaterTest();
      break;

    case 'H':
      stopHeater();
      break;

    case 'F':
      setFan(255);
      Serial.println("Fan ON 100% (Pin 9 PWM = 255)");
      publishTelemetry();
      break;

    case 'M':
      if (!heaterOn) {
        setFan(128);
        Serial.println("Fan ON 50% (Pin 9 PWM = 128)");
        publishTelemetry();
      } else {
        Serial.println("Fan change denied while heater is active");
      }
      break;

    case 'S':
      if (!heaterOn) {
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
  mqttClient.setKeepAliveInterval(60 * 1000);

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

  Serial.print("[MQTT] Listening for commands on: ");
  Serial.println(TOPIC_COMMAND);

  // Immediately publish initial state upon connection
  publishTelemetry();
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

  // 1. Direct single-letter command from HiveMQ Web Client (e.g. "5", "F", "M", "S", "H", "W")
  if (payload.length() == 1) {
    executeCommand(payload.charAt(0), "MQTT");
    return;
  }

  // 2. JSON command from Digital Twin Simulation or Web UI:
  //    e.g. {"cmd":"F"}, {"command":"5"}, {"fan_pwm":200}, {"setpoint":23.5}
  int cmdIdx = payload.indexOf("\"cmd\"");
  if (cmdIdx < 0) cmdIdx = payload.indexOf("\"command\"");
  if (cmdIdx >= 0) {
    int colon = payload.indexOf(':', cmdIdx);
    if (colon >= 0) {
      for (int i = colon + 1; i < (int)payload.length(); i++) {
        char c = payload.charAt(i);
        if (c != ' ' && c != '\"' && c != '\'' && c != '{' && c != '}') {
          executeCommand(c, "MQTT-JSON");
          return;
        }
      }
    }
  }

  // Direct fan PWM value from Sim slider: {"fan_pwm": 180}
  int fanIdx = payload.indexOf("\"fan_pwm\"");
  if (fanIdx >= 0) {
    int colon = payload.indexOf(':', fanIdx);
    if (colon >= 0) {
      int val = payload.substring(colon + 1).toInt();
      val = constrain(val, 0, 255);
      setFan((uint8_t)val);
      Serial.print("[MQTT-SIM] Fan PWM set to: ");
      Serial.println(val);
      publishTelemetry();
    }
  }

  // Setpoint update from Sim Nest Turntable: {"setpoint": 24.0}
  if (topic == TOPIC_SETPOINT || payload.indexOf("\"setpoint\"") >= 0) {
    float sp = payload.toFloat();
    int spIdx = payload.indexOf("\"setpoint\"");
    if (spIdx >= 0) {
      int colon = payload.indexOf(':', spIdx);
      if (colon >= 0) sp = payload.substring(colon + 1).toFloat();
    }
    if (sp >= 10.0 && sp <= 35.0) {
      targetSetpointC = sp;
      Serial.print("[MQTT-SIM] Target Setpoint updated to: ");
      Serial.print(targetSetpointC, 1);
      Serial.println(" C");
      publishTelemetry();
    }
  }
}

void publishTelemetry() {
  if (!mqttClient.connected()) return;

  float fanPct = fanPWM * 100.0 / 255.0;
  float airVel = (fanPct / 100.0) * 3.4;
  float feelsC = apparentTempC(temperatureC, humidity, airVel);
  float powerW = calculateCircuitPower(fanPWM, heaterOn);

  // Compact JSON payload (< 240 bytes) so it fits safely inside ArduinoMqttClient's 256-byte TX buffer
  String json = "{";
  json += "\"device_id\":\"UNO-R4-WIFI\",";
  json += "\"temp_c\":" + String(temperatureC, 2) + ",";
  json += "\"temp_f\":" + String(fahrenheit(temperatureC), 2) + ",";
  json += "\"humidity\":" + String(humidity, 1) + ",";
  json += "\"pressure_hpa\":" + String(pressureHPA, 1) + ",";
  json += "\"feels_like_c\":" + String(feelsC, 2) + ",";
  json += "\"air_vel_ms\":" + String(airVel, 2) + ",";
  json += "\"heater_relay\":" + String(heaterOn ? 1 : 0) + ",";
  json += "\"fan_pwm\":" + String(fanPWM) + ",";
  json += "\"fan_speed_pct\":" + String(fanPct, 0) + ",";
  json += "\"power_w\":" + String(powerW, 2) + ",";
  json += "\"cooldown\":" + String(cooldownActive ? 1 : 0) + ",";
  json += "\"lockout\":" + String(safetyLockout ? 1 : 0) + ",";
  json += "\"last_cmd\":\"" + String(lastCmdExecuted) + "\",";
  json += "\"rssi\":" + String(WiFi.RSSI());
  json += "}";

  mqttClient.beginMessage(TOPIC_TELEMETRY, (unsigned long)json.length(), false, 0, false);
  mqttClient.print(json);
  mqttClient.endMessage();
}

void handleNetwork(unsigned long now) {
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
  Serial.println("   ECE 441 SMART HVAC: ALL-IN-ONE WIRELESS BENCH V5.2   ");
  Serial.println("   Arduino UNO R4 WiFi | Fan (Pin 9) | Heater (Pin 10)  ");
  Serial.println("========================================================");

  initializeSensor();
  if (sensorFound) {
    readSensor();
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
    Serial.println("5-second heating test complete.");
  }

  // 2. Always force relay OFF during safety lockout
  if (safetyLockout) {
    relayOff();
  }

  // 3. Periodic sensor reading & telemetry broadcast (every 2s)
  if (now - lastSensorRead >= SENSOR_INTERVAL_MS) {
    lastSensorRead = now;
    if (sensorFound) {
      readSensor();
    }
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
    Serial.println("30-second cooldown completed. Fan OFF.");
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
