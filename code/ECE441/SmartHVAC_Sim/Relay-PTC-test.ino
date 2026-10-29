
const int RELAY_PIN = 26;

// Change these if your relay behaves oppositely.
const int RELAY_ON  = LOW;
const int RELAY_OFF = HIGH;

void setup() {
  // Set the initial output state to OFF.
  digitalWrite(RELAY_PIN, RELAY_OFF);
  pinMode(RELAY_PIN, OUTPUT);

  Serial.begin(115200);
  Serial.println("ESP32 relay test starting");
  Serial.println("Heater should remain disconnected for this test.");
}

void loop() {
  Serial.println("Relay ON");
  digitalWrite(RELAY_PIN, RELAY_ON);
  delay(3000);

  Serial.println("Relay OFF");
  digitalWrite(RELAY_PIN, RELAY_OFF);
  delay(3000);
}
