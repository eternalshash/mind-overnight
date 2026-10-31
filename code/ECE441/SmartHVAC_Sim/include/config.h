#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// ECE 441 Smart HVAC Control - Unified Plug-and-Play Hardware Configuration
// Target MCU : Arduino Uno R4 (WiFi / Minima) & Wokwi Arduino Uno Simulator
// Reference  : Aligned 1:1 with Andy Tran & Kaleb Cowgur's 10-26-29 Pinout Report
// ============================================================================

#define DEVICE_ID               "ARDUINO-R4-HVAC-G2"
#define SERIAL_BAUD_RATE        115200

// --- Raspberry Pi 5 Edge Server & Telemetry Topics (Forwarded via USB Serial Bridge) ---
#define RPI_SERVER_HOST         "raspberrypi.local"
#define RPI_HTTP_PORT           8765
#define MQTT_TOPIC_PUB          "ece441/group2/hvac/telemetry"
#define MQTT_TOPIC_SUB          "ece441/group2/hvac/setpoint"
#define MQTT_TOPIC_ALERTS       "ece441/group2/hvac/alerts"

// --- Hardware Actuator Pins (Arduino Uno / Uno R4) ---
// Pin 9: Logic Pin connected to Gate (G) of IRLZ44N N-Channel MOSFET (PWM Fan Control)
#define PIN_FAN_MOSFET          9
#define PIN_FAN_PWM             PIN_FAN_MOSFET

// Pin 8: Digital Trigger connected to IN of 12V PTC Heating Element Relay Module
#define PIN_HEATER_RELAY        8
#define PIN_HEATER_PWM          PIN_HEATER_RELAY

// Pin 13: Onboard Status LED & Reference Indicator
#define PIN_STATUS_LED          13

// --- I2C Environmental Sensor Pins (Bosch BME280 / BME688) ---
// A4: SDA | A5: SCL | 5V: VIN | GND: Dedicated Arduino GND (Isolated from Fan return)
#define PIN_I2C_SDA             A4
#define PIN_I2C_SCL             A5
#define PIN_BME_SDA             PIN_I2C_SDA
#define PIN_BME_SCL             PIN_I2C_SCL
#define BME280_I2C_ADDR_PRIMARY 0x76
#define BME280_I2C_ADDR_ALT     0x77

// --- Closed-Loop PID & Thermal Parameters ---
#define DEFAULT_SETPOINT_C      23.0
#define MIN_SETPOINT_C          15.0
#define MAX_SETPOINT_C          30.0
#define PID_KP                  45.0
#define PID_KI                  0.5
#define PID_KD                  10.0

// --- Non-Blocking Timing Intervals (millis() Loops) ---
#define CONTROL_LOOP_MS         200
#define TELEMETRY_INTERVAL_MS   1000
#define BME_RETRY_INTERVAL_MS   3000

// --- Fan PWM Duty Cycle Limits (0-255) ---
#define FAN_MIN_Circulation_PWM 51   // 20% baseline draft circulation (51 / 255)
#define FAN_MAX_PWM             255

// --- Bench Electrical Circuit Constants (For Live Multimeter & Resistance Telemetry) ---
#define BENCH_V_SUPPLY_12V      12.00f  // Primary 12V 5A (60W) DC Bench Supply
#define BENCH_V_RAIL_5V         5.00f   // Regulated 5V Logic & Fan Rail
#define BENCH_R_FAN_OHM         14.286f // GDSTIME 5015 5V Blower Fan (5.00V / 0.35A)
#define BENCH_R_MOSFET_ON_OHM   0.028f  // IRLZ44N Logic-Level MOSFET R_DS(on) @ V_GS=5V
#define BENCH_R_PTC_HEATER_OHM  2.880f  // 12V 50W PTC Heating Element (12V^2 / 50W)
#define BENCH_I_MCU_BASE_A      0.045f  // Arduino Uno R4 + BME280 quiescent current (45 mA)
#define BENCH_BUCK_EFFICIENCY   0.88f   // LM2596 DC-DC Buck Converter efficiency

#endif // CONFIG_H
