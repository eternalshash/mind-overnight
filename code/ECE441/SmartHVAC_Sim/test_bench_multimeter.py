#!/usr/bin/env python3
"""
ECE 441 Smart HVAC - Live Wokwi / Arduino Bench Multimeter & Telemetry Verifier
================================================================================
Connects to Wokwi's live RFC2217 serial port (localhost:4000) in VS Code (or
physical USB serial /dev/cu.usbmodem* in the lab) to test Fan PWM adjustments,
PTC Heater relay switching, Voltage (V), Current (A), Power (W), and Total
Equivalent Circuit Resistance (Ohms).
"""

import json
import socket
import sys
import time

# Physical constants matching include/bench_hal.h & Andy/Kaleb's 10-26-29 Bench Report
V_SUPPLY_12V   = 12.00
V_RAIL_5V      = 5.00
R_FAN_WINDING  = 14.286  # GDSTIME 5015 5V Blower Fan (5.0V / 0.35A)
R_MOSFET_ON    = 0.028   # IRLZ44N Logic-Level N-MOSFET R_DS(on) @ V_GS=5V
R_PTC_HEATER   = 2.880   # 12V 50W PTC Heating Element (12V^2 / 50W)
I_MCU_QUIESCENT = 0.045  # Arduino Uno R4 + BME280 baseline logic draw (45 mA)
BUCK_EFF       = 0.88    # LM2596 DC-DC Buck Converter efficiency


def compute_circuit_state(fan_pct: float, heater_on: bool, temp_c: float = 20.5, rh_pct: float = 48.0, setpoint_c: float = 23.0, mode: str = "MANUAL"):
    fan_pwm = int(round((max(0.0, min(100.0, fan_pct)) / 100.0) * 255.0))
    duty = fan_pwm / 255.0
    v_gs = V_RAIL_5V * duty

    if fan_pwm > 0:
        i_fan_peak = V_RAIL_5V / (R_FAN_WINDING + R_MOSFET_ON)
        i_fan = duty * i_fan_peak
        v_fan_eff = duty * (V_RAIL_5V - (i_fan_peak * R_MOSFET_ON))
        r_fan_branch = V_RAIL_5V / i_fan
    else:
        i_fan = 0.0
        v_fan_eff = 0.0
        r_fan_branch = -1.0

    i_heater = (V_SUPPLY_12V / R_PTC_HEATER) if heater_on else 0.0
    r_heater = R_PTC_HEATER if heater_on else -1.0

    i_5v_total = I_MCU_QUIESCENT + i_fan
    i_total_load = i_5v_total + i_heater
    p_5v = V_RAIL_5V * i_5v_total
    p_heater = V_SUPPLY_12V * i_heater
    p_total = p_5v + p_heater
    i_12v_bus = i_heater + (p_5v / (V_SUPPLY_12V * BUCK_EFF))

    r_5v_rail = V_RAIL_5V / i_5v_total
    r_total_circuit = V_SUPPLY_12V / i_12v_bus
    air_vel = duty * 7.0

    return {
        "device_id": "ARDUINO-R4-HVAC-G2",
        "fan_mode": mode,
        "fan_speed_pct": round((fan_pwm * 100.0) / 255.0, 1),
        "fan_pwm": fan_pwm,
        "heater_relay": 1 if heater_on else 0,
        "temp_c": temp_c,
        "humidity": rh_pct,
        "setpoint_c": setpoint_c,
        "air_velocity_ms": round(air_vel, 2),
        "v_supply_12v": V_SUPPLY_12V,
        "v_rail_5v": V_RAIL_5V,
        "v_mosfet_gs": round(v_gs, 2),
        "v_fan_eff": round(v_fan_eff, 2),
        "i_mcu_a": I_MCU_QUIESCENT,
        "i_fan_a": round(i_fan, 3),
        "i_heater_a": round(i_heater, 3),
        "i_total_a": round(i_total_load, 3),
        "i_12v_bus_a": round(i_12v_bus, 3),
        "power_w": round(p_total, 2),
        "r_mosfet_ohm": R_MOSFET_ON if fan_pwm > 0 else -1.0,
        "r_fan_ohm": round(r_fan_branch, 2) if r_fan_branch > 0 else -1.0,
        "r_heater_ohm": r_heater,
        "r_5v_rail_ohm": round(r_5v_rail, 2),
        "r_total_circuit_ohm": round(r_total_circuit, 2),
    }


def try_live_wokwi_session(host="127.0.0.1", port=4000):
    try:
        sock = socket.create_connection((host, port), timeout=1.5)
        sock.settimeout(2.0)
        return sock
    except OSError:
        return None


def main():
    print("=" * 108)
    print(" ECE 441 SMART HVAC BENCH - LIVE TELEMETRY, FAN SPEED & CIRCUIT RESISTANCE MULTIMETER")
    print(" Hardware Target: Arduino Uno R4 + IRLZ44N MOSFET (Pin 9) + 12V PTC Relay (Pin 8) + BME280 (A4/A5)")
    print("=" * 108)

    sock = try_live_wokwi_session()
    if sock is not None:
        print("[CONNECTED] Attached to live Wokwi Simulator in VS Code via RFC2217 (localhost:4000)!\n")
        commands = ["AUTO\n", "FAN 0\n", "FAN 25\n", "FAN 50\n", "FAN 75\n", "FAN 100\n", "HEAT ON\n", "HEAT OFF\n", "AUTO\n"]
        for cmd in commands:
            print(f">>> Sending Command to Arduino: {cmd.strip()}")
            sock.sendall(cmd.encode("utf-8"))
            time.sleep(1.1)
            try:
                data = sock.recv(4096).decode("utf-8", errors="ignore")
                for line in data.splitlines():
                    if line.strip() and (line.startswith("{") or line.startswith("[MULTIMETER]")):
                        print("   ", line.strip())
            except socket.timeout:
                pass
        sock.close()
        return

    print("[INFO] Wokwi RFC2217 bridge (port 4000) starts when you click the green Play button in VS Code.")
    print("[SIMULATION SWEEP] Executing full Fan Speed (0% -> 100%) & PTC Heater Electrical Circuit Sweep:\n")

    header = (
        f"{'Command':<12} | {'Fan % (PWM)':<13} | {'V_GS':<6} | {'V_Fan':<6} | "
        f"{'I_Fan':<8} | {'I_Heat':<7} | {'I_Tot(12V)':<11} | {'Power':<7} | "
        f"{'R_Fan':<9} | {'R_5V_Rail':<10} | {'R_Total_Circuit'}"
    )
    print(header)
    print("-" * len(header))

    scenarios = [
        ("FAN 0",    0.0,   False, "MANUAL"),
        ("AUTO(20%)",20.0,  False, "AUTO"),
        ("FAN 35",   35.0,  False, "MANUAL"),
        ("FAN 50",   50.0,  False, "MANUAL"),
        ("FAN 75",   75.0,  False, "MANUAL"),
        ("FAN 100",  100.0, False, "MANUAL"),
        ("HEAT ON",  100.0, True,  "MANUAL+PTC"),
        ("AUTO+PTC", 85.0,  True,  "AUTO+PTC"),
    ]

    for cmd, pct, heat, mode in scenarios:
        s = compute_circuit_state(pct, heat, mode=mode)
        r_fan_str = f"{s['r_fan_ohm']:.2f} Ω" if s["r_fan_ohm"] > 0 else "OPEN (∞)"
        print(
            f"{cmd:<12} | {s['fan_speed_pct']:>5.1f}% ({s['fan_pwm']:>3d}) | "
            f"{s['v_mosfet_gs']:>4.2f}V | {s['v_fan_eff']:>4.2f}V | "
            f"{s['i_fan_a']*1000:>5.0f} mA | {s['i_heater_a']:>5.2f} A | "
            f"{s['i_total_a']:>4.3f}A({s['i_12v_bus_a']:>.2f}A)| {s['power_w']:>5.2f}W | "
            f"{r_fan_str:<9} | {s['r_5v_rail_ohm']:>6.2f} Ω  | {s['r_total_circuit_ohm']:>7.2f} Ω"
        )

    print("-" * len(header))
    print("\nSample Live Serial JSON Telemetry Packet (emitted every 1000 ms on Arduino Serial @ 115200 baud):")
    sample = compute_circuit_state(75.0, False, mode="MANUAL")
    print(json.dumps(sample))


if __name__ == "__main__":
    main()
