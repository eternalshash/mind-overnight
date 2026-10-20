"""
ECE 441: Smart and Connected Systems
Live Alert Dispatcher Test: Real SMS & Email Dispatch
Author: Shashwat Choudhry

This script allows you to test sending real text messages and emails when a
simulated HVAC fault or sudden temperature change occurs.
"""

import sys
import os
import subprocess
import argparse
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request
import urllib.parse

# Ensure local directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iot_alert_engine import (
    IoTAlertEngine, MultiChannelDispatcher, AlertCode, AlertSeverity, AlertRecord
)

CARRIER_GATEWAYS = {
    "att": ["txt.att.net", "mms.att.net"],
    "verizon": ["vtext.com", "vzwpix.com"],
    "tmobile": ["tmomail.net"],
    "googlefi": ["msg.fi.google.com"],
    "sprint": ["messaging.sprintpcs.com"],
    "boost": ["myboostmobile.com"]
}

def send_apple_mail(recipient: str, subject: str, body_text: str) -> bool:
    """Sends a real email using macOS native Mail app without requiring SMTP passwords."""
    # Escape quotes and backslashes for AppleScript
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
        proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
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
        print(f"❌ Messages.app dispatch note: {e.stderr.strip()}")
        print("💡 If recipient is not on iMessage or SMS Forwarding is off, use the Carrier Email-to-SMS Gateway option!")
        return False

def send_carrier_sms(phone_number: str, carrier: str, subject: str, message: str) -> bool:
    """Sends a real SMS via Carrier Email-to-SMS gateway(s)."""
    clean_phone = "".join(filter(str.isdigit, phone_number))
    if len(clean_phone) == 11 and clean_phone.startswith("1"):
        clean_phone = clean_phone[1:]
    carrier_domains = CARRIER_GATEWAYS.get(carrier.lower(), ["vtext.com", "vzwpix.com"])
    if isinstance(carrier_domains, str):
        carrier_domains = [carrier_domains]

    success = False
    for domain in carrier_domains:
        gateway_address = f"{clean_phone}@{domain}"
        print(f"📲 Routing SMS through carrier gateway: {gateway_address}")
        if send_apple_mail(gateway_address, subject, message):
            success = True
    return success

def send_textbelt_sms(phone_number: str, message: str) -> bool:
    """Sends an SMS using the free Textbelt quota (1 free test text per day)."""
    url = "https://textbelt.com/text"
    clean_phone = "".join(filter(str.isdigit, phone_number))
    if len(clean_phone) == 10:
        clean_phone = "+1" + clean_phone
    elif not clean_phone.startswith("+"):
        clean_phone = "+" + clean_phone
        
    data = urllib.parse.urlencode({
        "phone": clean_phone,
        "message": message,
        "key": "textbelt"
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "SmartHVAC/1.0"})
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("success"):
                print(f"✅ SMS sent via Textbelt! Quota remaining: {res.get('quotaRemaining', 0)}")
                return True
            else:
                print(f"❌ Textbelt response: {res.get('error')}")
                return False
    except Exception as e:
        print(f"❌ Textbelt request failed: {e}")
        return False

def simulate_and_send(
    email: str = None,
    phone: str = None,
    carrier: str = "att",
    fault_type: str = "surge",
    sms_method: str = "carrier"
):
    print("=" * 65)
    print("🚀 SMART HVAC LIVE ALERT DISPATCH TEST")
    print(f"Fault Scenario:  {fault_type.upper()}")
    print(f"Target Email:    {email or 'None'}")
    print(f"Target Phone:    {phone or 'None'} (Carrier: {carrier.upper()}, Method: {sms_method})")
    print("=" * 65)

    engine = IoTAlertEngine(cooldown_seconds=10)
    dispatcher = MultiChannelDispatcher(
        caregiver_phone=phone or "+1 (312) 555-0199",
        caregiver_email=email or "caregiver@example.com"
    )

    # Simulate fault condition
    if fault_type == "surge":
        print("\n[SIM] Simulating Sudden Thermal Surge (+4.5°F/min)...")
        engine.process_telemetry(t=0, temp_c=22.0, humidity=50, air_velocity=1.8, fan_cmd_pct=30, fan_rpm=840, static_dp=35, outside_temp_c=28.0)
        alerts = engine.process_telemetry(t=60, temp_c=26.0, humidity=50, air_velocity=1.8, fan_cmd_pct=30, fan_rpm=840, static_dp=35, outside_temp_c=28.0)
    elif fault_type == "blower":
        print("\n[SIM] Simulating Blower Motor Seizure (0 RPM)...")
        alerts = []
        for sec in range(6):
            new_al = engine.process_telemetry(t=sec, temp_c=24.0, humidity=50, air_velocity=0.0, fan_cmd_pct=60, fan_rpm=0, static_dp=0, outside_temp_c=28.0)
            if new_al:
                alerts.extend(new_al)
    elif fault_type == "heatstress":
        print("\n[SIM] Simulating Elderly Resident Heat Stress (Feels Like > 88°F)...")
        alerts = engine.process_telemetry(t=10, temp_c=30.0, humidity=75, air_velocity=0.2, fan_cmd_pct=30, fan_rpm=840, static_dp=35, outside_temp_c=36.0)
    else:
        print(f"Unknown fault type {fault_type}")
        return

    if not alerts:
        print("⚠️ No alerts triggered in simulation step.")
        return

    alert = alerts[0]
    print(f"\n🚨 ALERT GENERATED: [{alert.severity.value}] {alert.code.value} - {alert.title}")
    print(f"   Room: {alert.room_temp_f:.1f}°F | Feels Like: {alert.apparent_temp_f:.1f}°F | Outside: {alert.outside_temp_f:.1f}°F | dT/dt: {alert.rate_of_change_f_per_min:+.2f}°F/min")

    sms_content = dispatcher.format_sms(alert)
    print("\n📱 FORMATTED SMS PREVIEW:")
    print("-" * 40)
    print(sms_content)
    print("-" * 40)
    email_subject = f"[{alert.severity.value}] Smart HVAC Alert: {alert.title}"
    email_body = (
        f"SMART HVAC CONTROL - FAULT ALERT\n"
        f"Facility: Illinois Tech ECE 441 Zone-A Residential Suite\n"
        f"Severity: {alert.severity.value}\n"
        f"Diagnostic Code: {alert.code.value}\n"
        f"Incident Time: {alert.timestamp_iso}\n\n"
        f"TELEMETRY SNAPSHOT:\n"
        f"- Room Temperature: {alert.room_temp_f:.1f} °F\n"
        f"- Feels Like (Apparent): {alert.apparent_temp_f:.1f} °F\n"
        f"- Rate of Change: {alert.rate_of_change_f_per_min:+.2f} °F/min\n"
        f"- Relative Humidity: {alert.humidity:.1f} %\n\n"
        f"DETAILS:\n{alert.message}\n\n"
        f"ACTION REQUIRED:\n{alert.recommended_action}\n"
    )

    # 1. Send Email if requested
    if email:
        print("\n--- Dispatching Real Email ---")
        send_apple_mail(email, email_subject, email_body)

    # 2. Send SMS if requested
    if phone:
        print(f"\n--- Dispatching Real SMS to {phone} ---")
        if sms_method == "carrier":
            send_carrier_sms(phone, carrier, "", sms_content)
        elif sms_method == "imessage":
            send_apple_imessage(phone, sms_content)
        elif sms_method == "textbelt":
            send_textbelt_sms(phone, sms_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live HVAC Alert Test")
    parser.add_argument("--email", type=str, help="Recipient email address")
    parser.add_argument("--phone", type=str, help="Recipient phone number (e.g. 3125550199)")
    parser.add_argument("--carrier", type=str, default="att", choices=list(CARRIER_GATEWAYS.keys()), help="Mobile carrier for SMS gateway")
    parser.add_argument("--fault", type=str, default="surge", choices=["surge", "blower", "heatstress"], help="Fault to simulate")
    parser.add_argument("--sms-method", type=str, default="carrier", choices=["carrier", "imessage", "textbelt"], help="SMS delivery method")
    args = parser.parse_args()

    simulate_and_send(
        email=args.email,
        phone=args.phone,
        carrier=args.carrier,
        fault_type=args.fault,
        sms_method=args.sms_method
    )
