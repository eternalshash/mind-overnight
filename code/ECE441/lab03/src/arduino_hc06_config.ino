// ECE 441 Experiment 3: HC-06 Bluetooth Module AT Configuration Program
// Target Microcontroller: Arduino UNO R4 WiFi (Hardware Serial1 on Pins 0/1)
// Author: Shashwat Choudhry

const long DEFAULT_BAUD = 9600;  // HC-06 factory default baud rate
const long TARGET_BAUD = 38400;  // Target laboratory operational baud rate

void setup() {
  // Initialize USB Serial interface for PC Serial Monitor debugging
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for USB connection
  }
  
  // Initialize Hardware UART (Serial1) connected to HC-06 (Pins 0 RX, 1 TX)
  Serial1.begin(DEFAULT_BAUD);
  
  Serial.println("==================================================");
  Serial.println("ECE 441 Lab 3: HC-06 Bluetooth AT Configuration");
  Serial.println("==================================================");
  Serial.println("Transmitting AT commands to HC-06 module...");
  
  delay(1000); // Allow hardware power to stabilize
  
  // Test connection
  sendCommand("AT");
  delay(1000);
  
  // Query firmware revision
  sendCommand("AT+VERSION");
  delay(1000);
  
  // Set broadcast name to ece441 (or ANDYTRAN)
  sendCommand("AT+NAMEece441");
  delay(1000);
  
  // Configure pairing PIN to 1234
  sendCommand("AT+PIN1234");
  delay(1000);
  
  // Elevate baud rate to 38400 (AT+BAUD6)
  sendCommand("AT+BAUD6");
  delay(1000);
  
  // Reinitialize Serial1 to 38400 baud to verify new communication speed
  Serial1.begin(TARGET_BAUD);
  Serial.println("Reinitialized Serial1 at 38400 baud.");
  delay(500);
  sendCommand("AT");
}

void sendCommand(const char* cmd) {
  Serial.print("Sending Command: ");
  Serial.println(cmd);
  
  // Transmit command characters without carriage return or newline
  Serial1.print(cmd);
  
  // Await and display response from HC-06
  delay(500);
  Serial.print("Response: ");
  while (Serial1.available()) {
    char c = Serial1.read();
    Serial.write(c);
  }
  Serial.println();
}

void loop() {
  // Bi-directional serial passthrough bridge
  if (Serial.available()) {
    Serial1.write(Serial.read());
  }
  if (Serial1.available()) {
    Serial.write(Serial1.read());
  }
}
