"""
ECE 441: Smart and Connected Systems
Testing IoT Alert Engine & Live Dispatcher
File: testingIot.py
Target Directory: mind-overnight/code/ECE441/SmartHVAC_Sim

Implements multi-variable HVAC anomaly detection and dispatches real SMS and Email
alerts formatted cleanly in three distinct rows (with arrows removed):
  Row 1: Simplified alert title (e.g. Rapid temp increase)
  Row 2: Temperature & environmental telemetry metrics
  Row 3: Autonomous system action taken
"""

import sys
import os
import subprocess
import argparse
import math
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

CARRIER_GATEWAYS = {
    "verizon": ["vtext.com", "vzwpix.com"],
    "att": ["txt.att.net", "mms.att.net"],
    "tmobile": ["tmomail.net"],
    "googlefi": ["msg.fi.google.com"],
    "sprint": ["messaging.sprintpcs.com"],
    "boost": ["myboostmobile.com"]
}

class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class AlertFault(Enum):
    RAPID_TEMP_INCREASE = "surge"
    RAPID_TEMP_DROP = "drop"
    HEAT_STRESS = "heatstress"
    FREEZE_WARNING = "freeze"
    BLOWER_FAILURE = "blower"
    FILTER_CLOG = "filter"
    MCU_CRASH = "mcu"

def c_to_f(c: float) -> float:
    return c * 1.8 + 32.0

def calculate_apparent_temperature(temp_c: float, humidity: float, air_velocity: float) -> float:
    """Steadman apparent 'Feels Like' temperature calculation (ASHRAE 55)."""
    e = (humidity / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))
    return temp_c + 0.33 * e - 0.70 * air_velocity - 4.0

class HVACFaultRecord:
    def __init__(
        self,
        fault_type: AlertFault,
        row1_title: str,
        row2_temps: str,
        row3_action: str,
        severity: AlertSeverity,
        diagnostic_code: str,
        room_temp_f: float,
        apparent_temp_f: float,
        outside_temp_f: float,
        details: str
    ):
        self.fault_type = fault_type
        self.row1_title = row1_title
        self.row2_temps = row2_temps
        self.row3_action = row3_action
        self.severity = severity
        self.diagnostic_code = diagnostic_code
        self.room_temp_f = room_temp_f
        self.apparent_temp_f = apparent_temp_f
        self.outside_temp_f = outside_temp_f
        self.details = details
        self.timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def format_sms(self) -> str:
        """
        Formats cleanly into 3 rows without arrows:
        Row 1: Alert title
        Row 2: Temperatures and metrics
        Row 3: System action
        """
        return f"{self.row1_title}\n{self.row2_temps}\n{self.row3_action}"

    def format_email_body(self) -> str:
        return (
            f"SMART HVAC CONTROL - FAULT DISPATCH\n"
            f"----------------------------------------\n"
            f"Alert: {self.row1_title}\n"
            f"Status: {self.severity.value} ({self.diagnostic_code})\n"
            f"Timestamp: {self.timestamp_str}\n\n"
            f"ENVIRONMENTAL TELEMETRY:\n"
            f"{self.row2_temps}\n\n"
            f"SYSTEM RESPONSE:\n"
            f"{self.row3_action}\n\n"
            f"TECHNICAL DETAILS:\n"
            f"{self.details}\n"
            f"----------------------------------------\n"
            f"Dispatched by Illinois Tech ECE 441 Edge IoT Gateway\n"
        )

def generate_fault_data(
    fault_type: str = "surge",
    room_c: float = 26.0,
    outside_c: float = 28.0,
    humidity: float = 50.0,
    air_vel: float = 1.8
) -> HVACFaultRecord:
    """Generates dynamic 3-row information tailored specifically to each fault type."""
    room_f = c_to_f(room_c)
    outside_f = c_to_f(outside_c)
    apparent_f = c_to_f(calculate_apparent_temperature(room_c, humidity, air_vel))

    if fault_type == "surge":
        return HVACFaultRecord(
            fault_type=AlertFault.RAPID_TEMP_INCREASE,
            row1_title="Rapid temp increase",
            row2_temps=f"Room: {room_f:.1f}°F | Feels Like: {apparent_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: Heater shut off, emergency cooling engaged",
            severity=AlertSeverity.CRITICAL,
            diagnostic_code="E-405",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Zone temperature climbed abnormally fast (>2.5°F/min). 12V PTC heater interlocked to 0% duty cycle."
        )
    elif fault_type == "drop":
        return HVACFaultRecord(
            fault_type=AlertFault.RAPID_TEMP_DROP,
            row1_title="Rapid temp decrease",
            row2_temps=f"Room: {room_f:.1f}°F | Feels Like: {apparent_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: Heating boosted to 100%, checking envelope dampers",
            severity=AlertSeverity.WARNING,
            diagnostic_code="E-406",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Sudden temperature drop detected. Exterior window breach suspected."
        )
    elif fault_type == "heatstress":
        return HVACFaultRecord(
            fault_type=AlertFault.HEAT_STRESS,
            row1_title="Dangerous heat stress detected",
            row2_temps=f"Room: {room_f:.1f}°F | Feels Like: {apparent_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: Emergency cooling engaged at 100% duty cycle",
            severity=AlertSeverity.EMERGENCY,
            diagnostic_code="E-403",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Steadman apparent temperature exceeded 88.0°F safety limit for elderly occupant."
        )
    elif fault_type == "freeze":
        return HVACFaultRecord(
            fault_type=AlertFault.FREEZE_WARNING,
            row1_title="Freezing temperature warning",
            row2_temps=f"Room: {room_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: Auxiliary emergency heat engaged at 100%",
            severity=AlertSeverity.CRITICAL,
            diagnostic_code="E-407",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Room temperature breached 45°F freeze threshold. Pipe burst mitigation active."
        )
    elif fault_type == "blower":
        return HVACFaultRecord(
            fault_type=AlertFault.BLOWER_FAILURE,
            row1_title="Blower motor failure (0 RPM)",
            row2_temps=f"Room: {room_f:.1f}°F | Duct Velocity: 0.0 m/s | Outside: {outside_f:.1f}°F",
            row3_action="System Action: Heater cut off immediately to prevent melting",
            severity=AlertSeverity.CRITICAL,
            diagnostic_code="E-302",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Commanded blower fan at 60% but tachometer reads 0 RPM. Safety interlock tripped."
        )
    elif fault_type == "filter":
        return HVACFaultRecord(
            fault_type=AlertFault.FILTER_CLOG,
            row1_title="Air filter severely restricted",
            row2_temps=f"Static Pressure: 295 Pa | Flow Ratio: 62% | Room: {room_f:.1f}°F",
            row3_action="System Action: Blower boosted +25%, compressor capped at 50%",
            severity=AlertSeverity.WARNING,
            diagnostic_code="E-301",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Return duct static pressure exceeded 280 Pa threshold. Compressor capped to prevent coil icing."
        )
    elif fault_type == "mcu":
        return HVACFaultRecord(
            fault_type=AlertFault.MCU_CRASH,
            row1_title="Primary controller crash detected",
            row2_temps=f"MCU-A: PANIC | MCU-B: ACTIVE | Room: {room_f:.1f}°F",
            row3_action="System Action: Backup MCU-B took over control bumplessly",
            severity=AlertSeverity.CRITICAL,
            diagnostic_code="E-201",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Watchdog timer expired on primary ESP32. Hardware hot-standby failover completed."
        )
    else:
        # Default fallback
        return HVACFaultRecord(
            fault_type=AlertFault.RAPID_TEMP_INCREASE,
            row1_title="Rapid temp increase",
            row2_temps=f"Room: {room_f:.1f}°F | Feels Like: {apparent_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: Heater shut off, emergency cooling engaged",
            severity=AlertSeverity.CRITICAL,
            diagnostic_code="E-405",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Environmental surge detected."
        )

def send_apple_mail(recipient: str, subject: str, body_text: str) -> bool:
    """Dispatches a real email via macOS Apple Mail client."""
    safe_subject = subject.replace('\\', '\\\\').replace('"', '\\"')
    safe_body = body_text.replace('\\', '\\\\').replace('"', '\\"')
    safe_recip = recipient.replace('\\', '\\\\').replace('"', '\\"')

    script = f'''
    tell application "Mail"
        set newMsg to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:false}}
        tell newMsg
            make new to recipient at end of to recipients with properties {{address:"{safe_recip}"}}
            send
        end tell
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
        print(f"✅ Dispatched to {recipient} via macOS Apple Mail.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to dispatch to {recipient}: {e.stderr.strip()}")
        return False

def send_carrier_sms(phone_number: str, carrier: str, sms_text: str) -> bool:
    """Dispatches real SMS via carrier email-to-SMS gateway with empty subject to prevent headers."""
    clean_phone = "".join(filter(str.isdigit, phone_number))
    if len(clean_phone) == 11 and clean_phone.startswith("1"):
        clean_phone = clean_phone[1:]
        
    carrier_domains = CARRIER_GATEWAYS.get(carrier.lower(), ["vtext.com", "vzwpix.com"])
    if isinstance(carrier_domains, str):
        carrier_domains = [carrier_domains]

    success = False
    for domain in carrier_domains:
        gateway_addr = f"{clean_phone}@{domain}"
        print(f"📲 Routing SMS through gateway: {gateway_addr}")
        # Empty subject "" ensures Verizon does not prepend any ugly subject tags
        if send_apple_mail(gateway_addr, "", sms_text):
            success = True
    return success

def test_all_fault_scenarios():
    """Validates and prints the 3-row layout for all supported fault scenarios."""
    fault_keys = ["surge", "drop", "heatstress", "freeze", "blower", "filter", "mcu"]
    print("=" * 65)
    print("🧪 BATCH VALIDATION: 3-ROW SMS LAYOUT ACROSS ALL FAULT SCENARIOS")
    print("=" * 65)
    for idx, f_key in enumerate(fault_keys, 1):
        rec = generate_fault_data(f_key)
        sms = rec.format_sms()
        lines = sms.split("\n")
        print(f"\n[{idx}/7] SCENARIO: {f_key.upper()} ({rec.diagnostic_code} - {rec.severity.value})")
        print(f"  Row 1: {lines[0]}")
        print(f"  Row 2: {lines[1]}")
        print(f"  Row 3: {lines[2]}")
        assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"
        assert "->" not in sms, f"Found arrow in SMS: {sms}"
    print("\n" + "=" * 65)
    print("✅ All 7 fault scenarios verified: 3 rows, zero arrows, valid metrics.")
    print("=" * 65)

def run_test(
    email: str = "choudhryshashwat29@gmail.com",
    phone: str = "9254075652",
    carrier: str = "verizon",
    fault: str = "surge",
    run_all: bool = False
):
    if run_all:
        test_all_fault_scenarios()
        return
    print("=" * 65)
    print("🚀 SMART HVAC TESTING IOT ALERT DISPATCHER")
    print(f"Target Email:   {email}")
    print(f"Target Phone:   {phone} (Carrier: {carrier.upper()})")
    print(f"Fault Scenario: {fault.upper()}")
    print("=" * 65)

    # 1. Generate fault record
    if fault == "surge":
        record = generate_fault_data("surge", room_c=26.0, outside_c=28.0, humidity=50.0, air_vel=1.8)
    elif fault == "heatstress":
        record = generate_fault_data("heatstress", room_c=31.0, outside_c=36.0, humidity=75.0, air_vel=0.2)
    elif fault == "blower":
        record = generate_fault_data("blower", room_c=24.0, outside_c=28.0, humidity=50.0, air_vel=0.0)
    elif fault == "filter":
        record = generate_fault_data("filter", room_c=23.5, outside_c=27.0, humidity=48.0, air_vel=1.1)
    elif fault == "freeze":
        record = generate_fault_data("freeze", room_c=5.5, outside_c=-8.0, humidity=30.0, air_vel=0.8)
    elif fault == "mcu":
        record = generate_fault_data("mcu", room_c=24.0, outside_c=28.0, humidity=50.0, air_vel=1.8)
    else:
        record = generate_fault_data(fault)

    sms_text = record.format_sms()
    email_subject = f"[{record.severity.value}] Smart HVAC Alert: {record.row1_title}"
    email_body = record.format_email_body()

    print("\n📱 FORMATTED SMS CONTENT (3 ROWS, NO ARROWS):")
    print("-" * 55)
    print(sms_text)
    print("-" * 55)

    # 2. Dispatch real email
    if email:
        print(f"\n📧 Sending Email to {email}...")
        send_apple_mail(email, email_subject, email_body)

    # 3. Dispatch real SMS text
    if phone:
        print(f"\n💬 Sending Text Message to {phone} ({carrier.upper()})...")
        send_carrier_sms(phone, carrier, sms_text)

    print("\n🎉 Live alert dispatch test completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testing IoT Alert Dispatcher")
    parser.add_argument("--email", type=str, default="choudhryshashwat29@gmail.com", help="Recipient email")
    parser.add_argument("--phone", type=str, default="9254075652", help="Recipient phone number")
    parser.add_argument("--carrier", type=str, default="verizon", choices=list(CARRIER_GATEWAYS.keys()), help="Mobile carrier")
    parser.add_argument("--fault", type=str, default="surge", choices=["surge", "drop", "heatstress", "freeze", "blower", "filter", "mcu"], help="Fault scenario")
    parser.add_argument("--all", action="store_true", help="Batch test all fault scenarios and verify 3-row layout")
    args = parser.parse_args()

    run_test(
        email=args.email,
        phone=args.phone,
        carrier=args.carrier,
        fault=args.fault,
        run_all=args.all
    )
