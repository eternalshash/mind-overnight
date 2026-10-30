#ifndef BENCH_HAL_H
#define BENCH_HAL_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include "bench_config.h"

// Complete Electrical & Circuit Resistance Telemetry Snapshot
struct CircuitMetrics {
    float v_supply_12v;       // Primary bench power supply voltage (12.00 V)
    float v_rail_5v;          // Logic & fan 5V rail voltage (5.00 V)
    float v_mosfet_gs;        // Effective Gate-to-Source drive voltage on Pin 9 (0.00 - 5.00 V)
    float v_fan_eff;          // Effective voltage across GDSTIME 5015 blower fan (0.00 - 4.99 V)
    float i_mcu_a;            // Arduino Uno R4 + BME280 quiescent current (0.045 A)
    float i_fan_a;            // Blower fan current via IRLZ44N MOSFET Drain-Source (0.000 - 0.349 A)
    float i_heater_a;         // 12V PTC Heating Element current via Relay (0.000 or 4.167 A)
    float i_total_load_a;     // Sum of active branch currents (A)
    float i_12v_bus_a;        // Total current drawn from the 12V primary bench supply (A)
    float p_fan_w;            // Fan electrical power (W)
    float p_heater_w;         // PTC Heater electrical power (W)
    float p_total_w;          // Total circuit power consumption (W)
    float r_mosfet_ohm;       // IRLZ44N MOSFET on-state channel resistance R_DS(on) (0.028 Ohm)
    float r_fan_branch_ohm;   // Effective resistance of Fan + MOSFET branch (Ohm, -1 if OFF)
    float r_heater_ohm;       // Effective resistance of 12V PTC Heater branch (Ohm, -1 if OFF)
    float r_5v_rail_ohm;      // Equivalent resistance of the 5V subsystem (MCU || Fan) (Ohm)
    float r_total_circuit_ohm;// Total equivalent resistance of the entire circuit seen by 12V supply (Ohm)
};

class BenchSensorHAL {
private:
    Adafruit_BME280 bme;
    bool bme_online;
    unsigned long last_retry_ms;
    float last_valid_temp_c;
    float last_valid_rh;
    float last_valid_press_hpa;

public:
    BenchSensorHAL()
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

    // Compute duct air velocity (m/s) from IRLZ44N MOSFET Fan PWM duty (0-255)
    float estimateAirVelocity(int fan_pwm) {
        return (constrain(fan_pwm, 0, 255) / 255.0f) * 7.0f;
    }

    // Compute complete circuit Voltage (V), Current (A), Power (W), and Equivalent Resistance (Ohm)
    CircuitMetrics computeCircuitMetrics(bool heater_relay_on, int fan_pwm) {
        CircuitMetrics m;
        float duty = constrain(fan_pwm, 0, 255) / 255.0f;

        // 1. Voltages
        m.v_supply_12v = 12.00f;
        m.v_rail_5v    = 5.00f;
        m.v_mosfet_gs  = 5.00f * duty;

        // 2. Resistances of physical components:
        //    - GDSTIME 5015 5V Blower Fan: R_fan = 5.00V / 0.35A = 14.286 Ohm
        //    - IRLZ44N Logic-Level MOSFET @ V_GS=5V: R_DS(on) = 0.028 Ohm (28 mOhm)
        //    - 12V 50W PTC Heating Element: R_ptc = 12.0V^2 / 50.0W = 2.880 Ohm
        //    - Arduino Uno R4 + BME280 logic load: R_mcu = 5.00V / 0.045A = 111.11 Ohm
        const float R_FAN_WINDING = 14.286f;
        const float R_MOSFET_ON   = 0.028f;
        const float R_PTC_HEATER  = 2.880f;
        const float BUCK_EFF      = 0.88f; // LM2596 step-down efficiency

        m.r_mosfet_ohm = (fan_pwm > 0) ? R_MOSFET_ON : -1.0f;

        // 3. Branch Currents
        m.i_mcu_a = 0.045f; // 45 mA baseline MCU + BME280 current
        if (fan_pwm > 0) {
            float i_fan_peak = m.v_rail_5v / (R_FAN_WINDING + R_MOSFET_ON); // ~0.3493 A
            m.i_fan_a        = duty * i_fan_peak;
            m.v_fan_eff      = duty * (m.v_rail_5v - (i_fan_peak * R_MOSFET_ON));
            m.r_fan_branch_ohm = m.v_rail_5v / m.i_fan_a;
        } else {
            m.i_fan_a        = 0.0f;
            m.v_fan_eff      = 0.0f;
            m.r_fan_branch_ohm = -1.0f; // Open circuit (MOSFET cutoff)
        }

        if (heater_relay_on) {
            m.i_heater_a   = m.v_supply_12v / R_PTC_HEATER; // 4.167 A
            m.r_heater_ohm = R_PTC_HEATER;                  // 2.88 Ohm
        } else {
            m.i_heater_a   = 0.0f;
            m.r_heater_ohm = -1.0f; // Open relay contact
        }

        // 4. Total Currents & Power
        float i_5v_total   = m.i_mcu_a + m.i_fan_a;
        m.i_total_load_a   = i_5v_total + m.i_heater_a;
        m.p_fan_w          = m.v_rail_5v * m.i_fan_a;
        m.p_heater_w       = m.v_supply_12v * m.i_heater_a;
        float p_5v_total_w = m.v_rail_5v * i_5v_total;
        m.p_total_w        = p_5v_total_w + m.p_heater_w;

        // Current drawn from primary 12V supply (including LM2596 buck conversion)
        m.i_12v_bus_a = m.i_heater_a + (p_5v_total_w / (m.v_supply_12v * BUCK_EFF));

        // 5. Equivalent Circuit Resistances (R = V / I)
        m.r_5v_rail_ohm       = m.v_rail_5v / i_5v_total;
        m.r_total_circuit_ohm = m.v_supply_12v / m.i_12v_bus_a;

        return m;
    }
};

#endif // BENCH_HAL_H
