#ifndef BENCH_CONFIG_H
#define BENCH_CONFIG_H

// ============================================================================
// ECE 441 Smart HVAC - Plug-and-Play Hardware Pinout Configuration
// Aligned 1:1 with Andy Tran & Kaleb Cowgur's 10-26-29 Hardware Pinout Report
// ============================================================================

#define DEVICE_ID               "ARDUINO-R4-HVAC-G2"
#define SERIAL_BAUD_RATE        115200

// --- Actuator Pins (Arduino Uno / Uno R4) ---
// Pin 9: Logic Pin connected to Gate (G) of IRLZ44N N-Channel MOSFET (PWM Fan Control)
#define PIN_FAN_MOSFET          9

// Pin 8: Digital Trigger connected to IN of 12V PTC Heating Element Relay Module
#define PIN_HEATER_RELAY        8

// Pin 13: Onboard Status / Common Reference Indicator
#define PIN_STATUS_LED          13

// --- I2C Environmental Sensor Pins (Bosch BME280 / BME688) ---
// A4: SDA | A5: SCL | 5V: VIN | GND: Dedicated Arduino GND (Isolated from Fan return)
#define PIN_BME_SDA             A4
#define PIN_BME_SCL             A5
#define BME280_I2C_ADDR_PRIMARY 0x76
#define BME280_I2C_ADDR_ALT     0x77

// --- Closed-Loop PID & Thermal Parameters ---
#define DEFAULT_SETPOINT_C      23.0
#define MIN_SETPOINT_C          15.0
#define MAX_SETPOINT_C          30.0
#define PID_KP                  45.0
#define PID_KI                  0.5
#define PID_KD                  10.0

// --- Timing Intervals (Non-Blocking millis() Loops) ---
#define CONTROL_LOOP_MS         200
#define TELEMETRY_INTERVAL_MS   1000
#define BME_RETRY_INTERVAL_MS   3000

// --- Baseline Fan Draft Speed (PWM 0-255) ---
#define FAN_MIN_Circulation_PWM 51   // 20% baseline airflow circulation
#define FAN_MAX_PWM             255

#endif // BENCH_CONFIG_H
