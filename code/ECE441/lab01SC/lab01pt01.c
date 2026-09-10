#include <Arduino.h>
#include <avr/io.h>
#include <util/delay.h>

void setup(void) {
    DDRD |= (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 6) | (1 << 7);
    DDRB &= ~((1 << 4) | (1 << 5));
    PORTB |= (1 << 4) | (1 << 5);
    PORTD = (1 << 4) | (1 << 5);
}

void loop(void) {
    if (!(PINB & (1 << 4)) || !(PINB & (1 << 5))) {
        PORTD &= ~(1 << 4);
        PORTD |= (1 << 3);
        _delay_ms(1000);

        PORTD &= ~(1 << 3);
        PORTD |= (1 << 2);
        _delay_ms(1000);
        PORTD &= ~(1 << 5);
        PORTD |= (1 << 7);
        _delay_ms(5000);

        PORTD &= ~(1 << 7);
        PORTD |= (1 << 6);
        _delay_ms(1000);
        uart_puts("[TELEMETRY][PT1] Phase 5: All Red (1s)\r\n");

        PORTD &= ~(1 << 6);
        PORTD |= (1 << 5);
        delay(1000);

        PORTD &= ~(1 << 2);
        PORTD |= (1 << 4);
        uart_puts("[TELEMETRY][PT1] Cycle Complete -> State: IDLE (NS: GREEN, EW: RED)\r\n");
    }
}
