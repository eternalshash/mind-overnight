#ifndef CONFIG_H
#define CONFIG_H

// --- Wi-Fi & Raspberry Pi 5 Edge Server Configuration ---
// Update WIFI_SSID / WIFI_PASSWORD for lab router or hotspot (keep "Wokwi-GUEST" for Wokwi sim)
#define WIFI_SSID       "Wokwi-GUEST"
#define WIFI_PASSWORD   ""

// Plug-and-Play Raspberry Pi 5 Server Hostname (mDNS) or LAN IP (e.g. "192.168.0.70")
#define RPI_SERVER_HOST "raspberrypi.local"
#define RPI_HTTP_PORT   8765
#define MQTT_BROKER     RPI_SERVER_HOST
#define MQTT_PORT       1883

// --- Unified MQTT Topics (Shared with Raspberry Pi 5 Edge Server) ---
#define DEVICE_ID       "ESP32-HVAC-G2"
#define MQTT_TOPIC_PUB    "ece441/group2/hvac/telemetry"
#define MQTT_TOPIC_SUB    "ece441/group2/hvac/setpoint"
#define MQTT_TOPIC_ALERTS "ece441/group2/hvac/alerts"

// --- Hardware Pins ---
#define PIN_HEATER_PWM  25
#define PIN_FAN_PWM     26
#define PIN_I2C_SDA     21
#define PIN_I2C_SCL     22

// --- PWM Configuration ---
#define PWM_FREQ        5000
#define PWM_RES         8
#define HEATER_CHANNEL  0
#define FAN_CHANNEL     1

#endif // CONFIG_H
