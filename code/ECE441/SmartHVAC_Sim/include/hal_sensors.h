#ifndef HAL_SENSORS_H
#define HAL_SENSORS_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include "config.h"

// Complete Electrical & Circuit Resistance Telemetry Snapshot
struct CircuitMetrics {
    float v_supply_12v;        // Primary bench power supply voltage (12.00 V)
    float v_rail_5v;           // Logic & fan 5V rail voltage (5.00 V)
    float v_mosfet_gs;         // Effective Gate-to-Source drive voltage on Pin 9 (0.00 - 5.00 V)
    float v_fan_eff;           // Effective voltage across GDSTIME 5015 blower fan (0.00 - 4.99 V)
    float i_mcu_a;             // Arduino Uno R4 + BME280 quiescent current (0.045 A)
    float i_fan_a;             // Blower fan current via IRLZ44N MOSFET Drain-Source (0.000 - 0.349 A)
    float i_heater_a;          // 12V PTC Heating Element current via Relay (0.000 or 4.167 A)
    float i_total_load_a;      // Sum of active branch currents (A)
    float i_12v_bus_a;         // Total current drawn from the 12V primary bench supply (A)
    float p_fan_w;             // Fan electrical power (W)
    float p_heater_w;          // PTC Heater electrical power (W)
    float p_total_w;           // Total circuit power consumption (W)
    float r_mosfet_ohm;        // IRLZ44N MOSFET on-state channel resistance R_DS(on) (0.028 Ohm)
    float r_fan_branch_ohm;    // Effective resistance of Fan + MOSFET branch (Ohm, -1 if OFF)
    float r_heater_ohm;        // Effective resistance of 12V PTC Heater branch (Ohm, -1 if OFF)
    float r_5v_rail_ohm;       // Equivalent resistance of the 5V subsystem (MCU || Fan) (Ohm)
    float r_total_circuit_ohm; // Total equivalent resistance of the entire circuit seen by 12V supply (Ohm)
};

class SensorHAL {
private:
    Adafruit_BME280 bme;
    bool bme_online;
    unsigned long last_retry_ms;
    float last_valid_temp_c;
    float last_valid_rh;
    float last_valid_press_hpa;

public:
    SensorHAL()
        : bme_online(false),
          last_retry_ms(0),
          last_valid_temp_c(20.5f),
          last_valid_rh(48.0f),
          last_valid_press_hpa(1013.25f) {}

    bool init() {
        Wire.begin();
        bme_online = bme.begin(BME280_I2C_ADDR_PRIMARY);
        if (!bme_online) {
            bme_online = bme.begin(BME280_I2C_ADDR_ALT);
        }
        return bme_online;
    }

    // Automatic soft-reconnect if the BME280 jumper wire is bumped in lab
    void pollSensor(float &temp_c, float &rh_pct, float &press_hpa, bool &sensor_ok) {
        if (!bme_online) {
            unsigned long now = millis();
            if (now - last_retry_ms >= BME_RETRY_INTERVAL_MS) {
                last_retry_ms = now;
                init();
            }
        }

        if (bme_online) {
            float t = bme.readTemperature();
            float h = bme.readHumidity();
            float p = bme.readPressure() / 100.0f;

            if (!isnan(t) && t > -35.0f && t < 80.0f) {
                last_valid_temp_c = t;
                last_valid_rh = (!isnan(h) && h >= 0.0f && h <= 100.0f) ? h : last_valid_rh;
                last_valid_press_hpa = (!isnan(p) && p > 800.0f && p < 1200.0f) ? p : last_valid_press_hpa;
                sensor_ok = true;
            } else {
                bme_online = false;
                sensor_ok = false;
            }
        } else {
            sensor_ok = false;
        }

        temp_c = last_valid_temp_c;
        rh_pct = last_valid_rh;
        press_hpa = last_valid_press_hpa;
    }

    float getTemperature() {
        float t, h, p;
        bool ok;
        pollSensor(t, h, p, ok);
        return t;
    }

    float getHumidity() {
        return last_valid_rh;
    }

    // Compute duct air velocity (m/s) from IRLZ44N MOSFET Fan PWM duty (0-255)
    float estimateAirVelocity(int fan_pwm) {
        return (constrain(fan_pwm, 0, 255) / 255.0f) * 7.0f;
    }

    float getAirVelocity(int fan_pwm) {
        return estimateAirVelocity(fan_pwm);
    }

    // Compute complete circuit Voltage (V), Current (A), Power (W), and Equivalent Resistance (Ohm)
    CircuitMetrics computeCircuitMetrics(bool heater_relay_on, int fan_pwm) {
        CircuitMetrics m;
        float duty = constrain(fan_pwm, 0, 255) / 255.0f;

        m.v_supply_12v = BENCH_V_SUPPLY_12V;
        m.v_rail_5v    = BENCH_V_RAIL_5V;
        m.v_mosfet_gs  = BENCH_V_RAIL_5V * duty;
        m.r_mosfet_ohm = (fan_pwm > 0) ? BENCH_R_MOSFET_ON_OHM : -1.0f;

        m.i_mcu_a = BENCH_I_MCU_BASE_A;
        if (fan_pwm > 0) {
            float i_fan_peak = m.v_rail_5v / (BENCH_R_FAN_OHM + BENCH_R_MOSFET_ON_OHM);
            m.i_fan_a        = duty * i_fan_peak;
            m.v_fan_eff      = duty * (m.v_rail_5v - (i_fan_peak * BENCH_R_MOSFET_ON_OHM));
            m.r_fan_branch_ohm = m.v_rail_5v / m.i_fan_a;
        } else {
            m.i_fan_a        = 0.0f;
            m.v_fan_eff      = 0.0f;
            m.r_fan_branch_ohm = -1.0f;
        }

        if (heater_relay_on) {
            m.i_heater_a   = m.v_supply_12v / BENCH_R_PTC_HEATER_OHM;
            m.r_heater_ohm = BENCH_R_PTC_HEATER_OHM;
        } else {
            m.i_heater_a   = 0.0f;
            m.r_heater_ohm = -1.0f;
        }

        float i_5v_total   = m.i_mcu_a + m.i_fan_a;
        m.i_total_load_a   = i_5v_total + m.i_heater_a;
        m.p_fan_w          = m.v_rail_5v * m.i_fan_a;
        m.p_heater_w       = m.v_supply_12v * m.i_heater_a;
        float p_5v_total_w = m.v_rail_5v * i_5v_total;
        m.p_total_w        = p_5v_total_w + m.p_heater_w;

        m.i_12v_bus_a         = m.i_heater_a + (p_5v_total_w / (m.v_supply_12v * BENCH_BUCK_EFFICIENCY));
        m.r_5v_rail_ohm       = m.v_rail_5v / i_5v_total;
        m.r_total_circuit_ohm = m.v_supply_12v / m.i_12v_bus_a;

        return m;
    }

    float getPowerDraw(int heater_pwm, int fan_pwm) {
        return computeCircuitMetrics(heater_pwm >= 64, fan_pwm).p_total_w;
    }
};

typedef SensorHAL BenchSensorHAL;

#endif // HAL_SENSORS_H
