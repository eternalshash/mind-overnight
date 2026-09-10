#include <Arduino.h>
#include <avr/io.h>

void uart_init(void) {
    UBRR0H = 0;
    UBRR0L = 8;
    UCSR0A |= (1 << U2X0);
    UCSR0B = (1 << TXEN0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
}

void uart_putc(char c) {
    while (!(UCSR0A & (1 << UDRE0)));
    UDR0 = c;
}

void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

void setup(void) {
    DDRD |= (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 6) | (1 << 7);
    DDRB &= ~((1 << 4) | (1 << 5));
    PORTB |= (1 << 4) | (1 << 5);
    PORTD = (1 << 4) | (1 << 5);
    uart_init();
    uart_puts("[TELEMETRY][PT1] System initialized. State: IDLE (NS: GREEN, EW: RED)\r\n");
}

void loop(void) {
    if (!(PINB & (1 << 4)) || !(PINB & (1 << 5))) {
        uart_puts("[TELEMETRY][PT1] Sensor Triggered -> Phase 1: NS Yellow (1s)\r\n");
        PORTD &= ~(1 << 4);
        PORTD |= (1 << 3);
        delay(1000);
        uart_puts("[TELEMETRY][PT1] Phase 2: All Red (1s)\r\n");

        PORTD &= ~(1 << 3);
        PORTD |= (1 << 2);
        delay(1000);
        uart_puts("[TELEMETRY][PT1] Phase 3: EW Green (5s)\r\n");

        PORTD &= ~(1 << 5);
        PORTD |= (1 << 7);
        delay(5000);
        uart_puts("[TELEMETRY][PT1] Phase 4: EW Yellow (1s)\r\n");

        PORTD &= ~(1 << 7);
        PORTD |= (1 << 6);
        delay(1000);
        uart_puts("[TELEMETRY][PT1] Phase 5: All Red (1s)\r\n");

        PORTD &= ~(1 << 6);
        PORTD |= (1 << 5);
        delay(1000);

        PORTD &= ~(1 << 2);
        PORTD |= (1 << 4);
        uart_puts("[TELEMETRY][PT1] Cycle Complete -> State: IDLE (NS: GREEN, EW: RED)\r\n");
    }
}
