#ifndef CONFIG_H
#define CONFIG_H

// --- Wi-Fi & MQTT Configuration ---
#define WIFI_SSID       "Wokwi-GUEST"
#define WIFI_PASSWORD   ""
#define MQTT_BROKER     "broker.hivemq.com"
#define MQTT_PORT       1883
#define MQTT_TOPIC_PUB  "ece441/group2/hvac/telemetry"
#define MQTT_TOPIC_SUB  "ece441/group2/hvac/setpoint"

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
