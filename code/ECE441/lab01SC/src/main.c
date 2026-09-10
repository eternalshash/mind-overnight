#include <Arduino.h>
#include <avr/io.h>

static const uint8_t pb_digits[10] = {0x00, 0x09, 0x04, 0x00, 0x09, 0x02, 0x02, 0x08, 0x00, 0x00};
static const uint8_t pc_digits[10] = {0x04, 0x07, 0x02, 0x03, 0x01, 0x01, 0x00, 0x07, 0x00, 0x01};

static uint8_t count = 0;
static uint8_t digit = 0;
static uint8_t paused = 0;

static uint8_t button_state = 1;
static uint8_t last_reading = 1;
static unsigned long last_debounce_time = 0;
static const unsigned long debounce_delay = 50;

static unsigned long last_count_time = 0;
static unsigned long last_digit_time = 0;

void setup(void) {
    DDRD |= (0x3F << 2);
    DDRB &= ~(1 << 4);
    PORTB |= (1 << 4);
    DDRB |= 0x0F;
    DDRC |= 0x07;

    PORTD = (PORTD & ~0xFC) | ((count & 0x3F) << 2);
    PORTB = (PORTB & ~0x0F) | (pb_digits[digit] & 0x0F);
    PORTC = (PORTC & ~0x07) | (pc_digits[digit] & 0x07);

    uart_init();
    uart_puts("[TELEMETRY][PT2] 6-Bit Counter & 7-Seg Display Initialized\r\n");
}

void loop(void) {
    unsigned long current_time = millis();
    uint8_t reading = (PINB & (1 << 4)) ? 1 : 0;

    if (reading != last_reading) {
        last_debounce_time = current_time;
    }

    if ((current_time - last_debounce_time) > debounce_delay) {
        if (reading != button_state) {
            button_state = reading;
            if (button_state == 0) {
                paused = !paused;
                uart_puts("[TELEMETRY][PT2] Button Toggle -> State: ");
                uart_puts(paused ? "PAUSED\r\n" : "RUNNING\r\n");
            }
        }
    }

    last_reading = reading;

    if (!paused && (current_time - last_count_time >= 500)) {
        last_count_time = current_time;
        count = (count + 1) & 0x3F;
        PORTD = (PORTD & ~0xFC) | ((count & 0x3F) << 2);
        uart_puts("[TELEMETRY][PT2] Time: ");
        uart_put_num(current_time);
        uart_puts("ms | Count: 0b");
        for (int8_t i = 5; i >= 0; i--) {
            uart_putc((count & (1 << i)) ? '1' : '0');
        }
        uart_puts(" (");
        uart_put_num(count);
        uart_puts(") | Seg: ");
        uart_put_num(digit);
        uart_puts("\r\n");
    }

    if (current_time - last_digit_time >= 500) {
        last_digit_time = current_time;
        digit = (digit + 1) % 10;
        PORTB = (PORTB & ~0x0F) | (pb_digits[digit] & 0x0F);
        PORTC = (PORTC & ~0x07) | (pc_digits[digit] & 0x07);
    }
}
