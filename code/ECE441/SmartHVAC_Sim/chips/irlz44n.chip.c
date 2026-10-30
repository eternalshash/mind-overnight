#include "wokwi-api.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DISP_W 168
#define DISP_H 56

typedef struct {
  pin_t pin_g;
  pin_t pin_d;
  pin_t pin_s;
  buffer_t fb;
  uint64_t window_start_ns;
  uint64_t high_accum_ns;
  uint64_t last_edge_ns;
  bool last_active;
  uint32_t pixels[DISP_W * DISP_H];
} chip_state_t;

// Compact 5x7 ASCII glyph table (32..90)
static const uint8_t font5x7[][5] = {
  {0x00,0x00,0x00,0x00,0x00}, // ' ' 32
  {0x00,0x00,0x5F,0x00,0x00}, // '!' 33
  {0x00,0x07,0x00,0x07,0x00}, // '"' 34
  {0x14,0x7F,0x14,0x7F,0x14}, // '#' 35
  {0x24,0x2A,0x7F,0x2A,0x12}, // '$' 36
  {0x23,0x13,0x08,0x64,0x62}, // '%' 37
  {0x36,0x49,0x55,0x22,0x50}, // '&' 38
  {0x00,0x05,0x03,0x00,0x00}, // ''' 39
  {0x00,0x1C,0x22,0x41,0x00}, // '(' 40
  {0x00,0x41,0x22,0x1C,0x00}, // ')' 41
  {0x14,0x08,0x3E,0x08,0x14}, // '*' 42
  {0x08,0x08,0x3E,0x08,0x08}, // '+' 43
  {0x00,0x50,0x30,0x00,0x00}, // ',' 44
  {0x08,0x08,0x08,0x08,0x08}, // '-' 45
  {0x00,0x60,0x60,0x00,0x00}, // '.' 46
  {0x20,0x10,0x08,0x04,0x02}, // '/' 47
  {0x3E,0x51,0x49,0x45,0x3E}, // '0' 48
  {0x00,0x42,0x7F,0x40,0x00}, // '1' 49
  {0x42,0x61,0x51,0x49,0x46}, // '2' 50
  {0x21,0x41,0x45,0x4B,0x31}, // '3' 51
  {0x18,0x14,0x12,0x7F,0x10}, // '4' 52
  {0x27,0x45,0x45,0x45,0x39}, // '5' 53
  {0x3C,0x4A,0x49,0x49,0x30}, // '6' 54
  {0x01,0x71,0x09,0x05,0x03}, // '7' 55
  {0x36,0x49,0x49,0x49,0x36}, // '8' 56
  {0x06,0x49,0x49,0x29,0x1E}, // '9' 57
  {0x00,0x36,0x36,0x00,0x00}, // ':' 58
  {0x00,0x56,0x36,0x00,0x00}, // ';' 59
  {0x08,0x14,0x22,0x41,0x00}, // '<' 60
  {0x14,0x14,0x14,0x14,0x14}, // '=' 61
  {0x00,0x41,0x22,0x14,0x08}, // '>' 62
  {0x02,0x01,0x51,0x09,0x06}, // '?' 63
  {0x32,0x49,0x79,0x41,0x3E}, // '@' 64
  {0x7E,0x11,0x11,0x11,0x7E}, // 'A' 65
  {0x7F,0x49,0x49,0x49,0x36}, // 'B' 66
  {0x3E,0x41,0x41,0x41,0x22}, // 'C' 67
  {0x7F,0x41,0x41,0x22,0x1C}, // 'D' 68
  {0x7F,0x49,0x49,0x49,0x41}, // 'E' 69
  {0x7F,0x09,0x09,0x09,0x01}, // 'F' 70
  {0x3E,0x41,0x49,0x49,0x7A}, // 'G' 71
  {0x7F,0x08,0x08,0x08,0x7F}, // 'H' 72
  {0x00,0x41,0x7F,0x41,0x00}, // 'I' 73
  {0x20,0x40,0x41,0x3F,0x01}, // 'J' 74
  {0x7F,0x08,0x14,0x22,0x41}, // 'K' 75
  {0x7F,0x40,0x40,0x40,0x40}, // 'L' 76
  {0x7F,0x02,0x0C,0x02,0x7F}, // 'M' 77
  {0x7F,0x04,0x08,0x10,0x7F}, // 'N' 78
  {0x3E,0x41,0x41,0x41,0x3E}, // 'O' 79
  {0x7F,0x09,0x09,0x09,0x06}, // 'P' 80
  {0x3E,0x41,0x51,0x21,0x5E}, // 'Q' 81
  {0x7F,0x09,0x19,0x29,0x46}, // 'R' 82
  {0x46,0x49,0x49,0x49,0x31}, // 'S' 83
  {0x01,0x01,0x7F,0x01,0x01}, // 'T' 84
  {0x3F,0x40,0x40,0x40,0x3F}, // 'U' 85
  {0x1F,0x20,0x40,0x20,0x1F}, // 'V' 86
  {0x3F,0x40,0x38,0x40,0x3F}, // 'W' 87
  {0x63,0x14,0x08,0x14,0x63}, // 'X' 88
  {0x07,0x08,0x70,0x08,0x07}, // 'Y' 89
  {0x61,0x51,0x49,0x45,0x43}  // 'Z' 90
};

static void draw_char(uint32_t *px, int x, int y, char c, uint32_t color) {
  if (c >= 'a' && c <= 'z') c -= 32;
  if (c < 32 || c > 90) c = ' ';
  const uint8_t *glyph = font5x7[c - 32];
  for (int col = 0; col < 5; col++) {
    uint8_t bits = glyph[col];
    for (int row = 0; row < 7; row++) {
      if (bits & (1 << row)) {
        int px_x = x + col;
        int px_y = y + row;
        if (px_x >= 0 && px_x < DISP_W && px_y >= 0 && px_y < DISP_H) {
          px[px_y * DISP_W + px_x] = color;
        }
      }
    }
  }
}

static void draw_str(uint32_t *px, int x, int y, const char *s, uint32_t color) {
  while (*s) {
    draw_char(px, x, y, *s++, color);
    x += 6;
  }
}

static void render_multimeter(chip_state_t *chip, float duty) {
  if (duty < 0.0f) duty = 0.0f;
  if (duty > 1.0f) duty = 1.0f;

  // ABGR colors (0xFFBBGGRR)
  const uint32_t BG_COLOR     = 0xFF221409; // Deep navy background
  const uint32_t BORDER_COLOR = 0xFFFFBF38; // Cyan border
  const uint32_t CYAN_TEXT    = 0xFFFFE500; // Bright cyan
  const uint32_t GREEN_TEXT   = 0xFF81B910; // Emerald green
  const uint32_t AMBER_TEXT   = 0xFF0B9EF5; // Amber gold
  const uint32_t WHITE_TEXT   = 0xFFF5E7DB; // Crisp light gray/white

  for (int i = 0; i < DISP_W * DISP_H; i++) {
    chip->pixels[i] = BG_COLOR;
  }
  for (int x = 0; x < DISP_W; x++) {
    chip->pixels[x] = BORDER_COLOR;
    chip->pixels[(DISP_H - 1) * DISP_W + x] = BORDER_COLOR;
  }
  for (int y = 0; y < DISP_H; y++) {
    chip->pixels[y * DISP_W] = BORDER_COLOR;
    chip->pixels[y * DISP_W + (DISP_W - 1)] = BORDER_COLOR;
  }

  int pwm_val = (int)(duty * 255.0f + 0.5f);
  float pct = duty * 100.0f;
  float v_gs = 5.0f * duty;
  float i_fan_ma = duty * 349.3f;
  float i_tot_ma = 45.0f + i_fan_ma;
  float p_w = 5.0f * (i_tot_ma / 1000.0f);
  float r_5v = 5.0f / (i_tot_ma / 1000.0f);
  float i_12v = (p_w / (12.0f * 0.88f));
  float r_tot = 12.0f / i_12v;

  char line1[32], line2[32], line3[32], line4[32], line5[32];
  snprintf(line1, sizeof(line1), "IRLZ44N MOSFET MULTIMETER");
  snprintf(line2, sizeof(line2), "FAN:%3d%% (PWM:%3d) VGS:%.1fV", (int)(pct + 0.5f), pwm_val, v_gs);
  snprintf(line3, sizeof(line3), "IFAN:%3dmA ITOT:%3dmA %.2fW", (int)(i_fan_ma + 0.5f), (int)(i_tot_ma + 0.5f), p_w);
  if (pwm_val > 0) {
    float r_fan = 5000.0f / i_fan_ma;
    snprintf(line4, sizeof(line4), "RFAN:%5.1f  R5V:%5.1f OHM", r_fan, r_5v);
  } else {
    snprintf(line4, sizeof(line4), "RFAN: OPEN  R5V:%5.1f OHM", r_5v);
  }
  snprintf(line5, sizeof(line5), "RTOT(12V): %6.1f OHM", r_tot);

  draw_str(chip->pixels, 5, 4,  line1, CYAN_TEXT);
  draw_str(chip->pixels, 5, 14, line2, WHITE_TEXT);
  draw_str(chip->pixels, 5, 24, line3, GREEN_TEXT);
  draw_str(chip->pixels, 5, 34, line4, AMBER_TEXT);
  draw_str(chip->pixels, 5, 44, line5, CYAN_TEXT);

  buffer_write(chip->fb, 0, chip->pixels, sizeof(chip->pixels));
}

static void update_mosfet(chip_state_t *chip) {
  uint64_t now = get_sim_nanos();
  if (chip->last_active) {
    chip->high_accum_ns += (now - chip->last_edge_ns);
  }
  chip->last_edge_ns = now;

  uint32_t g_val = pin_read(chip->pin_g);
  uint32_t s_val = pin_read(chip->pin_s);
  bool active = (g_val == HIGH && s_val == LOW);
  chip->last_active = active;

  if (active) {
    pin_mode(chip->pin_d, OUTPUT_LOW);
  } else {
    pin_mode(chip->pin_d, INPUT_PULLUP);
  }
}

static void on_pin_change(void *user_data, pin_t pin, uint32_t value) {
  (void)pin;
  (void)value;
  chip_state_t *chip = (chip_state_t *)user_data;
  update_mosfet(chip);
}

static void on_timer(void *user_data) {
  chip_state_t *chip = (chip_state_t *)user_data;
  uint64_t now = get_sim_nanos();
  if (chip->last_active) {
    chip->high_accum_ns += (now - chip->last_edge_ns);
  }
  chip->last_edge_ns = now;

  uint64_t elapsed = now - chip->window_start_ns;
  float duty = 0.0f;
  if (elapsed > 0) {
    duty = (float)((double)chip->high_accum_ns / (double)elapsed);
  }
  chip->window_start_ns = now;
  chip->high_accum_ns = 0;

  render_multimeter(chip, duty);
}

void chip_init(void) {
  chip_state_t *chip = calloc(1, sizeof(chip_state_t));
  chip->pin_g = pin_init("G", INPUT_PULLDOWN);
  chip->pin_d = pin_init("D", INPUT_PULLUP);
  chip->pin_s = pin_init("S", INPUT_PULLDOWN);

  uint32_t w = DISP_W, h = DISP_H;
  chip->fb = framebuffer_init(&w, &h);
  chip->window_start_ns = get_sim_nanos();
  chip->last_edge_ns = chip->window_start_ns;

  const pin_watch_config_t watch_cfg = {
    .edge = BOTH,
    .pin_change = on_pin_change,
    .user_data = chip,
  };
  pin_watch(chip->pin_g, &watch_cfg);
  pin_watch(chip->pin_s, &watch_cfg);

  const timer_config_t t_cfg = {
    .user_data = chip,
    .callback = on_timer,
  };
  timer_t t = timer_init(&t_cfg);
  timer_start(t, 250000, true); // Refresh multimeter screen every 250 ms

  update_mosfet(chip);
  render_multimeter(chip, 0.20f);
}
