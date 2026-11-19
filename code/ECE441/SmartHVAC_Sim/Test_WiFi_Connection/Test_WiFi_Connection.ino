// =============================================================================
// ECE 441: SMART HVAC CONTROL — ARDUINO UNO R4 WIFI CONNECTION TESTER
// Standalone sketch to test connectivity to Illinois Tech's 'IIT-IoT' network.
// Board: Arduino UNO R4 WiFi (ESP32-S3 Co-Processor)
// =============================================================================

#include <WiFiS3.h>

// Campus Wi-Fi Credentials from iot.iit.edu
const char ssid[] = "IIT-IoT";
const char pass[] = "XtAOhMfEQ7yeLeIVOSgHdv7bjNOxtqH7A1XjyzCpTsXRr";

int status = WL_IDLE_STATUS;
WiFiSSLClient client;

void printMacAddress(byte mac[]) {
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 0x10) Serial.print("0");
    Serial.print(mac[i], HEX);
    if (i < 5) Serial.print(":");
  }
  Serial.println();
}

void printCurrentNet() {
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  byte bssid[6];
  WiFi.BSSID(bssid);
  Serial.print("BSSID: ");
  printMacAddress(bssid);

  long rssi = WiFi.RSSI();
  Serial.print("Signal Strength (RSSI): ");
  Serial.print(rssi);
  Serial.println(" dBm");

  byte encryption = WiFi.encryptionType();
  Serial.print("Encryption Type: ");
  Serial.println(encryption, HEX);
  Serial.println();
}

void printWifiData() {
  IPAddress ip = WiFi.localIP();
  Serial.print("Assigned IP Address: ");
  Serial.println(ip);

  IPAddress subnet = WiFi.subnetMask();
  Serial.print("Subnet Mask: ");
  Serial.println(subnet);

  IPAddress gateway = WiFi.gatewayIP();
  Serial.print("Gateway IP: ");
  Serial.println(gateway);

  Serial.println();
}

void testInternetAccess() {
  Serial.println("\nTesting Outbound Network Connectivity...");

  // Test 1: Check Cloud MQTT Port 8883
  Serial.print("1. Connecting to MQTT Broker (broker.hivemq.com:8883)... ");
  if (client.connect("broker.hivemq.com", 8883)) {
    Serial.println("SUCCESS! Port 8883 is reachable.");
    client.stop();
  } else {
    Serial.println("Warning: Could not connect to port 8883.");
  }

  // Test 2: Check standard HTTPS Port 443
  Serial.print("2. Connecting to HTTPS Gateway (www.google.com:443)... ");
  if (client.connect("www.google.com", 443)) {
    Serial.println("SUCCESS! Outbound HTTPS is working.");
    client.stop();
  } else {
    Serial.println("Warning: HTTPS port check failed.");
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  delay(1000);
  Serial.println();
  Serial.println("========================================================");
  Serial.println("      ECE 441: ARDUINO UNO R4 WIFI CONNECTION TEST      ");
  Serial.println("========================================================");

  // Check module firmware version
  String fv = WiFi.firmwareVersion();
  Serial.print("ESP32-S3 Firmware Version: ");
  Serial.println(fv);

  byte mac[6];
  WiFi.macAddress(mac);
  Serial.print("Hardware MAC Address:     ");
  printMacAddress(mac);

  Serial.print("Connecting to SSID:        ");
  Serial.println(ssid);

  // Connect loop
  unsigned long startTime = millis();
  status = WiFi.begin(ssid, pass);

  int dots = 0;
  while (status != WL_CONNECTED && (millis() - startTime < 20000)) {
    delay(500);
    Serial.print(".");
    dots++;
    if (dots % 30 == 0) Serial.println();
    status = WiFi.status();
    // Blink LED while searching
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }
  Serial.println();

  if (status == WL_CONNECTED) {
    digitalWrite(LED_BUILTIN, HIGH); // Solid ON = Connected!
    Serial.println("\n========================================================");
    Serial.println("       SUCCESS! CONNECTED TO ILLINOIS TECH IIT-IoT!     ");
    Serial.println("========================================================");
    printWifiData();
    printCurrentNet();
    testInternetAccess();
    Serial.println("========================================================");
    Serial.println("Ready to flash SmartHVAC_Arduino_Bench.ino!");
    Serial.println("========================================================");
  } else {
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("\n[ERROR] Connection failed or timed out.");
    Serial.print("Status code: ");
    Serial.println(WiFi.status());
    Serial.println("\nTroubleshooting Tips:");
    Serial.println("1. Verify registration on https://iot.iit.edu for MAC 70:04:1D:D4:F6:68");
    Serial.println("2. Confirm you are in range of IIT-IoT wireless AP");
    Serial.println("3. Ensure the passkey matches iot.iit.edu");
  }
}

void loop() {
  // Periodic status heartbeat every 10 seconds
  static unsigned long lastHeartbeat = 0;
  if (millis() - lastHeartbeat >= 10000) {
    lastHeartbeat = millis();
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("[HEARTBEAT] Connected to IIT-IoT | Signal RSSI: ");
      Serial.print(WiFi.RSSI());
      Serial.print(" dBm | IP: ");
      Serial.println(WiFi.localIP());
      digitalWrite(LED_BUILTIN, HIGH);
    } else {
      Serial.println("[HEARTBEAT] Disconnected! Attempting reconnect...");
      digitalWrite(LED_BUILTIN, LOW);
      WiFi.begin(ssid, pass);
    }
  }
}
