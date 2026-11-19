#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>
#include <math.h>
#include <ctype.h>
#include <WiFiS3.h>
#include <ArduinoMqttClient.h>

// =======================================
// SMART HVAC DEMO V5 + WIRELESS / MQTT
// Arduino UNO R4 WiFi
// BME688 ONLY
// =======================================

// Conditional inclusion of secrets header
#if __has_include("arduino_secrets.h")
  #include "arduino_secrets.h"
#elif __has_include("../arduino_secrets.h")
  #include "../arduino_secrets.h"
#else
  #warning "arduino_secrets.h not found. Run generate_secrets.py to configure. Running in offline/autonomous mode."
  #define SECRET_SSID ""
  #define SECRET_PASS ""
  #define SECRET_BROKER ""
  #define SECRET_PORT 8883
  #define SECRET_USER ""
  #define SECRET_MQTT_PASS ""
  #define SECRET_TOPIC_TELEMETRY "ece441/group2/hvac/telemetry"
  #define SECRET_TOPIC_COMMAND   "ece441/group2/hvac/command"
#endif

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
const unsigned long WIFI_RETRY_INTERVAL_MS = 15000;
const unsigned long MQTT_RETRY_INTERVAL_MS = 5000;

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
unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;

const char* lockoutReason = "None";
const char* lastError = "None";

// =======================================
// WIRELESS & MQTT NETWORKING
// =======================================

WiFiSSLClient wifiSslClient;
MqttClient mqttClient(wifiSslClient);

const char topicTelemetry[]    = SECRET_TOPIC_TELEMETRY;
const char topicTelemetryAlt[] = "ece441/hvac/telemetry";
const char topicCommand[]      = SECRET_TOPIC_COMMAND;
const char topicCommandAlt[]   = "ece441/hvac/command";

// Forward declarations
void executeCommand(char cmd, const char* source = "SERIAL");
void publishTelemetry();
void onMqttMessageReceived(int messageSize);

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
// UNIT CONVERSIONS & HVAC METRICS
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

  float gamma = log(rh / 100.0) + (a * temp) / (b + temp);
  return (b * gamma) / (a - gamma);
}

float altitudeFeet(float pressure) {
  return 145366.45 * (1.0 - pow(pressure / SEA_LEVEL_HPA, 0.190284));
}

float apparentTempC(float t_c, float rh, float vel_ms) {
  if (isnan(t_c) || isnan(rh)) return NAN;
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
    emergencyStop("BME688 not detected");
  }

  Serial.println("============================");
}

// =======================================
// RESET GAS BASELINE
// =======================================

void resetGasBaseline() {
  gasTotal = 0;
  gasBaseline = 0;
  gasCount = 0;
  gasReady = false;

  Serial.println("Gas baseline reset.");
}

void updateGasBaseline() {
  if (gasReady || !isfinite(gasKOhms) || gasKOhms <= 0) {
    return;
  }

  gasTotal += gasKOhms;
  gasCount++;

  if (gasCount >= GAS_BASELINE_SAMPLES) {
    gasBaseline = gasTotal / gasCount;
    gasReady = true;
    Serial.println("Gas baseline established.");
  }
}

// =======================================
// GAS RESISTANCE INTERPRETATION
// =======================================

void printGasData() {
  Serial.println();
  Serial.println("[GAS SENSOR]");

  if (!isfinite(gasKOhms) || gasKOhms <= 0) {
    Serial.println("Gas reading unavailable");
    return;
  }

  Serial.print("Gas resistance: ");
  Serial.print(gasKOhms, 2);
  Serial.println(" kOhms");

  if (!gasReady) {
    Serial.print("Reference samples: ");
    Serial.print(gasCount);
    Serial.print("/");
    Serial.println(GAS_BASELINE_SAMPLES);
    return;
  }

  float relative = gasKOhms / gasBaseline * 100.0;

  Serial.print("Baseline: ");
  Serial.print(gasBaseline, 2);
  Serial.println(" kOhms");

  Serial.print("Relative resistance: ");
  Serial.print(relative, 1);
  Serial.println("%");

  if (relative >= 110) {
    Serial.println("Trend: Resistance increased");
  } else if (relative >= 90) {
    Serial.println("Trend: Near baseline");
  } else if (relative >= 70) {
    Serial.println("Trend: Resistance decreased");
  } else {
    Serial.println("Trend: Large resistance decrease");
  }

  Serial.println("Relative trend only; not an IAQ or CO2 value.");
}

// =======================================
// VALIDATE SENSOR DATA
// =======================================

const char* validateSensor() {
  if (!sensorFound) {
    return "BME688 missing";
  }

  if (!isfinite(temperatureC) || temperatureC < MIN_TEMP_C || temperatureC > 85.0) {
    return "Invalid BME688 temperature";
  }

  if (!isfinite(humidity) || humidity < 0 || humidity > 100) {
    return "Invalid BME688 humidity";
  }

  if (!isfinite(pressureHPA) || pressureHPA < 300 || pressureHPA > 1100) {
    return "Invalid BME688 pressure";
  }

  if (temperatureC >= MAX_TEMP_C) {
    return "BME688 overtemperature";
  }

  return NULL;
}

// =======================================
// READ BME688
// =======================================

void readSensor() {
  if (!sensorFound) {
    sensorValid = false;
    emergencyStop("BME688 not initialized");
    return;
  }

  bool success = bme688.performReading();

  if (!success) {
    sensorValid = false;
    emergencyStop("BME688 reading failed");
    return;
  }

  temperatureC = bme688.temperature;
  humidity = bme688.humidity;
  pressureHPA = bme688.pressure / 100.0;
  gasKOhms = bme688.gas_resistance / 1000.0;

  const char* error = validateSensor();

  if (error != NULL) {
    sensorValid = false;
    emergencyStop(error);
    return;
  }

  sensorValid = true;
  lastError = "None";

  updateGasBaseline();
  printSensorData();
}

// =======================================
// PRINT SENSOR DATA
// =======================================

void printSensorData() {
  Serial.println();
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

  Serial.print("Dew point: ");
  Serial.print(fahrenheit(dewPointC(temperatureC, humidity)), 2);
  Serial.println(" F");

  Serial.print("Approx. altitude: ");
  Serial.print(altitudeFeet(pressureHPA), 0);
  Serial.println(" ft");

  printGasData();

  Serial.println();
  Serial.println("[HVAC SYSTEM]");

  Serial.print("Heater: ");
  Serial.println(heaterOn ? "ON" : "OFF");

  Serial.print("Fan PWM: ");
  Serial.print(fanPWM * 100.0 / 255.0, 0);
  Serial.println("%");

  Serial.print("Cooldown: ");
  Serial.println(cooldownActive ? "ACTIVE" : "OFF");

  Serial.print("Safety lockout: ");
  Serial.println(safetyLockout ? "ACTIVE" : "CLEAR");

  if (safetyLockout) {
    Serial.print("Lockout reason: ");
    Serial.println(lockoutReason);
  }

  if (heaterOn) {
    Serial.print("Heating elapsed: ");
    Serial.print((millis() - heaterStart) / 1000.0, 1);
    Serial.println(" / 5 seconds");
  }

  Serial.println("================================");
}

// =======================================
// DIAGNOSTICS
// =======================================

void printDiagnostics() {
  Serial.println();
  Serial.println("===== BME688 DIAGNOSTICS =====");

  Serial.print("Sensor detected: ");
  Serial.println(sensorFound ? "YES" : "NO");

  Serial.print("Sensor address: 0x");
  Serial.println(sensorAddress, HEX);

  Serial.print("Sensor data valid: ");
  Serial.println(sensorValid ? "YES" : "NO");

  Serial.print("Last error: ");
  Serial.println(lastError);

  Serial.print("Temperature C: ");
  Serial.println(temperatureC);

  Serial.print("Humidity %: ");
  Serial.println(humidity);

  Serial.print("Pressure hPa: ");
  Serial.println(pressureHPA);

  Serial.print("Gas resistance kOhms: ");
  Serial.println(gasKOhms);

  Serial.print("Heater: ");
  Serial.println(heaterOn ? "ON" : "OFF");

  Serial.print("Cooldown: ");
  Serial.println(cooldownActive ? "ACTIVE" : "OFF");

  Serial.print("Lockout: ");
  Serial.println(safetyLockout ? "ACTIVE" : "CLEAR");

  Serial.print("Lockout reason: ");
  Serial.println(lockoutReason);

  // Network diagnostics
  Serial.print("Wi-Fi Status: ");
  Serial.println(WiFi.status() == WL_CONNECTED ? "CONNECTED" : "DISCONNECTED");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("IP: "); Serial.println(WiFi.localIP());
    Serial.print("RSSI: "); Serial.print(WiFi.RSSI()); Serial.println(" dBm");
  }
  Serial.print("MQTT Status: ");
  Serial.println(mqttClient.connected() ? "CONNECTED" : "DISCONNECTED");

  Serial.println("==============================");
}

// =======================================
// FIVE-SECOND HEATER TEST
// =======================================

void startHeaterTest() {
  if (safetyLockout || !sensorValid || cooldownActive || heaterOn) {
    Serial.println("HEATER TEST DENIED");
    if (safetyLockout) {
      Serial.print("Reason: ");
      Serial.println(lockoutReason);
    }
    return;
  }

  readSensor();

  if (safetyLockout || !sensorValid) {
    Serial.println("Unsafe sensor condition");
    return;
  }

  setFan(255);
  heaterStart = millis();
  relayOn();

  Serial.println();
  Serial.println("HEATER ON");
  Serial.println("5-second heating test started.");
  Serial.println("Fan at 100%.");
}

// =======================================
// RESET SAFETY
// =======================================

void resetSafety() {
  relayOff();

  Serial.println("Attempting safety reset...");

  if (cooldownActive) {
    Serial.println("Reset denied: cooldown active");
    return;
  }

  setFan(255);
  initializeSensor();

  if (!sensorFound) {
    Serial.println("Reset failed: sensor missing");
    return;
  }

  readSensor();

  if (!sensorValid) {
    Serial.println("Reset failed: invalid data");
    return;
  }

  safetyLockout = false;
  lockoutReason = "None";

  setFan(0);
  Serial.println("SAFETY RESET SUCCESSFUL");
}

// =======================================
// COMMAND DISPATCHER (SERIAL & MQTT)
// =======================================

void executeCommand(char cmd, const char* source) {
  cmd = toupper(cmd);
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
      Serial.println("Fan ON 100%");
      break;

    case 'M':
      if (!heaterOn && !cooldownActive && !safetyLockout) {
        setFan(128);
        Serial.println("Fan ON 50%");
      } else {
        Serial.println("Fan change denied");
      }
      break;

    case 'S':
      if (!heaterOn && !cooldownActive && !safetyLockout) {
        setFan(0);
        Serial.println("Fan OFF");
      } else {
        Serial.println("Fan OFF denied");
      }
      break;

    case 'X':
      emergencyStop("Manual emergency stop");
      break;

    case 'R':
      resetSafety();
      break;

    case 'D':
      printDiagnostics();
      break;

    case 'B':
      resetGasBaseline();
      break;

    case '?':
      printMenu();
      break;

    default:
      break;
  }
}

// =======================================
// COMMAND MENU
// =======================================

void printMenu() {
  Serial.println();
  Serial.println("====== HVAC COMMANDS ======");
  Serial.println("5 = Heater ON for 5 seconds");
  Serial.println("H = Stop heater");
  Serial.println("F = Fan ON 100%");
  Serial.println("M = Fan ON 50%");
  Serial.println("S = Fan OFF");
  Serial.println("X = Emergency software stop");
  Serial.println("R = Reset safety / retry sensor");
  Serial.println("D = Diagnostics");
  Serial.println("B = Reset gas baseline");
  Serial.println("? = Show menu");
  Serial.println("===========================");
}

// =======================================
// WIRELESS & MQTT IMPLEMENTATION
// =======================================

void connectWiFi(bool blocking = false) {
  if (strlen(SECRET_SSID) == 0) {
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println();
  Serial.print("[WIFI] Connecting to SSID: ");
  Serial.println(SECRET_SSID);

  WiFi.begin(SECRET_SSID, SECRET_PASS);

  if (blocking) {
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 8000) {
      delay(250);
      Serial.print(".");
    }
    Serial.println();
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WIFI] Connected to IIT-IoT!");
    Serial.print("[WIFI] IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WIFI] Signal (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else if (blocking) {
    Serial.println("[WIFI] Connection pending. Continuing in background...");
  }
}

void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqttClient.connected()) return;
  if (strlen(SECRET_BROKER) == 0) return;

  Serial.print("[MQTT] Connecting to broker ");
  Serial.print(SECRET_BROKER);
  Serial.print(":");
  Serial.println(SECRET_PORT);

  if (strlen(SECRET_USER) > 0) {
    mqttClient.setUsernamePassword(SECRET_USER, SECRET_MQTT_PASS);
  }

  mqttClient.setKeepAliveInterval(60 * 1000);

  if (!mqttClient.connect(SECRET_BROKER, SECRET_PORT)) {
    Serial.print("[MQTT] Connection failed! Error code = ");
    Serial.println(mqttClient.connectError());
    return;
  }

  Serial.println("[MQTT] Connected to HiveMQ Cloud!");

  // Subscribe to command channels
  mqttClient.subscribe(topicCommand);
  mqttClient.subscribe(topicCommandAlt);
  mqttClient.onMessage(onMqttMessageReceived);

  Serial.print("[MQTT] Subscribed to command topics: ");
  Serial.print(topicCommand);
  Serial.print(", ");
  Serial.println(topicCommandAlt);
}

void onMqttMessageReceived(int messageSize) {
  String topic = mqttClient.messageTopic();
  String payload = "";
  while (mqttClient.available()) {
    payload += (char)mqttClient.read();
  }
  payload.trim();

  Serial.print("[MQTT IN] Topic: ");
  Serial.print(topic);
  Serial.print(" | Payload: ");
  Serial.println(payload);

  if (payload.length() == 0) return;

  // Single character command
  if (payload.length() == 1) {
    executeCommand(payload.charAt(0), "MQTT");
    return;
  }

  // JSON format {"cmd": "5"} or {"command": "F"}
  int cmdIdx = payload.indexOf("\"cmd\"");
  if (cmdIdx < 0) cmdIdx = payload.indexOf("\"command\"");
  if (cmdIdx >= 0) {
    int colon = payload.indexOf(':', cmdIdx);
    if (colon >= 0) {
      for (int i = colon + 1; i < (int)payload.length(); i++) {
        char c = payload.charAt(i);
        if (c != ' ' && c != '\"' && c != '\'' && c != '{' && c != '}') {
          executeCommand(c, "MQTT");
          return;
        }
      }
    }
  }
}

void publishTelemetry() {
  if (!mqttClient.connected()) {
    return;
  }

  float tempF = fahrenheit(temperatureC);
  float dewPointF = fahrenheit(dewPointC(temperatureC, humidity));
  float altFt = altitudeFeet(pressureHPA);
  float fanPct = fanPWM * 100.0 / 255.0;
  float airVelMs = (fanPct / 100.0) * 3.4;
  float feelsLikeC = apparentTempC(temperatureC, humidity, airVelMs);
  float feelsLikeF = fahrenheit(feelsLikeC);
  float powerW = calculateCircuitPower(fanPWM, heaterOn);
  float relativeGas = gasReady ? (gasKOhms / gasBaseline * 100.0) : 100.0;

  mqttClient.beginMessage(topicTelemetry);
  mqttClient.print("{");
  mqttClient.print("\"device_id\":\"ARDUINO-UNO-R4-WIFI\",");
  mqttClient.print("\"source\":\"arduino-v5-bme688\",");
  mqttClient.print("\"temp_c\":"); mqttClient.print(temperatureC, 2); mqttClient.print(",");
  mqttClient.print("\"temp_f\":"); mqttClient.print(tempF, 2); mqttClient.print(",");
  mqttClient.print("\"humidity\":"); mqttClient.print(humidity, 1); mqttClient.print(",");
  mqttClient.print("\"pressure_hpa\":"); mqttClient.print(pressureHPA, 2); mqttClient.print(",");
  mqttClient.print("\"dew_point_f\":"); mqttClient.print(dewPointF, 2); mqttClient.print(",");
  mqttClient.print("\"altitude_ft\":"); mqttClient.print(altFt, 0); mqttClient.print(",");
  mqttClient.print("\"gas_kohms\":"); mqttClient.print(gasKOhms, 2); mqttClient.print(",");
  mqttClient.print("\"gas_rel_pct\":"); mqttClient.print(relativeGas, 1); mqttClient.print(",");
  mqttClient.print("\"feels_like_c\":"); mqttClient.print(feelsLikeC, 2); mqttClient.print(",");
  mqttClient.print("\"feels_like_f\":"); mqttClient.print(feelsLikeF, 2); mqttClient.print(",");
  mqttClient.print("\"air_velocity_ms\":"); mqttClient.print(airVelMs, 2); mqttClient.print(",");
  mqttClient.print("\"heater_relay\":"); mqttClient.print(heaterOn ? 1 : 0); mqttClient.print(",");
  mqttClient.print("\"heater_pwm\":"); mqttClient.print(heaterOn ? 255 : 0); mqttClient.print(",");
  mqttClient.print("\"fan_pwm\":"); mqttClient.print(fanPWM); mqttClient.print(",");
  mqttClient.print("\"fan_speed_pct\":"); mqttClient.print(fanPct, 1); mqttClient.print(",");
  mqttClient.print("\"power_w\":"); mqttClient.print(powerW, 2); mqttClient.print(",");
  mqttClient.print("\"cooldown_active\":"); mqttClient.print(cooldownActive ? 1 : 0); mqttClient.print(",");
  mqttClient.print("\"safety_lockout\":"); mqttClient.print(safetyLockout ? 1 : 0); mqttClient.print(",");
  mqttClient.print("\"lockout_reason\":\""); mqttClient.print(lockoutReason); mqttClient.print("\",");
  mqttClient.print("\"bme_ok\":"); mqttClient.print(sensorValid ? 1 : 0); mqttClient.print(",");
  mqttClient.print("\"wifi_rssi\":"); mqttClient.print(WiFi.RSSI());
  mqttClient.print("}");
  mqttClient.endMessage();
}

void handleNetwork(unsigned long now) {
  if (strlen(SECRET_SSID) == 0) {
    return; // Autonomous offline mode
  }

  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiAttempt >= WIFI_RETRY_INTERVAL_MS) {
      lastWifiAttempt = now;
      connectWiFi(false);
    }
    return;
  }

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
// SETUP
// =======================================

void setup() {
  digitalWrite(RELAY_PIN, RELAY_OFF);
  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(FAN_PIN, LOW);
  pinMode(FAN_PIN, OUTPUT);

  relayOff();
  setFan(0);

  Serial.begin(115200);

  Wire.begin();
  Wire.setClock(100000);

  Serial.println();
  Serial.println("SMART HVAC DEMO V5 + WIRELESS / MQTT");
  Serial.println("Board: Arduino UNO R4 WiFi");
  Serial.println("Sensor: BME688 ONLY");
  Serial.println("Relay: ACTIVE-HIGH (Pin 10)");
  Serial.println("Heating limit: 5 seconds");

  initializeSensor();

  if (sensorFound) {
    readSensor();
  }

  lastSensorRead = millis();

  // Print board MAC address
  byte mac[6];
  WiFi.macAddress(mac);
  Serial.print("Board MAC: ");
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 0x10) Serial.print("0");
    Serial.print(mac[i], HEX);
    if (i < 5) Serial.print(":");
  }
  Serial.println();

  // Initialize Wi-Fi and MQTT
  if (strlen(SECRET_SSID) > 0) {
    connectWiFi(true);
    if (WiFi.status() == WL_CONNECTED) {
      connectMQTT();
    }
  } else {
    Serial.println("[WIFI] Offline mode: No secrets configured in arduino_secrets.h.");
  }

  printMenu();
}

// =======================================
// MAIN LOOP
// =======================================

void loop() {
  unsigned long now = millis();

  // 1. Five-second maximum software timer
  if (heaterOn && now - heaterStart >= HEAT_TIME_MS) {
    stopHeater();
    Serial.println("5-second test complete.");
  }

  // 2. Always force relay OFF during lockout
  if (safetyLockout) {
    relayOff();
  }

  // 3. Read sensor & publish telemetry periodically
  if (now - lastSensorRead >= SENSOR_INTERVAL_MS) {
    lastSensorRead = now;

    if (sensorFound) {
      readSensor();
      if (sensorValid) {
        publishTelemetry();
      }
    }
  }

  // Check heater timer again after reading
  now = millis();
  if (heaterOn && now - heaterStart >= HEAT_TIME_MS) {
    stopHeater();
  }

  // 4. Cooldown timer
  if (cooldownActive && now - cooldownStart >= COOLDOWN_MS) {
    cooldownActive = false;

    if (!safetyLockout) {
      setFan(0);
    }

    Serial.println("Cooldown completed.");
  }

  // 5. Non-blocking wireless & MQTT handler
  handleNetwork(now);

  // 6. Serial commands
  if (Serial.available()) {
    char cmd = Serial.read();
    executeCommand(cmd, "SERIAL");
  }
}
