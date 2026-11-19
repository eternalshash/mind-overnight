// =============================================================================
// ECE 441: SMART HVAC CONTROL — ARDUINO UNO R4 WIFI MAC ADDRESS FINDER
// Flash this sketch to your Arduino UNO R4 WiFi in the lab.
// Open Serial Monitor at 115200 baud to view your ESP32-S3 MAC Address.
// Register this MAC address at: https://iot.iit.edu
// =============================================================================

#include <WiFiS3.h>

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  delay(1000);
  Serial.println();
  Serial.println("=================================================");
  Serial.println("       ECE 441 SMART HVAC: MAC ADDRESS FINDER     ");
  Serial.println("       Arduino UNO R4 WiFi (ESP32-S3 Co-Proc)    ");
  Serial.println("=================================================");

  byte mac[6];
  WiFi.macAddress(mac);

  Serial.print("Hardware MAC Address: ");
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 0x10) {
      Serial.print("0");
    }
    Serial.print(mac[i], HEX);
    if (i < 5) {
      Serial.print(":");
    }
  }
  Serial.println();
  Serial.println();
  Serial.println("NEXT STEPS:");
  Serial.println("1. Go to: https://iot.iit.edu on your laptop or phone");
  Serial.println("2. Sign in with your MyIIT portal credentials");
  Serial.println("3. Register this MAC address for device 'ECE441-HVAC-Arduino'");
  Serial.println("4. Copy the generated WPA2-Personal passphrase (PSK)");
  Serial.println("5. Run: python3 generate_secrets.py to save your credentials");
  Serial.println("=================================================");
}

void loop() {
  // Blink onboard LED to show active state
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
}
