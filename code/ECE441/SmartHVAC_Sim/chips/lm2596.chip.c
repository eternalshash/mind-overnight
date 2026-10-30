#include "wokwi-api.h"
#include <stdlib.h>

void chip_init(void) {
  pin_init("IN_12V", OUTPUT_HIGH);
  pin_init("GND_IN", OUTPUT_LOW);
  pin_init("OUT_V", OUTPUT_HIGH);
  pin_init("GND_OUT", OUTPUT_LOW);
}
