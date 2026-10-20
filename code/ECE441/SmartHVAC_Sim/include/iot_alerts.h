#ifndef IOT_ALERTS_H
#define IOT_ALERTS_H

#include <Arduino.h>

// --- Alert Anomaly Thresholds ---
#define THRESHOLD_DT_DT_SURGE_F_PER_MIN    2.5f
#define THRESHOLD_DT_DT_DROP_F_PER_MIN    -3.5f
#define THRESHOLD_HEAT_STRESS_APPARENT_F  88.0f
#define THRESHOLD_HEAT_STRESS_DRYBULB_F   85.0f
#define THRESHOLD_FREEZE_RISK_F           45.0f
#define THRESHOLD_STATIC_DP_MAX_PA       280.0f
#define BLOWER_STALL_PERSISTENCE_TICKS        5

// --- MQTT Alert Topic ---
#define MQTT_TOPIC_ALERTS   "ece441/group2/hvac/alerts"

enum AlertSeverityLevel {
    SEV_INFO = 0,
    SEV_WARNING,
    SEV_CRITICAL,
    SEV_EMERGENCY
};

struct EdgeAlertPayload {
    const char* code;
    const char* headline;
    const char* systemAction;
    AlertSeverityLevel severity;
    float roomTempF;
    float apparentTempF;
    float outsideTempF;
    float rateOfChangeFPerMin;
};

class EdgeAlertDetector {
private:
    float tempHistory[60];
    int historyIndex;
    int historyCount;
    int blowerFaultCounter;
    unsigned long lastAlertMillis;

public:
    EdgeAlertDetector() : historyIndex(0), historyCount(0), blowerFaultCounter(0), lastAlertMillis(0) {}

    void init() {
        historyIndex = 0;
        historyCount = 0;
        blowerFaultCounter = 0;
        lastAlertMillis = 0;
        memset(tempHistory, 0, sizeof(tempHistory));
    }

    float computeRateOfChange(float currentTempF, float dtSeconds) {
        tempHistory[historyIndex] = currentTempF;
        historyIndex = (historyIndex + 1) % 60;
        if (historyCount < 60) historyCount++;

        if (historyCount < 10 || dtSeconds <= 0.0f) return 0.0f;
        int oldestIndex = (historyIndex - historyCount + 60) % 60;
        float deltaT = currentTempF - tempHistory[oldestIndex];
        float totalTimeMinutes = (historyCount * dtSeconds) / 60.0f;
        return deltaT / totalTimeMinutes;
    }

    bool checkThermalSurge(float dT_dt) {
        return (dT_dt >= THRESHOLD_DT_DT_SURGE_F_PER_MIN);
    }

    bool checkHeatStress(float apparentF) {
        return (apparentF >= THRESHOLD_HEAT_STRESS_APPARENT_F);
    }

    bool checkBlowerStall(int fanCmd, int tachRpm) {
        if (fanCmd > 38 && tachRpm < 100) { // >15% commanded
            blowerFaultCounter++;
            return (blowerFaultCounter >= BLOWER_STALL_PERSISTENCE_TICKS);
        } else {
            blowerFaultCounter = 0;
            return false;
        }
    }
};

#endif // IOT_ALERTS_H
