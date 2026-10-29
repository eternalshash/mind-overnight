
// IRLZ24N MOSFET Fan Speed Control
// Compatible with Arduino Uno and classic Nano

const int fanPin = 9;  // PWM-capable pin connected to MOSFET gate

void setup() {
  pinMode(fanPin, OUTPUT);
  Serial.begin(9600);

  Serial.println("MOSFET Fan Speed Test");
}

void loop() {
  // Fan OFF
  Serial.println("Fan OFF");
  analogWrite(fanPin, 0);
  delay(3000);

  // Approximately 50% duty cycle
  Serial.println("Fan at 50%");
  analogWrite(fanPin, 128);
  delay(3000);

  // Approximately 75% duty cycle
  Serial.println("Fan at 75%");
  analogWrite(fanPin, 191);
  delay(3000);

  // Full power
  Serial.println("Fan at 100%");
  analogWrite(fanPin, 255);
  delay(3000);
}
