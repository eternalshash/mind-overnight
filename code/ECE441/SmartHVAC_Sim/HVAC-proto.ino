
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
  }

  if (sensorFound) {
    bme688.setTemperatureOversampling(
      BME680_OS_8X
    );

    bme688.setHumidityOversampling(
      BME680_OS_2X
    );

    bme688.setPressureOversampling(
      BME680_OS_4X
    );

    bme688.setIIRFilterSize(
      BME680_FILTER_SIZE_3
    );

    // Internal gas-sensing heater
    // Does NOT control external PTC
    bme688.setGasHeater(320, 150);

    Serial.print("Sensor ready at 0x");
    Serial.println(sensorAddress, HEX);
  }
  else {
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
  if (gasReady || !isfinite(gasKOhms) ||
      gasKOhms <= 0) {
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

  float relative =
    gasKOhms / gasBaseline * 100.0;

  Serial.print("Baseline: ");
  Serial.print(gasBaseline, 2);
  Serial.println(" kOhms");

  Serial.print("Relative resistance: ");
  Serial.print(relative, 1);
  Serial.println("%");

  if (relative >= 110) {
    Serial.println("Trend: Resistance increased");
  }
  else if (relative >= 90) {
    Serial.println("Trend: Near baseline");
  }
  else if (relative >= 70) {
    Serial.println("Trend: Resistance decreased");
  }
  else {
    Serial.println("Trend: Large resistance decrease");
  }

  Serial.println(
    "Relative trend only; not an IAQ or CO2 value."
  );
}

// =======================================
// VALIDATE SENSOR DATA
// =======================================

const char* validateSensor() {
  if (!sensorFound) {
    return "BME688 missing";
  }

  if (!isfinite(temperatureC) ||
      temperatureC < MIN_TEMP_C ||
      temperatureC > 85.0) {
    return "Invalid BME688 temperature";
  }

  if (!isfinite(humidity) ||
      humidity < 0 ||
      humidity > 100) {
    return "Invalid BME688 humidity";
  }

  if (!isfinite(pressureHPA) ||
      pressureHPA < 300 ||
      pressureHPA > 1100) {
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
  Serial.print(
    fahrenheit(dewPointC(temperatureC, humidity)), 2
  );
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
  Serial.println(
    cooldownActive ? "ACTIVE" : "OFF"
  );

  Serial.print("Safety lockout: ");
  Serial.println(
    safetyLockout ? "ACTIVE" : "CLEAR"
  );

  if (safetyLockout) {
    Serial.print("Lockout reason: ");
    Serial.println(lockoutReason);
  }

  if (heaterOn) {
    Serial.print("Heating elapsed: ");
    Serial.print(
      (millis() - heaterStart) / 1000.0, 1
    );
    Serial.println(" / 5 seconds");
  }

  Serial.println("================================");
}
