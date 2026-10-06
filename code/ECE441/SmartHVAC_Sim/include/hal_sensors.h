#ifndef HAL_SENSORS_H
#define HAL_SENSORS_H

#include <Arduino.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

class SensorHAL {
private:
    Adafruit_BME280 bme;
    bool bme_status;

public:
    SensorHAL() : bme_status(false) {}

    void init() {
        bme_status = bme.begin(0x76);
        if (!bme_status) {
            Serial.println("Warning: BME280 not found, using mock values if needed.");
        }
    }

    float getTemperature() {
        if (bme_status) return bme.readTemperature();
        // Map Wokwi potentiometer (0-4095) to temperature range (10C to 40C)
        int potValue = analogRead(34);
        return 10.0 + (potValue / 4095.0) * 30.0;
    }

    float getHumidity() {
        if (bme_status) return bme.readHumidity();
        return 50.0; // Mock default
    }

    // Mock FS3000 Air Velocity Sensor based on Fan PWM (0-255)
    float getAirVelocity(int fan_pwm_val) {
        // Assume max fan pwm (255) gives 7 m/s
        return (fan_pwm_val / 255.0) * 7.0;
    }

    // Mock INA219 Power Draw based on Heater and Fan PWM (0-255)
    float getPowerDraw(int heater_pwm_val, int fan_pwm_val) {
        // Heater max 60W, Fan max 10W
        float heater_power = (heater_pwm_val / 255.0) * 60.0;
        float fan_power = (fan_pwm_val / 255.0) * 10.0;
        return heater_power + fan_power;
    }
};

#endif // HAL_SENSORS_H
