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
            }
        }
    }

    last_reading = reading;

    if (!paused && (current_time - last_count_time >= 500)) {
        last_count_time = current_time;
        count = (count + 1) & 0x3F;
        PORTD = (PORTD & ~0xFC) | ((count & 0x3F) << 2);
    }

    if (current_time - last_digit_time >= 500) {
        last_digit_time = current_time;
        digit = (digit + 1) % 10;
        PORTB = (PORTB & ~0x0F) | (pb_digits[digit] & 0x0F);
        PORTC = (PORTC & ~0x07) | (pc_digits[digit] & 0x07);
    }
}


/*
Digital Pin 0 (PD0) is the hardware RX (USART Receiver) pin.      
Digital Pin 1 (PD1) is the hardware TX (USART Transmitter) pin.

Serial Telemetry & Debugging: The firmware explicitly initializes
  the USART peripheral via uart_init() (or Serial.begin()) to send    
  telemetry data, cycle logs, and state information to the computer   
  over the Serial Monitor.                                            
  2. Conflict with USB Interface: Pins 0 and 1 are physically wired to
  the onboard USB-to-Serial bridge microcontroller (ATmega16U2). Using
  them as general-purpose I/O (GPIO) would disrupt the serial         
  telemetry stream and cause bus contention with the USB bridge.      
  3. Firmware Uploading: Arduino uses the UART interface and          
  bootloader to flash programs over the USB port. Driving these pins  
  with external components during normal operation can interfere with 
  uploading new code.  


  2. 

 2. When You Would Be Able to Use Pins 0 and 1 in a Project      
                                                                      
  You can use Pins 0 and 1 in a project under the following           
  circumstances:                                                      
                                                                      
  1. Pin-Constrained Standalone Projects: When all other I/O pins     
  (Digital 2–13 and Analog A0–A5 configured as digital I/O) are fully 
  occupied and additional GPIO lines are strictly needed.             
  2. No Serial Monitor / Debugging Required: When your embedded       
  project is in its final deployment state and no runtime serial      
  communication, logging, or USB debugging is needed.                 
  3. Dedicated External UART Communication: When you want to          
  communicate with external serial hardware (e.g., GPS modules,       
  Bluetooth HC-05 modules, Wi-Fi ESP8266, or sensors using hardware   
  serial) rather than using them as standard GPIO.          

*/