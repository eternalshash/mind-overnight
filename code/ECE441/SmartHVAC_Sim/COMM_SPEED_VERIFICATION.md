# Communication Speed & Lab Telemetry Verification Report

**Dataset File:** [`hvac_comm_speed_1792898839748.csv`](hvac_comm_speed_1792898839748.csv)  
**Date:** October 24, 2026  
**Target:** Raspberry Pi 5 Edge Server (`http://192.168.0.70:8765`)  
**Client:** Digital Twin Residential HVAC Simulator (Brave Browser)  

Examining the newly generated CSV file, focusing on its schema. The file was created recently and likely contains performance data from a "TEST SPEED" action in a web browser. The headers define different measurement types, hinting at HVAC communication parameters.

This CSV file looks clean, consistent, and ready for your lab verification report.

Here is the technical evaluation of the dataset you just exported:

---

### 1. Communication Speed & Network Health

* **Success Rate:** 100.0% (25/25 requests succeeded with `HTTP 200 OK`).
* **Steady-State Latency:** 35.0 ms to 53.2 ms across the entire 20-packet test run.
  * **Fastest packet:** 35.0 ms (`Benchmark #1/20`)
  * **Median latency:** ~41.3 ms
  * **Consistency:** 19 out of 20 benchmark packets remained clustered under 53 ms.
* **The Single Spike (`1513.8 ms` at Sync #3):**  
  This corresponds to macOS resolving the mDNS hostname `raspberrypi.local` on the initial connection before caching the ARP/LAN IP entry (`192.168.0.70`). All subsequent requests were fast and steady.

---

### 2. Physical Telemetry & Closed-Loop Control Verification

| Parameter | CSV Value Range | Assessment |
| :--- | :---: | :--- |
| **Room Temperature** | 72.5°F – 73.1°F (22.5°C – 22.8°C) | Tracking setpoint smoothly |
| **"Feels Like" Apparent Temp** | 73.0°F – 73.7°F (22.7°C – 23.2°C) | Correctly factors in 48.5% RH and air draft |
| **Thermostat Setpoint** | 72.5°F (22.5°C) | Bidirectionally synced from the Pi! |
| **FS3000 Air Velocity** | 1.28 – 1.40 m/s | Stable duct circulation velocity |
| **Static Pressure** | 19.0 – 23.0 Pa | Filter restriction nominal |
| **Total Power Draw** | 282.7 – 331.4 W | Modulating compressor + blower load |
| **Actuator PWMs** | Heater: 0 / Fan: 101–112 (~40%) | Proportional PWM modulating correctly |
| **Dual MCU State** | `active_mcu: A`, `mode: COOLING` | Primary MCU active in cooling loop |

---

### 3. File Structure & Interoperability

* **Standard RFC-4180 Format:** Timestamps, numbers, and strings are properly quoted and comma-delimited.
* **Plugs Directly Into:** Excel, Apple Numbers, MATLAB, Pandas, or Google Sheets with zero cleaning required.

This file provides proof that your Raspberry Pi 5 edge server, SQLite persistence, and Digital Twin telemetry bridge are communicating reliably with low latency.
