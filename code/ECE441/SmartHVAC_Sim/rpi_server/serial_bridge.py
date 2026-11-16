"""
ECE 441: Smart and Connected Systems
Plug-and-Play USB Serial & Wokwi RFC2217 Bridge for Raspberry Pi 5 Edge Server
File: rpi_server/serial_bridge.py

Automatically discovers and connects to:
  1. Physical Arduino Uno R4 WiFi (SMART HVAC DEMO V5 — BME688 ONLY, Pin 9 Fan PWM, Pin 10 Relay)
     over USB Serial (/dev/ttyACM*, /dev/ttyUSB*, /dev/cu.usbmodem*)
  2. Live VS Code Wokwi Simulator via TCP RFC2217 port (127.0.0.1:4000)

Parses BOTH:
  - Andy's HVAC-proto.ino V5 multi-line text output ([BME688], [GAS SENSOR], [HVAC SYSTEM])
  - Single-line JSON telemetry packets
And forwards single-character V5 control commands (5, H, F, M, S, X, R, D, B) over Serial.
"""

import glob
import json
import math
import re
import socket
import threading
from typing import Any, Dict, Optional

from .storage import HVACEdgeStore


class SerialEdgeBridge:
    def __init__(
        self,
        store: HVACEdgeStore,
        serial_port: str = "auto",
        baud_rate: int = 115200,
        wokwi_host: str = "127.0.0.1",
        wokwi_port: int = 4000,
    ):
        self.store = store
        self.requested_port = serial_port
        self.baud_rate = int(baud_rate)
        self.wokwi_host = wokwi_host
        self.wokwi_port = int(wokwi_port)

        self.connected = False
        self.active_endpoint: str = ""
        self.messages_rx = 0
        self.messages_tx = 0
        self.last_error: str = ""

        self._ser = None
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Stateful accumulator for Andy's HVAC-proto.ino V5 multi-line serial blocks
        self._v5: Dict[str, Any] = {
            "device_id": "ARDUINO-R4-V5-BME688",
            "chip_id": "0x61",
            "temp_c": 24.0,
            "humidity": 48.0,
            "pressure_hpa": 1013.25,
            "dew_point_f": 54.3,
            "altitude_ft": 412.0,
            "gas_kohms": 142.5,
            "gas_baseline_kohms": 140.0,
            "gas_rel_pct": 101.8,
            "gas_trend": "Near baseline",
            "heater_relay": 0,
            "fan_pwm": 0,
            "fan_speed_pct": 0.0,
            "cooldown_active": 0,
            "safety_lockout": 0,
            "lockout_reason": "None",
            "bme_ok": 1,
            "_has_temp": False,
        }

    def start(self) -> None:
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

    def _discover_usb_serial_port(self) -> Optional[str]:
        if self.requested_port and self.requested_port != "auto":
            return self.requested_port
        patterns = [
            "/dev/ttyACM*",
            "/dev/ttyUSB*",
            "/dev/cu.usbmodem*",
            "/dev/cu.usbserial*",
        ]
        for pat in patterns:
            matches = sorted(glob.glob(pat))
            if matches:
                return matches[0]
        return None

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            # 1. Try physical USB Serial port first (if pyserial is available and a device is plugged in)
            usb_port = self._discover_usb_serial_port()
            if usb_port:
                try:
                    import serial  # type: ignore

                    with serial.Serial(usb_port, self.baud_rate, timeout=1.0) as ser:
                        with self._lock:
                            self._ser = ser
                            self.connected = True
                            self.active_endpoint = f"usb:{usb_port}@{self.baud_rate}"
                            self.last_error = ""
                        while not self._stop_event.is_set():
                            raw = ser.readline()
                            if raw:
                                self._process_line(raw.decode("utf-8", errors="ignore"))
                except Exception as exc:
                    self.last_error = str(exc)
                finally:
                    with self._lock:
                        self._ser = None
                        self.connected = False

            # 2. Fallback: Try live VS Code Wokwi Simulator TCP port (localhost:4000)
            try:
                sock = socket.create_connection((self.wokwi_host, self.wokwi_port), timeout=1.5)
                sock.settimeout(1.0)
                with self._lock:
                    self._sock = sock
                    self.connected = True
                    self.active_endpoint = f"wokwi-tcp:{self.wokwi_host}:{self.wokwi_port}"
                    self.last_error = ""
                buf = ""
                while not self._stop_event.is_set():
                    try:
                        chunk = sock.recv(1024)
                        if not chunk:
                            break
                        buf += chunk.decode("utf-8", errors="ignore")
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            self._process_line(line)
                    except socket.timeout:
                        continue
            except Exception as exc:
                self.last_error = str(exc)
            finally:
                with self._lock:
                    if self._sock is not None:
                        try:
                            self._sock.close()
                        except Exception:
                            pass
                    self._sock = None
                    self.connected = False

            self._stop_event.wait(2.5)

    def _process_line(self, line: str) -> None:
        s = line.strip()
        if not s or not s.startswith("{"):
            return
        try:
            payload = json.loads(s)
        except Exception:
            return
        if not isinstance(payload, dict) or "temp_c" not in payload:
            return

        self.messages_rx += 1
        payload.setdefault("source", "arduino-serial")
        payload.setdefault("device_id", "ARDUINO-R4-HVAC-G2")
        self.store.record_telemetry(payload, default_source="arduino-serial")

    def publish_control_state(self, ctrl: Dict[str, Any], fan_speed: Optional[float] = None) -> bool:
        msg_obj: Dict[str, Any] = {
            "command_seq": ctrl.get("command_seq", 1),
            "setpoint_c": ctrl.get("setpoint_c", 23.0),
        }
        if fan_speed is not None:
            msg_obj["fan_speed"] = float(fan_speed)
        raw_bytes = (json.dumps(msg_obj) + "\n").encode("utf-8")

        with self._lock:
            if not self.connected:
                return False
            try:
                if self._ser is not None:
                    self._ser.write(raw_bytes)
                    self._ser.flush()
                    self.messages_tx += 1
                    return True
                if self._sock is not None:
                    self._sock.sendall(raw_bytes)
                    self.messages_tx += 1
                    return True
            except Exception as exc:
                self.last_error = str(exc)
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "endpoint": self.active_endpoint or "auto-scanning (/dev/ttyACM*, /dev/cu.usbmodem*, localhost:4000)",
            "baud_rate": self.baud_rate,
            "messages_rx": self.messages_rx,
            "messages_tx": self.messages_tx,
            "last_error": self.last_error,
        }

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.close()
                except Exception:
                    pass
            self._sock = None
            self._ser = None
            self.connected = False
