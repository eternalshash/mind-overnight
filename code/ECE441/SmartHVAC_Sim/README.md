# Smart HVAC Control – Residential Digital Twin

Welcome to the **Smart HVAC Control** project for ECE 441 (Smart and Connected Systems). This project is an interactive digital twin simulation of a residential suite equipped with an advanced, dual-ESP32 HVAC control system.

The simulation models real-world thermodynamics, indoor air quality (IAQ), duct airflow dynamics, and power consumption, all autonomously regulated by a custom split-range PID controller.

## View the Simulation

**[Click Here to Run the Simulation Live](https://eternalshash.github.io/mind-overnight/code/ECE441/SmartHVAC_Sim/simulation/index.html)** 

*(Note: To make this link work, you must enable GitHub Pages on your repository. Go to Settings > Pages, set the source to "Deploy from a branch", select `main`, and click Save. The link will be live after 1 minute!)*

## How to Interact With It

The interface is divided into three main sections, designed to look like a 2D architectural CAD blueprint.

1. **The Blueprint (Left)**
   - This is the physical room environment. You will see the supply ducts (blue/red particles), the return vent, the dual-MCU thermostat, and the bed zone.
   - When a fault occurs, a colored highlight circle will appear over the affected device explaining exactly what the ESP32 is doing to solve it.

2. **Telemetry & Forecast (Top Right)**
   - Displays real-time charts for the simulated environment.
   - Use the tabs (`POWER`, `FORECAST`, `THERMAL`, `AIRFLOW`, `AIR QUALITY`) to switch between different live data views.

3. **Fault Injection & ESP32 Diagnostics (Bottom Right)**
   - **Inject Faults:** Use the toggle switches on the left side of this panel to simulate real-world hardware failures (e.g., *Primary ESP32 crash*, *Blower motor failure*, *Wildfire smoke*).
   - **Controller Response:** Watch the right side of this panel. You'll see the ESP32's immediate response, actuator outputs (PWM duty cycles), and a scrolling event log detailing the firmware's mitigation strategy.
   - **Sliders:** Adjust the desired thermostat setpoint, outdoor temperature, or energy demand limits using the sliders at the bottom to see how the PID controller adapts.

## Core Features Modeled
- **Thermodynamic Mass:** Realistic heat capacity, specific heat of air, and envelope heat transfer.
- **Fail-Safe Redundancy:** Watchdog timers enable a hot-standby ESP32 (MCU-B) to take over seamlessly if the primary MCU crashes.
- **Air Quality (IAQ):** Simulates VOC/CO2 buildup requiring ventilation purges, and PM2.5 smoke events requiring damper lockouts and recirculation.
- **Hardware Faults:** Models filter clogging (static pressure rise), blower failures, sensor drift cross-checking, and cloud/Wi-Fi outages.

## Development & Contribution Guide
For instructions on setting up the ESP32 build toolchain in PlatformIO, installing code libraries, configuring Wokwi simulation in VS Code, and submitting Pull Requests, please review the [Team Contribution Guide](CONTRIBUTING.md).

