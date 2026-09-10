#include <Arduino.h>

void setup(void) {
    DDRD |= (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 6) | (1 << 7);
    DDRB &= ~((1 << 4) | (1 << 5));
    PORTD = (1 << 4) | (1 << 5);
    Serial.begin(115200);
    Serial.println(F("[TELEMETRY][PT1] System initialized. State: IDLE (NS: GREEN, EW: RED)"));
}

void loop(void) {
    if (!(PINB & (1 << 4)) || !(PINB & (1 << 5))) {
        Serial.println(F("[TELEMETRY][PT1] Sensor Triggered -> Phase 1: NS Yellow (1s)"));
        PORTD &= ~(1 << 4);
        PORTD |= (1 << 3);
        delay(1000);
        Serial.println(F("[TELEMETRY][PT1] Phase 2: All Red (1s)"));

        PORTD &= ~(1 << 3);
        PORTD |= (1 << 2);
        delay(1000);
        Serial.println(F("[TELEMETRY][PT1] Phase 3: EW Green (5s)"));

        PORTD &= ~(1 << 5);
        PORTD |= (1 << 7);
        delay(5000);
        Serial.println(F("[TELEMETRY][PT1] Phase 4: EW Yellow (1s)"));

        PORTD &= ~(1 << 7);
        PORTD |= (1 << 6);
        delay(1000);
        Serial.println(F("[TELEMETRY][PT1] Phase 5: All Red (1s)"));

        PORTD &= ~(1 << 6);
        PORTD |= (1 << 5);
        delay(1000);

        PORTD &= ~(1 << 2);
        PORTD |= (1 << 4);
        Serial.println(F("[TELEMETRY][PT1] Cycle Complete -> State: IDLE (NS: GREEN, EW: RED)"));
    }
}
