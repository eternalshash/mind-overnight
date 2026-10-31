#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <PID_v1.h>
#include "esp32_legacy_config.h"
#include "esp32_legacy_hal.h"
#include "thermal_comfort.h"

// Task Handles
TaskHandle_t TaskControl;
TaskHandle_t TaskTelemetry;

// Globals
SensorHAL hal;
WiFiClient espClient;
PubSubClient mqtt(espClient);

// PID Variables (Setpoint shared between Telemetry/Command task and Control task)
volatile double TargetSetpoint = 23.0;
double Setpoint = 23.0;
double Input = 0.0;
double Output = 0.0;
double Kp = 45.0, Ki = 0.5, Kd = 10.0;
PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

// Actuator States
volatile int current_heater_pwm = 0;
volatile int current_fan_pwm = 51; // 20% baseline draft (255 * 0.2)
long last_command_seq = -1;

// Extract numeric JSON field without requiring external JSON heap libraries
bool extractJsonFloat(const char* json, const char* key, float& outVal) {
    char pattern[48];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char* pos = strstr(json, pattern);
    if (!pos) return false;
    pos = strchr(pos + strlen(pattern), ':');
    if (!pos) return false;
    pos++;
    while (*pos == ' ' || *pos == '\t') pos++;
    char* endPtr = nullptr;
    float v = strtof(pos, &endPtr);
    if (endPtr == pos) return false;
    outVal = v;
    return true;
}

void applyRemoteControlPayload(const char* msg) {
    float spC = 0.0f;
    float seqF = -1.0f;
    if (extractJsonFloat(msg, "command_seq", seqF)) {
        long seq = (long)seqF;
        if (seq <= last_command_seq && last_command_seq >= 0) {
            return; // Already applied this command sequence
        }
        last_command_seq = seq;
    }

    if (extractJsonFloat(msg, "setpoint_c", spC) || extractJsonFloat(msg, "setpoint", spC)) {
        if (spC >= 15.0f && spC <= 30.0f) {
            TargetSetpoint = (double)spC;
            Serial.printf("[RPi->ESP32] Updated Target Setpoint to %.2f C (%.1f F)\n", spC, spC * 1.8f + 32.0f);
        }
    } else {
        // Support plain numeric string payload (e.g. "22.5")
        char* endPtr = nullptr;
        float plainSp = strtof(msg, &endPtr);
        if (endPtr != msg && plainSp >= 15.0f && plainSp <= 30.0f) {
            TargetSetpoint = (double)plainSp;
            Serial.printf("[RPi->ESP32] Updated Target Setpoint to %.2f C\n", plainSp);
        }
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    char buf[256];
    unsigned int copyLen = (length < sizeof(buf) - 1) ? length : (sizeof(buf) - 1);
    memcpy(buf, payload, copyLen);
    buf[copyLen] = '\0';
    Serial.printf("[MQTT RX] %s -> %s\n", topic, buf);
    applyRemoteControlPayload(buf);
}

void setup_wifi() {
    delay(10);
    Serial.printf("\nConnecting to %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        vTaskDelay(500 / portTICK_PERIOD_MS);
        Serial.print(".");
    }
    Serial.printf("\nWiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
}

bool tryReconnectMqtt() {
    if (mqtt.connected()) return true;
    Serial.printf("Attempting MQTT connection to %s:%d...\n", MQTT_BROKER, MQTT_PORT);
    if (mqtt.connect(DEVICE_ID)) {
        Serial.println("MQTT connected to Raspberry Pi Edge Broker!");
        mqtt.subscribe(MQTT_TOPIC_SUB);
        return true;
    }
    Serial.printf("MQTT unavailable (rc=%d), using HTTP REST fallback to RPi.\n", mqtt.state());
    return false;
}

bool postHttpTelemetryFallback(const char* payload) {
    if (WiFi.status() != WL_CONNECTED) return false;
    HTTPClient http;
    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d/api/telemetry", RPI_SERVER_HOST, RPI_HTTP_PORT);
    http.begin(url);
    http.setTimeout(1500);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST((uint8_t*)payload, strlen(payload));
    if (code == 200) {
        String resp = http.getString();
        applyRemoteControlPayload(resp.c_str());
        http.end();
        return true;
    }
    http.end();
    return false;
}

// Core 1 Task: Control Loop (High Priority, Deterministic, Autonomous Offline Fallback)
void controlLoopTask(void *pvParameters) {
    ledcSetup(HEATER_CHANNEL, PWM_FREQ, PWM_RES);
    ledcAttachPin(PIN_HEATER_PWM, HEATER_CHANNEL);
    ledcSetup(FAN_CHANNEL, PWM_FREQ, PWM_RES);
    ledcAttachPin(PIN_FAN_PWM, FAN_CHANNEL);

    hal.init();

    myPID.SetMode(AUTOMATIC);
    myPID.SetOutputLimits(-255, 255);

    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = 1000 / portTICK_PERIOD_MS; // 1Hz Loop

    for(;;) {
        Setpoint = TargetSetpoint;
        float raw_temp = hal.getTemperature();
        float humidity = hal.getHumidity();
        float air_velocity = hal.getAirVelocity(current_fan_pwm);

        // Calculate Apparent Temperature for PID input
        Input = ThermalComfort::calculateApparentTemp(raw_temp, humidity, air_velocity);

        myPID.Compute();

        int next_heater = 0;
        int next_fan = 51;
        // Split-Range Logic with Deadband
        if (Output > 10) { // Heating
            next_heater = (int)Output;
            next_fan = 51; // 20% Baseline draft
        } else if (Output < -10) { // Cooling
            next_heater = 0;
            next_fan = (int)abs(Output);
        }

        current_heater_pwm = constrain(next_heater, 0, 255);
        current_fan_pwm = constrain(next_fan, 0, 255);

        ledcWrite(HEATER_CHANNEL, current_heater_pwm);
        ledcWrite(FAN_CHANNEL, current_fan_pwm);

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

// Core 0 Task: Wi-Fi, Bidirectional MQTT & HTTP Edge Telemetry (Lower Priority)
void telemetryTask(void *pvParameters) {
    setup_wifi();
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(mqttCallback);

    unsigned long lastMqttRetryMs = 0;

    for(;;) {
        unsigned long nowMs = millis();
        if (!mqtt.connected() && (nowMs - lastMqttRetryMs >= 5000)) {
            lastMqttRetryMs = nowMs;
            tryReconnectMqtt();
        }
        if (mqtt.connected()) {
            mqtt.loop();
        }

        int h_pwm = current_heater_pwm;
        int f_pwm = current_fan_pwm;
        double sp_c = TargetSetpoint;

        float raw_temp = hal.getTemperature();
        float humidity = hal.getHumidity();
        float air_velocity = hal.getAirVelocity(f_pwm);
        float apparent_temp = ThermalComfort::calculateApparentTemp(raw_temp, humidity, air_velocity);
        float power_draw = hal.getPowerDraw(h_pwm, f_pwm);
        const char* mode_str = (h_pwm > 0) ? "HEATING" : ((f_pwm > 55) ? "COOLING" : "IDLE");

        char payload[320];
        snprintf(payload, sizeof(payload),
                 "{\"device_id\":\"%s\",\"source\":\"esp32\",\"temp\":%.2f,\"humidity\":%.2f,"
                 "\"apparent\":%.2f,\"velocity\":%.2f,\"power\":%.2f,\"heater_pwm\":%d,"
                 "\"fan_pwm\":%d,\"setpoint_c\":%.2f,\"mode\":\"%s\"}",
                 DEVICE_ID, raw_temp, humidity, apparent_temp, air_velocity,
                 power_draw, h_pwm, f_pwm, sp_c, mode_str);

        if (mqtt.connected() && mqtt.publish(MQTT_TOPIC_PUB, payload)) {
            Serial.printf("[ESP32->RPi MQTT] %s\n", payload);
        } else if (postHttpTelemetryFallback(payload)) {
            Serial.printf("[ESP32->RPi HTTP] %s\n", payload);
        } else {
            Serial.printf("[ESP32 OFFLINE AUTONOMOUS] %s\n", payload);
        }

        vTaskDelay(2000 / portTICK_PERIOD_MS); // 2 second telemetry period
    }
}

void setup() {
    Serial.begin(115200);

    // Core 1 (Control) Setup
    xTaskCreatePinnedToCore(
        controlLoopTask,
        "Control_Task",
        10000,
        NULL,
        2,
        &TaskControl,
        1);

    // Core 0 (Telemetry) Setup
    xTaskCreatePinnedToCore(
        telemetryTask,
        "Telemetry_Task",
        10000,
        NULL,
        1,
        &TaskTelemetry,
        0);
}

void loop() {
    vTaskDelay(portMAX_DELAY);
}
