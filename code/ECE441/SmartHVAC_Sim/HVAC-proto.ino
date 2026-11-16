
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
