
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

// BME280 sensor
Adafruit_BME280 bme;
bool sensorReady = false;

// Fan control
const int FAN_PIN = 9;

unsigned long lastSensorRead = 0;
const unsigned long SENSOR_INTERVAL = 2000;

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("================================");
  Serial.println(" BME280 + FULL-SPEED FAN TEST");
  Serial.println(" Arduino UNO R4");
  Serial.println("================================");

  // Configure fan output
  pinMode(FAN_PIN, OUTPUT);

  // Turn fan on at full power
  analogWrite(FAN_PIN, 255);

  Serial.println("Fan set to 100% power.");
  Serial.println("Fan will remain on.");

  // Initialize I2C
  Wire.begin();

  // Initialize BME280
  Serial.println("Initializing BME280...");

  if (bme.begin(0x76, &Wire)) {
    Serial.println("BME280 detected at 0x76!");
    sensorReady = true;
  }
  else if (bme.begin(0x77, &Wire)) {
    Serial.println("BME280 detected at 0x77!");
    sensorReady = true;
  }

  if (sensorReady) {
    Serial.println("BME280 initialization successful!");
  }
  else {
    Serial.println("WARNING: BME280 not detected.");
    Serial.println("Fan will continue running.");
  }

  Serial.println();
  Serial.println("Starting continuous sensor readings...");
  Serial.println();
}

void loop() {
  unsigned long currentTime = millis();

  // Read sensor every 2 seconds
  if (sensorReady &&
      currentTime - lastSensorRead >= SENSOR_INTERVAL) {

    lastSensorRead = currentTime;

    float temperatureC = bme.readTemperature();
    float temperatureF = (temperatureC * 9.0 / 5.0) + 32.0;

    float humidity = bme.readHumidity();
    float pressure = bme.readPressure() / 100.0F;

    Serial.println("----- SENSOR READINGS -----");

    Serial.print("Temperature: ");
    Serial.print(temperatureF, 2);
    Serial.println(" F");

    Serial.print("Humidity: ");
    Serial.print(humidity, 2);
    Serial.println(" %");

    Serial.print("Pressure: ");
    Serial.print(pressure, 2);
    Serial.println(" hPa");

    Serial.println("Fan setting: 100%");
    Serial.println();
  }
}
