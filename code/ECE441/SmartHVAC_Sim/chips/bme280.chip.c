#include "wokwi-api.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  pin_t pin_vin;
  pin_t pin_gnd;
  uint8_t reg_addr;
  bool waiting_reg;
  uint32_t attr_temp;
  uint32_t attr_hum;
  uint32_t attr_pres;
  uint8_t regs[256];
} bme280_state_t;

static void refresh_measurement_regs(bme280_state_t *chip) {
  float temp_c = attr_read_float(chip->attr_temp);
  float hum_pct = attr_read_float(chip->attr_hum);
  float pres_hpa = attr_read_float(chip->attr_pres);

  if (temp_c < -40.0f) temp_c = -40.0f;
  if (temp_c > 85.0f) temp_c = 85.0f;
  if (hum_pct < 0.0f) hum_pct = 0.0f;
  if (hum_pct > 100.0f) hum_pct = 100.0f;

  // Exact compensation mapping for dig_T1=0, dig_T2=16384, dig_T3=0:
  // adc_T_20bit = temp_c * 40960.0f
  int32_t adc_T = (int32_t)(temp_c * 40960.0f);
  if (adc_T < 0) adc_T = 0;
  chip->regs[0xFA] = (uint8_t)((adc_T >> 12) & 0xFF);
  chip->regs[0xFB] = (uint8_t)((adc_T >> 4) & 0xFF);
  chip->regs[0xFC] = (uint8_t)((adc_T << 4) & 0xF0);

  // Exact compensation mapping for dig_H2=4096, others=0:
  // adc_H_16bit = hum_pct * 16.0f
  uint16_t adc_H = (uint16_t)(hum_pct * 16.0f);
  chip->regs[0xFD] = (uint8_t)((adc_H >> 8) & 0xFF);
  chip->regs[0xFE] = (uint8_t)(adc_H & 0xFF);

  // Pressure raw 20-bit
  int32_t adc_P = 524288 - (int32_t)((pres_hpa - 1013.25f) * 64.0f);
  chip->regs[0xF7] = (uint8_t)((adc_P >> 12) & 0xFF);
  chip->regs[0xF8] = (uint8_t)((adc_P >> 4) & 0xFF);
  chip->regs[0xF9] = (uint8_t)((adc_P << 4) & 0xF0);
}

static bool on_i2c_connect(void *user_data, uint32_t address, bool read) {
  bme280_state_t *chip = (bme280_state_t *)user_data;
  if (!read) {
    chip->waiting_reg = true;
  } else {
    refresh_measurement_regs(chip);
  }
  return true;
}

static uint8_t on_i2c_read(void *user_data) {
  bme280_state_t *chip = (bme280_state_t *)user_data;
  uint8_t val = chip->regs[chip->reg_addr];
  chip->reg_addr++;
  return val;
}

static bool on_i2c_write(void *user_data, uint8_t data) {
  bme280_state_t *chip = (bme280_state_t *)user_data;
  if (chip->waiting_reg) {
    chip->reg_addr = data;
    chip->waiting_reg = false;
  } else {
    if (chip->reg_addr != 0xD0 && chip->reg_addr != 0xF3) {
      chip->regs[chip->reg_addr] = data;
    }
    chip->reg_addr++;
  }
  return true;
}

static void on_i2c_disconnect(void *user_data) {
  (void)user_data;
}

void chip_init(void) {
  bme280_state_t *chip = calloc(1, sizeof(bme280_state_t));
  chip->pin_vin = pin_init("VIN", INPUT_PULLUP);
  chip->pin_gnd = pin_init("GND", INPUT_PULLDOWN);
  pin_t scl = pin_init("SCL", INPUT_PULLUP);
  pin_t sda = pin_init("SDA", INPUT_PULLUP);

  chip->attr_temp = attr_init_float("temperature", 20.5f);
  chip->attr_hum = attr_init_float("humidity", 48.0f);
  chip->attr_pres = attr_init_float("pressure", 1013.25f);

  // Chip ID for Bosch BME280 = 0x60
  chip->regs[0xD0] = 0x60;
  // Status = ready
  chip->regs[0xF3] = 0x00;

  // Calibration constants:
  // dig_T1 = 0, dig_T2 = 16384 (0x4000), dig_T3 = 0
  chip->regs[0x88] = 0x00;
  chip->regs[0x89] = 0x00;
  chip->regs[0x8A] = 0x00;
  chip->regs[0x8B] = 0x40;
  chip->regs[0x8C] = 0x00;
  chip->regs[0x8D] = 0x00;

  // dig_P1 = 32768 (0x8000)
  chip->regs[0x8E] = 0x00;
  chip->regs[0x8F] = 0x80;

  // dig_H1 = 0 (0xA1), dig_H2 = 4096 (0x1000 at 0xE1..0xE2)
  chip->regs[0xA1] = 0x00;
  chip->regs[0xE1] = 0x00;
  chip->regs[0xE2] = 0x10;
  chip->regs[0xE3] = 0x00;
  chip->regs[0xE4] = 0x00;
  chip->regs[0xE5] = 0x00;
  chip->regs[0xE6] = 0x00;
  chip->regs[0xE7] = 0x00;

  refresh_measurement_regs(chip);

  const i2c_config_t i2c_cfg = {
    .user_data = chip,
    .address = 0x76,
    .scl = scl,
    .sda = sda,
    .connect = on_i2c_connect,
    .read = on_i2c_read,
    .write = on_i2c_write,
    .disconnect = on_i2c_disconnect,
  };
  i2c_init(&i2c_cfg);
}
