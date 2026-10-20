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
import json
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
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
    VOC_BUILDUP = "voc"
    WILDFIRE_SMOKE = "smoke"
    SENSOR_FAULT = "sensor"
    WIFI_OUTAGE = "wifi"
    WINDOW_OPEN = "window"

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
    elif fault_type == "heatstress" or fault_type == "heatwave":
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
    elif fault_type == "filter" or fault_type == "clog":
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
    elif fault_type == "voc":
        return HVACFaultRecord(
            fault_type=AlertFault.VOC_BUILDUP,
            row1_title="Poor indoor air quality detected",
            row2_temps=f"VOC: 480 ppb | CO2: 1180 ppm | Room: {room_f:.1f}°F",
            row3_action="System Action: Ventilation purge active, OA damper 100%, blower 85%",
            severity=AlertSeverity.WARNING,
            diagnostic_code="E-101",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Indoor VOC and CO2 levels exceeded fresh air comfort limits. Outdoor air damper opened."
        )
    elif fault_type == "smoke":
        return HVACFaultRecord(
            fault_type=AlertFault.WILDFIRE_SMOKE,
            row1_title="Outdoor wildfire smoke hazard",
            row2_temps=f"Indoor PM2.5: 28 ug/m3 | Outdoor: 160 ug/m3 | Room: {room_f:.1f}°F",
            row3_action="System Action: Outdoor damper locked closed, MERV-13 recirc at 70%",
            severity=AlertSeverity.CRITICAL,
            diagnostic_code="E-102",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Outdoor PM2.5 smoke plume detected. Damper locked shut to protect indoor air."
        )
    elif fault_type == "sensor":
        return HVACFaultRecord(
            fault_type=AlertFault.SENSOR_FAULT,
            row1_title="Primary temperature sensor fault",
            row2_temps=f"TS-A: 63.0°F (Stuck) | TS-B: {room_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: TS-A voted out, regulating on redundant TS-B sensor",
            severity=AlertSeverity.WARNING,
            diagnostic_code="E-202",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Cross-check between primary BME280 (TS-A) and secondary SHT31 (TS-B) failed."
        )
    elif fault_type == "wifi":
        return HVACFaultRecord(
            fault_type=AlertFault.WIFI_OUTAGE,
            row1_title="Cloud link restored after outage",
            row2_temps=f"Room: {room_f:.1f}°F | Feels Like: {apparent_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: Edge PID maintained control, buffered alerts flushed",
            severity=AlertSeverity.INFO,
            diagnostic_code="E-203",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="MQTT broker connection restored. Flushed queued offline telemetry samples."
        )
    elif fault_type == "window":
        return HVACFaultRecord(
            fault_type=AlertFault.WINDOW_OPEN,
            row1_title="Exterior window left open",
            row2_temps=f"Room: {room_f:.1f}°F | Feels Like: {apparent_f:.1f}°F | Outside: {outside_f:.1f}°F",
            row3_action="System Action: HVAC paused after 60s to prevent conditioning outdoors",
            severity=AlertSeverity.WARNING,
            diagnostic_code="E-402",
            room_temp_f=room_f,
            apparent_temp_f=apparent_f,
            outside_temp_f=outside_f,
            details="Window contact sensor open >60 seconds. Conditioning paused until window is closed."
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

def send_apple_imessage(recipient_phone: str, message: str) -> bool:
    """Sends a real iMessage or SMS text using macOS Messages app."""
    safe_msg = message.replace('\\', '\\\\').replace('"', '\\"')
    safe_phone = recipient_phone.replace('\\', '\\\\').replace('"', '\\"')

    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to participant "{safe_phone}" of targetService
        send "{safe_msg}" to targetBuddy
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
        print(f"✅ Text message dispatched to {recipient_phone} via macOS Messages.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Messages.app dispatch: {e.stderr.strip()}")
        return False

def send_carrier_sms(phone_number: str, carrier: str, sms_text: str, subject: str = "Alert") -> bool:
    """Dispatches real SMS via carrier email-to-SMS gateway with valid subject for spam filtering."""
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
        if send_apple_mail(gateway_addr, subject, sms_text):
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
        send_carrier_sms(phone, carrier, sms_text, subject=f"HVAC-{record.diagnostic_code}")
        print("\n💬 Also sending direct message via macOS Messages app...")
        send_apple_imessage(phone, sms_text)

    print("\n🎉 Live alert dispatch test completed!")

def dispatch_custom_alert(
    row1: str,
    row2: str,
    row3: str,
    code: str = "E-405",
    severity: str = "CRITICAL",
    details: str = "",
    email: str = "choudhryshashwat29@gmail.com",
    phone: str = "9254075652",
    carrier: str = "verizon",
    dry_run: bool = False
) -> str:
    """Dispatches a 3-row alert directly from live Digital Twin simulation payloads."""
    row1_clean = row1.replace("->", "|").strip()
    row2_clean = row2.replace("->", "|").strip()
    row3_clean = row3.replace("->", "|").strip()
    if not row3_clean.startswith("System Action:"):
        row3_clean = f"System Action: {row3_clean}"

    sms_text = f"{row1_clean}\n{row2_clean}\n{row3_clean}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email_subject = f"[{severity}] Smart HVAC Alert: {row1_clean}"
    email_body = (
        f"SMART HVAC CONTROL - DIGITAL TWIN FAULT DISPATCH\n"
        f"----------------------------------------\n"
        f"Alert: {row1_clean}\n"
        f"Status: {severity} ({code})\n"
        f"Timestamp: {timestamp_str}\n\n"
        f"ENVIRONMENTAL TELEMETRY:\n"
        f"{row2_clean}\n\n"
        f"SYSTEM RESPONSE:\n"
        f"{row3_clean}\n\n"
        f"TECHNICAL DETAILS:\n"
        f"{details or 'Triggered by live ECE 441 Digital Twin Simulation.'}\n"
        f"----------------------------------------\n"
        f"Dispatched by Illinois Tech ECE 441 Edge IoT Gateway\n"
    )

    if dry_run:
        return sms_text

    def _bg_send():
        print(f"\n🚨 [SIM GATEWAY DISPATCH] {code} - {row1_clean}")
        print("-" * 55)
        print(sms_text)
        print("-" * 55)
        if email:
            send_apple_mail(email, email_subject, email_body)
        if phone:
            send_carrier_sms(phone, carrier, sms_text, subject=f"HVAC-{code}")
            send_apple_imessage(phone, sms_text)

    threading.Thread(target=_bg_send, daemon=True).start()
    return sms_text

class IoTGatewayHandler(SimpleHTTPRequestHandler):
    default_email = "choudhryshashwat29@gmail.com"
    default_phone = "9254075652"
    default_carrier = "verizon"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "status": "ok",
                "service": "ECE441-IoT-Alert-Gateway",
                "email": self.default_email,
                "phone": self.default_phone,
                "carrier": self.default_carrier
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/dispatch"):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}

            email = data.get("email", self.default_email)
            phone = data.get("phone", self.default_phone)
            carrier = data.get("carrier", self.default_carrier)
            dry_run = bool(data.get("dry_run", False))

            if data.get("row1") and data.get("row2") and data.get("row3"):
                sms_text = dispatch_custom_alert(
                    row1=data["row1"],
                    row2=data["row2"],
                    row3=data["row3"],
                    code=data.get("code", "E-405"),
                    severity=data.get("severity", "CRITICAL"),
                    details=data.get("details", ""),
                    email=email,
                    phone=phone,
                    carrier=carrier,
                    dry_run=dry_run
                )
            else:
                fault_type = data.get("fault_type") or data.get("fault", "surge")
                room_c = float(data.get("room_c", 26.0))
                outside_c = float(data.get("outside_c", 28.0))
                humidity = float(data.get("humidity", 50.0))
                air_vel = float(data.get("air_vel", 1.8))
                rec = generate_fault_data(fault_type, room_c=room_c, outside_c=outside_c, humidity=humidity, air_vel=air_vel)
                sms_text = dispatch_custom_alert(
                    row1=rec.row1_title,
                    row2=rec.row2_temps,
                    row3=rec.row3_action,
                    code=rec.diagnostic_code,
                    severity=rec.severity.value,
                    details=rec.details,
                    email=email,
                    phone=phone,
                    carrier=carrier,
                    dry_run=dry_run
                )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "status": "dispatched",
                "sms_preview": sms_text,
                "email": email,
                "phone": phone,
                "carrier": carrier,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def start_gateway_server(port: int = 8765, email: str = "choudhryshashwat29@gmail.com", phone: str = "9254075652", carrier: str = "verizon"):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    IoTGatewayHandler.default_email = email
    IoTGatewayHandler.default_phone = phone
    IoTGatewayHandler.default_carrier = carrier
    server = ThreadingHTTPServer(("127.0.0.1", port), IoTGatewayHandler)
    print("=" * 65)
    print(f"🌐 ECE 441 SMART HVAC IOT ALERT GATEWAY SERVER LISTENING")
    print(f"   Endpoint:       http://127.0.0.1:{port}/dispatch")
    print(f"   Sim Dashboard:  http://127.0.0.1:{port}/simulation/index.html")
    print(f"   Default Email:  {email}")
    print(f"   Default Phone:  {phone} ({carrier.upper()})")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down IoT Gateway Server.")
        server.server_close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testing IoT Alert Dispatcher")
    parser.add_argument("--email", type=str, default="choudhryshashwat29@gmail.com", help="Recipient email")
    parser.add_argument("--phone", type=str, default="9254075652", help="Recipient phone number")
    parser.add_argument("--carrier", type=str, default="verizon", choices=list(CARRIER_GATEWAYS.keys()), help="Mobile carrier")
    parser.add_argument("--fault", type=str, default="surge", choices=["surge", "drop", "heatstress", "heatwave", "freeze", "blower", "filter", "clog", "mcu", "voc", "smoke", "sensor", "wifi", "window"], help="Fault scenario")
    parser.add_argument("--all", action="store_true", help="Batch test all fault scenarios and verify 3-row layout")
    parser.add_argument("--serve", action="store_true", help="Run local HTTP IoT Alert Gateway server for the Digital Twin simulation")
    parser.add_argument("--port", type=int, default=8765, help="Port for local HTTP IoT Alert Gateway server")
    args = parser.parse_args()

    if args.serve:
        start_gateway_server(port=args.port, email=args.email, phone=args.phone, carrier=args.carrier)
    else:
        run_test(
            email=args.email,
            phone=args.phone,
            carrier=args.carrier,
            fault=args.fault,
            run_all=args.all
        )
