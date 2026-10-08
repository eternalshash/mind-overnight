// ECE 441 Experiment 3: Temperature Acquisition and Bluetooth Transmission
// Target Microcontroller: Arduino UNO R4 WiFi
// Sensor: Aosong AM2302 (DHT22) on Digital Pin 2
// Wireless Transceiver: HC-06 Bluetooth Module on Hardware Serial1 (38400 Baud)
// Author: Shashwat Choudhry

#include <dht.h>

dht DHT;                        // Instantiate DHT sensor driver object
const int DHT22_PIN = 2;        // Digital pin connected to DHT22 DATA line
const long BT_BAUD = 38400;     // HC-06 Bluetooth communication baud rate
const long USB_BAUD = 115200;   // USB Serial Monitor baud rate

void setup() {
  // Initialize USB Serial interface for local debugging
  Serial.begin(USB_BAUD);
  while (!Serial) {
    ; // Wait for USB connection
  }
  
  // Initialize Hardware UART (Serial1) on Pins 0 and 1 for HC-06
  Serial1.begin(BT_BAUD);
  
  Serial.println("==================================================");
  Serial.println("ECE 441 Lab 3: DHT22 Temperature Telemetry Active");
  Serial.println("Target: Raspberry Pi Gateway over Bluetooth RFCOMM");
  Serial.println("==================================================");
}

void loop() {
  // Read 40-bit pulse stream from DHT22 digital sensor
  int chk = DHT.read22(DHT22_PIN);
  
  // Retrieve temperature in Celsius from driver object
  float tempC = DHT.temperature;
  
  // Convert Celsius to Fahrenheit
  float tempF = tempC * 9.0 / 5.0 + 32.0;
  
  // Display reading locally on USB Serial Monitor
  Serial.print(tempF, 2);
  Serial.print("F   ");
  
  // Transmit floating point value to HC-06 Bluetooth module over Serial1
  Serial1.println(tempF, 2);
  
  // Confirm transmission completion locally
  Serial.println("Bluetooth transmission complete");
  
  // Delay 1000 milliseconds (1 second) between consecutive samples
  delay(1000);
}
