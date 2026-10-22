"""
ECE 441 Smart HVAC - Hosted IoT Alert Gateway (shared core)

Cloud replacement for the local `testingIot.py --serve` gateway so the public
GitHub Pages digital twin can send real SMS + email alerts from any visitor's
browser without running anything locally.

Delivery: Gmail SMTP (App Password) -> recipient email + carrier email-to-SMS
gateway (e.g. 10digits@vtext.com), the same delivery path as testingIot.py.

Abuse protections (the endpoint is public and recipients are visitor-supplied):
  * Shared demo passcode (DEMO_PASSCODE env var) required on every dispatch.
  * CORS restricted to the GitHub Pages origin (+ localhost for development).
  * Row 1 / Row 3 text comes from a server-side table keyed by fault code;
    only Row 2 (live telemetry) comes from the client and it is charset- and
    length-restricted with links/addresses rejected, so the gateway cannot be
    used to relay arbitrary spam content.
  * Best-effort in-memory rate limits per client IP and per recipient.
    (Serverless instances can recycle, so these are per-instance limits.)
"""

import hmac
import json
import os
import re
import smtplib
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText

CARRIER_GATEWAYS = {
    "verizon": ["vtext.com", "vzwpix.com"],
    "att": ["txt.att.net", "mms.att.net"],
    "tmobile": ["tmomail.net"],
    "googlefi": ["msg.fi.google.com"],
    "sprint": ["messaging.sprintpcs.com"],
    "boost": ["myboostmobile.com"],
}

# Server-owned alert text, mirrored from simulation/index.html buildIoTAlertPayload()
FAULT_TEXT = {
    "E-101": ("WARNING", "Poor indoor air quality detected", "System Action: Outdoor damper 100%, ventilation purge active"),
    "E-102": ("CRITICAL", "Outdoor wildfire smoke detected", "System Action: Outdoor damper locked closed, MERV-13 recirculation active"),
    "E-201": ("CRITICAL", "Primary controller crash detected", "System Action: Watchdog failover to MCU-B, heater relay gated safe"),
    "E-202": ("WARNING", "Primary temp sensor fault detected", "System Action: TS-A voted out, control loop switched to redundant TS-B"),
    "E-203": ("INFO", "Cloud link lost (Wi-Fi outage)", "System Action: Autonomous local edge PID active, buffering telemetry"),
    "E-301": ("WARNING", "Air filter severely restricted", "System Action: Blower boosted, compressor capped at 50%, replace filter"),
    "E-302": ("CRITICAL", "Blower motor failure (0 RPM)", "System Action: Safety interlock engaged, heater and compressor shut off"),
    "E-401": ("WARNING", "Power demand limit exceeded", "System Action: Smart plug load shed, thermostat setpoint +1.8°F"),
    "E-402": ("WARNING", "Window left open", "System Action: HVAC paused to prevent energy waste"),
    "E-403": ("EMERGENCY", "Dangerous heat stress detected", "System Action: Maximum emergency cooling engaged, caregiver notified"),
    "E-404": ("CRITICAL", "Rapid temp increase", "System Action: Heater shut off, emergency cooling engaged"),
}

ALLOWED_ORIGINS = {
    "https://eternalshash.github.io",
    "https://htmlpreview.github.io",
    "https://raw.githack.com",
    "http://127.0.0.1:8765",
    "http://localhost:8765",
    "null",
}

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,24}$")
ROW2_RE = re.compile(r"^[A-Za-z0-9 °|:.\-/%()+,]{1,110}$")

# --- Best-effort rate limiting (per serverless instance) ---
IP_LIMIT, IP_WINDOW = 6, 60            # 6 dispatches / minute / IP
RCPT_LIMIT, RCPT_WINDOW = 20, 3600     # 20 dispatches / hour / recipient
_hits = {}


def _rate_ok(key, limit, window):
    now = time.time()
    bucket = [t for t in _hits.get(key, []) if now - t < window]
    if len(bucket) >= limit:
        _hits[key] = bucket
        return False
    bucket.append(now)
    _hits[key] = bucket
    return True


def cors_headers(origin):
    allow = origin if origin in ALLOWED_ORIGINS else "https://eternalshash.github.io"
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Vary": "Origin",
    }


def validate(data):
    """Returns (cleaned_dict, error_string)."""
    expected = os.environ.get("DEMO_PASSCODE", "")
    supplied = str(data.get("passcode", ""))
    if not expected or not hmac.compare_digest(supplied, expected):
        return None, "Invalid or missing demo passcode."

    phone = "".join(ch for ch in str(data.get("phone", "")) if ch.isdigit())
    if len(phone) == 11 and phone.startswith("1"):
        phone = phone[1:]
    if phone and len(phone) != 10:
        return None, "Phone must be a 10-digit US number."

    carrier = str(data.get("carrier", "verizon")).lower()
    if carrier not in CARRIER_GATEWAYS:
        return None, "Unsupported carrier."

    email = str(data.get("email", "")).strip()
    if email and not EMAIL_RE.match(email):
        return None, "Invalid email address."

    if not phone and not email:
        return None, "Provide a phone number and/or email."

    code = str(data.get("code", "E-404")).upper()
    if code not in FAULT_TEXT:
        code = "E-404"
    severity, row1, row3 = FAULT_TEXT[code]

    row2 = str(data.get("row2", "")).replace("->", "|").strip()
    low = row2.lower()
    if not ROW2_RE.match(row2) or "http" in low or "www" in low or ".com" in low:
        row2 = "Live telemetry unavailable"

    return {
        "phone": phone, "carrier": carrier, "email": email,
        "code": code, "severity": severity,
        "row1": row1, "row2": row2, "row3": row3,
        "dry_run": bool(data.get("dry_run", False)),
    }, None


def send_alert(a):
    """Sends email + carrier SMS over one Gmail SMTP session. Returns list of delivered addresses."""
    user = os.environ["GMAIL_USER"]
    pwd = os.environ["GMAIL_APP_PASSWORD"]
    sms_text = f"{a['row1']}\n{a['row2']}\n{a['row3']}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    email_body = (
        "SMART HVAC CONTROL - DIGITAL TWIN FAULT DISPATCH\n"
        "----------------------------------------\n"
        f"Alert: {a['row1']}\n"
        f"Status: {a['severity']} ({a['code']})\n"
        f"Timestamp: {ts}\n\n"
        f"ENVIRONMENTAL TELEMETRY:\n{a['row2']}\n\n"
        f"SYSTEM RESPONSE:\n{a['row3']}\n"
        "----------------------------------------\n"
        "Dispatched by Illinois Tech ECE 441 Hosted IoT Gateway\n"
    )

    outgoing = []
    if a["email"]:
        outgoing.append((a["email"], f"[{a['severity']}] Smart HVAC Alert: {a['row1']}", email_body))
    if a["phone"]:
        for domain in CARRIER_GATEWAYS[a["carrier"]]:
            outgoing.append((f"{a['phone']}@{domain}", f"HVAC-{a['code']}", sms_text))

    delivered = []
    pwd_clean = pwd.replace(" ", "").strip()
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=8) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, pwd_clean)
            for to_addr, subject, body in outgoing:
                msg = MIMEText(body, "plain", "utf-8")
                msg["From"] = user
                msg["To"] = to_addr
                msg["Subject"] = subject
                s.sendmail(user, [to_addr], msg.as_string())
                delivered.append(to_addr)
    except Exception:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as s:
            s.login(user, pwd_clean)
            for to_addr, subject, body in outgoing:
                msg = MIMEText(body, "plain", "utf-8")
                msg["From"] = user
                msg["To"] = to_addr
                msg["Subject"] = subject
                s.sendmail(user, [to_addr], msg.as_string())
                delivered.append(to_addr)
    return delivered, sms_text


def handle_dispatch(raw_body, client_ip):
    """Returns (status_code, response_dict)."""
    try:
        data = json.loads(raw_body or "{}")
    except Exception:
        return 400, {"status": "error", "error": "Invalid JSON."}

    a, err = validate(data)
    if err:
        return (401 if "passcode" in err else 400), {"status": "error", "error": err}

    if a["dry_run"]:
        return 200, {"status": "dry_run", "sms_preview": f"{a['row1']}\n{a['row2']}\n{a['row3']}"}

    if not _rate_ok(f"ip:{client_ip}", IP_LIMIT, IP_WINDOW):
        return 429, {"status": "error", "error": "Rate limit: too many alerts from this client, wait a minute."}
    for rcpt in filter(None, [a["phone"], a["email"].lower()]):
        if not _rate_ok(f"rcpt:{rcpt}", RCPT_LIMIT, RCPT_WINDOW):
            return 429, {"status": "error", "error": "Rate limit: this recipient has received too many alerts this hour."}

    try:
        delivered, sms_text = send_alert(a)
    except Exception as e:
        return 502, {"status": "error", "error": f"Mail delivery failed: {type(e).__name__}"}

    return 200, {
        "status": "dispatched",
        "sms_preview": sms_text,
        "delivered_to": delivered,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
    }
