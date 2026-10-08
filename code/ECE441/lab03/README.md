# ECE 441: Smart and Connected Systems / Internet of Things
## Experiment No. 03: Wireless Data Acquisition Using Temperature Sensor

**Author:** Shashwat Choudhry  
**Laboratory Partners:** Andy Tran, Kaleb Cowgur, Haron Abuelhija  
**Course:** ECE 441 Fall 2026  
**Instructors:** Dr. Jafar Saniie & Prof. Tianyang Fang  
**Department:** Electrical and Computer Engineering, Illinois Institute of Technology  
**Experiment Date:** October 01, 2026  
**Report Due Date:** October 08, 2026  

---

## 1. Directory Contents

```
lab03/
├── lab03ECE441.docx               # Formal Laboratory Report (Native Apple Pages / MS Word)
├── ECELabReport03441.pdf           # Formal Laboratory Report (Exported PDF)
├── README.md                      # Project documentation and reproduction guide
├── src/
│   ├── arduino_hc06_config.ino    # Arduino sketch to program HC-06 AT parameters (Name, PIN, 38400 baud)
│   ├── arduino_dht22_tx.ino       # Arduino sketch for DHT22 sensor acquisition and Bluetooth serial transmission
│   ├── lab3.py                    # Raspberry Pi Python gateway daemon (RFCOMM socket to ThingSpeak REST API)
│   └── ble_temperature_client.py  # Modern asynchronous Python BLE client implementation (using Bleak)
└── media/
    ├── Figure1_circuit_assembly.jpg   # Physical breadboard circuit (Arduino UNO R4, HC-06, DHT22)
    ├── Figure2_serial_monitor.jpg     # Arduino IDE Serial Monitor verification (COM10 @ 9600 baud)
    ├── Figure3_bluetoothctl_pairing.jpg # Raspberry Pi bluetoothctl discovery and pairing log
    ├── Figure4_telemetry_pipeline.jpg # Dual-display view: lab3.py terminal and ThingSpeak cloud portal
    ├── Figure5_thingspeak_chart.jpg   # Live ThingSpeak Field 1 real-time temperature graph
    └── Figure6_thingspeak_api_keys.jpg# ThingSpeak Channel Settings and Write API Key configuration
```

---

## 2. System Architecture Overview

This experiment demonstrates a distributed, multi-tier Internet of Things (IoT) wireless environmental monitoring platform:
1. **Edge Sensing Tier:** An **Arduino UNO R4 WiFi** microcontroller interfaces with an **Aosong AM2302 (DHT22)** digital temperature and humidity sensor via Digital Pin 2 using single-wire bus timing pulses.
2. **Wireless PAN Bridge:** An **HC-06 Bluetooth Transceiver** (Bluetooth 2.0+EDR) configured with broadcast name `ece441` (also verified as `ANDYTRAN`), pairing passkey `1234`, and elevated communication rate of `38400 baud` receives telemetry across the dedicated hardware `Serial1` UART (Pins 0 RX and 1 TX).
3. **IoT Gateway Tier:** A **Raspberry Pi 3 Model B+** running Raspberry Pi OS Linux executes an interactive `bluetoothctl` session to pair and establish persistent trust with HC-06 MAC address `00:14:03:05:5B:F3`. The Python script `lab3.py` binds an RFCOMM Bluetooth socket on Channel 1 to stream incoming byte payloads.
4. **Cloud Analytics Tier:** The Raspberry Pi parses incoming telemetry and dispatches RESTful HTTP POST requests to the **MathWorks ThingSpeak** cloud service (Channel ID `3518177`, Field 1 `Temperature`) with 15-second rate limiting, rendering dynamic real-time time-series plots.

---

## 3. Hardware Pin Mapping

| Subsystem / Device | Device Pin Name | Arduino UNO Pin | Raspberry Pi Pin | Signal Description and Electrical Function |
| :--- | :--- | :--- | :--- | :--- |
| **AM2302 / DHT22** | Pin 1 (VDD) | 5V Power Rail | N/A | 5.0V DC regulated power delivery rail |
| **AM2302 / DHT22** | Pin 2 (DATA) | Digital Pin 2 | N/A | Single-bus bidirectional serial data line (with 10 kΩ pull-up) |
| **AM2302 / DHT22** | Pin 3 (NC) | No Connection | N/A | Unconnected internal null pin |
| **AM2302 / DHT22** | Pin 4 (GND) | GND Rail | N/A | System common electrical ground reference |
| **HC-06 Module** | VCC Pin | 5V Power Rail | N/A | Power input to onboard 3.3V LDO regulator |
| **HC-06 Module** | GND Pin | GND Rail | N/A | System common ground return |
| **HC-06 Module** | TXD Pin | Digital Pin 0 (RX1) | N/A | Module serial transmit output to Arduino hardware UART receive |
| **HC-06 Module** | RXD Pin | Digital Pin 1 (TX1) | N/A | Module serial receive input from Arduino hardware UART transmit |
| **Raspberry Pi 3B+**| Onboard Bluetooth | N/A (Over Air) | BCM43438 Controller | Receives wireless 2.4 GHz RFCOMM Bluetooth packets from HC-06 |
| **Raspberry Pi 3B+**| Onboard Wi-Fi | N/A (Over Air) | BCM43438 Controller | Connects to campus network to dispatch HTTP POST telemetry to ThingSpeak |

---

## 4. Software Execution Instructions

### A. Arduino HC-06 AT Configuration
1. Open `src/arduino_hc06_config.ino` in Arduino IDE 2.x.
2. Select target board: `Arduino UNO R4 WiFi` on COM10.
3. Open Serial Monitor at 115200 baud with **No line ending**.
4. The sketch automatically sends:
   - `AT` -> Returns `OK`
   - `AT+VERSION` -> Returns `OKlinvorV1.8`
   - `AT+NAMEece441` -> Returns `OKsetname`
   - `AT+PIN1234` -> Returns `OKsetPIN`
   - `AT+BAUD6` -> Returns `OK38400`
5. The sketch reinitializes `Serial1` at 38400 baud and confirms communication.

### B. Arduino Sensor Telemetry Firmware
1. Open `src/arduino_dht22_tx.ino` in Arduino IDE.
2. Ensure the `dht.h` library is installed.
3. Upload to Arduino UNO R4 WiFi.
4. Serial Monitor displays live temperature in Fahrenheit and confirms `Bluetooth transmission complete` every 1000 ms.

### C. Raspberry Pi Bluetooth Pairing & Gateway Run
1. Open terminal on Raspberry Pi:
   ```bash
   sudo rm -rf /var/lib/bluetooth/*/cache/*
   sudo systemctl restart bluetooth
   bluetoothctl
   ```
2. Inside `bluetoothctl`:
   ```bash
   agent on
   default-agent
   scan on
   # Locate HC-06 MAC address (00:14:03:05:5B:F3)
   pair 00:14:03:05:5B:F3
   # Enter PIN: 1234
   trust 00:14:03:05:5B:F3
   exit
   ```
3. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install -y bluetooth libbluetooth-dev
   sudo python3 -m pip install thingspeak
   ```
4. Run the gateway script:
   ```bash
   cd src/
   sudo python3 lab3.py
   ```
5. Observe the HC-06 LED transition from flashing red to **solid red**, confirming an active RFCOMM link. Live temperatures will display in the console and synchronize with ThingSpeak every 15 seconds.

---

## 5. ThingSpeak Cloud Analytics Configuration

* **Channel ID:** `3518177`
* **Channel Name:** `ECE 441 LAB 3`
* **Field 1:** `Temperature`
* **Write API Key:** `INYZROAEU08IFDYH`
* **Endpoint URL:** `https://api.thingspeak.com/update`
* **Update Interval:** 15.0 seconds (rate limit constraint enforced in gateway software)

---

## 6. Demonstration Video Archive

* **Video File Name:** `20261001_152834000_iOS.MOV`
* **Recording Specifications:** 30 seconds, 1920x1080 Full HD, QuickTime MOV container
* **Demonstrated Milestones:**
  1. Breadboard circuit assembly verification (Arduino UNO R4 WiFi, HC-06, DHT22).
  2. Active Bluetooth connection verification (solid continuous red LED on HC-06).
  3. Real-time serial frame reception in Raspberry Pi `lab3.py` console.
  4. Instantaneous graphical update on MathWorks ThingSpeak Field 1 live chart.
* **SharePoint Media Archive Link:**  
  [Illinois Tech ECE 441 Group 2 SharePoint Media Folder](https://iit0-my.sharepoint.com/shared?id=%2Fpersonal%2Fatran14%5Fhawk%5Fillinoistech%5Fedu%2FDocuments%2FECE441%20F26%20Meeting%20Logs%20Group%202%2FLAB03%5FMEDIA&listurl=%2Fpersonal%2Fatran14%5Fhawk%5Fillinoistech%5Fedu%2FDocuments&viewid=ebcd2010%2D1bab%2D4115%2D97c0%2Dcf8025f751ee&sharingv2=true&fromShare=true&at=9&CT=1791418467450&OR=OWA%2DNT%2DMail&SI=NonSentItems&SLSync=F&FolderCTID=0x012000D40DDD3DEF2FA240AD38CC281BB1D868)
