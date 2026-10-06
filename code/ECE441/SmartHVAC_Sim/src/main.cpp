#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <PID_v1.h>
#include "config.h"
#include "hal_sensors.h"
#include "thermal_comfort.h"

// Task Handles
TaskHandle_t TaskControl;
TaskHandle_t TaskTelemetry;

// Globals
SensorHAL hal;
WiFiClient espClient;
PubSubClient mqtt(espClient);

// PID Variables
double Setpoint = 25.0;
double Input = 0.0;
double Output = 0.0;
double Kp = 45.0, Ki = 0.5, Kd = 10.0;
PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

// Actuator States
int current_heater_pwm = 0;
int current_fan_pwm = 51; // 20% baseline draft (255 * 0.2)

void setup_wifi() {
    delay(10);
    Serial.printf("\nConnecting to %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected.");
}

void reconnect() {
    while (!mqtt.connected()) {
        Serial.print("Attempting MQTT connection...");
        if (mqtt.connect("ESP32_HVAC_Group2")) {
            Serial.println("connected");
            mqtt.subscribe(MQTT_TOPIC_SUB);
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqtt.state());
            Serial.println(" try again in 5 seconds");
            vTaskDelay(5000 / portTICK_PERIOD_MS);
        }
    }
}

// Core 1 Task: Control Loop (High Priority, Deterministic)
void controlLoopTask(void *pvParameters) {
    // Setup PWM
    ledcSetup(HEATER_CHANNEL, PWM_FREQ, PWM_RES);
    ledcAttachPin(PIN_HEATER_PWM, HEATER_CHANNEL);
    ledcSetup(FAN_CHANNEL, PWM_FREQ, PWM_RES);
    ledcAttachPin(PIN_FAN_PWM, FAN_CHANNEL);
    
    hal.init();
    
    // PID Configuration
    myPID.SetMode(AUTOMATIC);
    // Allow PID output from -255 to 255 for split range
    myPID.SetOutputLimits(-255, 255);
    
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = 1000 / portTICK_PERIOD_MS; // 1Hz Loop
    
    for(;;) {
        float raw_temp = hal.getTemperature();
        float humidity = hal.getHumidity();
        float air_velocity = hal.getAirVelocity(current_fan_pwm);
        
        // Calculate Apparent Temperature for PID input
        Input = ThermalComfort::calculateApparentTemp(raw_temp, humidity, air_velocity);
        
        myPID.Compute();
        
        // Split-Range Logic with Deadband
        if (Output > 10) { // Heating
            current_heater_pwm = (int)Output;
            current_fan_pwm = 51; // 20% Baseline draft
        } else if (Output < -10) { // Cooling
            current_heater_pwm = 0;
            current_fan_pwm = (int)abs(Output);
        } else { // Deadband
            current_heater_pwm = 0;
            current_fan_pwm = 51; // Baseline draft
        }
        
        // Safety bounds
        current_heater_pwm = constrain(current_heater_pwm, 0, 255);
        current_fan_pwm = constrain(current_fan_pwm, 0, 255);
        
        // Actuate
        ledcWrite(HEATER_CHANNEL, current_heater_pwm);
        ledcWrite(FAN_CHANNEL, current_fan_pwm);
        
        // Delay until next period (1Hz loop)
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

// Core 0 Task: Wi-Fi & MQTT (Lower Priority)
void telemetryTask(void *pvParameters) {
    setup_wifi();
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    
    for(;;) {
        if (!mqtt.connected()) {
            reconnect();
        }
        mqtt.loop();
        
        // Grab current data for telemetry
        float raw_temp = hal.getTemperature();
        float humidity = hal.getHumidity();
        float air_velocity = hal.getAirVelocity(current_fan_pwm);
        float apparent_temp = ThermalComfort::calculateApparentTemp(raw_temp, humidity, air_velocity);
        float power_draw = hal.getPowerDraw(current_heater_pwm, current_fan_pwm);
        
        char payload[256];
        snprintf(payload, sizeof(payload), 
                 "{\"temp\":%.2f, \"humidity\":%.2f, \"apparent\":%.2f, \"velocity\":%.2f, \"power\":%.2f, \"heater_pwm\":%d, \"fan_pwm\":%d}",
                 raw_temp, humidity, apparent_temp, air_velocity, power_draw, current_heater_pwm, current_fan_pwm);
                 
        mqtt.publish(MQTT_TOPIC_PUB, payload);
        
        Serial.printf("Telemetry Published: %s\n", payload);
        
        vTaskDelay(2000 / portTICK_PERIOD_MS); // 2 second telemetry period
    }
}

void setup() {
    Serial.begin(115200);
    
    // Core 1 (Control) Setup
    xTaskCreatePinnedToCore(
        controlLoopTask,   /* Task function. */
        "Control_Task",    /* name of task. */
        10000,             /* Stack size of task */
        NULL,              /* parameter of the task */
        2,                 /* priority of the task */
        &TaskControl,      /* Task handle to keep track of created task */
        1);                /* pin task to core 1 */

    // Core 0 (Telemetry) Setup
    xTaskCreatePinnedToCore(
        telemetryTask,     /* Task function. */
        "Telemetry_Task",  /* name of task. */
        10000,             /* Stack size of task */
        NULL,              /* parameter of the task */
        1,                 /* priority of the task */
        &TaskTelemetry,    /* Task handle to keep track of created task */
        0);                /* pin task to core 0 */
}

void loop() {
    // Empty loop, managed by FreeRTOS tasks
    vTaskDelay(portMAX_DELAY);
}
