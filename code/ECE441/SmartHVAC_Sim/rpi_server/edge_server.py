"""
ECE 441: Smart and Connected Systems
Raspberry Pi 5 Unified Edge Server (HTTP REST + SQLite + Mosquitto MQTT Bridge)
File: rpi_server/edge_server.py

Serves as the central local server for BOTH:
  1. Digital Twin Web Simulator (simulation/index.html) via HTTP JSON
  2. Physical ESP32 HVAC Controller (src/main.cpp) via MQTT (port 1883) or HTTP (port 8765)

Usage:
  python3 -m rpi_server.edge_server --host 0.0.0.0 --port 8765
"""

import argparse
import gzip
import json
import os
import socket
import sys
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rpi_server.mqtt_bridge import MQTTEdgeBridge
from rpi_server.serial_bridge import SerialEdgeBridge
from rpi_server.storage import HVACEdgeStore
from testingIot import dispatch_custom_alert, generate_fault_data


class RPiEdgeHTTPHandler(SimpleHTTPRequestHandler):
    store: HVACEdgeStore
    mqtt_bridge: MQTTEdgeBridge
    serial_bridge: Optional[SerialEdgeBridge] = None
    enable_live_alerts: bool = False
    default_email: str = "choudhryshashwat29@gmail.com"
    default_phone: str = "9254075652"
    default_carrier: str = "verizon"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet high-frequency polling logs while keeping errors/mutations visible
        if self.command == "GET" and any(p in self.path for p in ("/api/", "/health")):
            return
        super().log_message(fmt, *args)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Content-Encoding, Accept-Encoding")
        # Allow Chrome/Safari Private Network Access (e.g., browser sim -> LAN Raspberry Pi)
        self.send_header("Access-Control-Allow-Private-Network", "true")
        super().end_headers()

    def _client_accepts_gzip(self) -> bool:
        accept = self.headers.get("Accept-Encoding", "").lower()
        return "gzip" in accept

    def _send_bytes(
        self,
        status_code: int,
        content_type: str,
        data: bytes,
        filename: Optional[str] = None,
        allow_gzip: bool = True,
        min_gzip_len: int = 256,
    ) -> None:
        use_gzip = allow_gzip and self._client_accepts_gzip() and len(data) >= min_gzip_len
        if use_gzip:
            compressed = gzip.compress(data, compresslevel=6)
            if len(compressed) < len(data):
                data = compressed
            else:
                use_gzip = False

        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self._send_bytes(status_code, "application/json; charset=utf-8", raw, allow_gzip=True, min_gzip_len=256)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        encoding = self.headers.get("Content-Encoding", "").lower()
        if "gzip" in encoding:
            try:
                raw = gzip.decompress(raw)
            except Exception:
                return {}
        try:
            text = raw.decode("utf-8", errors="ignore")
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)

        if route in ("/", "/dashboard", "/rpi"):
            dash_path = os.path.join(PROJECT_ROOT, "rpi_server", "dashboard.html")
            with open(dash_path, "rb") as f:
                body = f.read()
            self._send_bytes(200, "text/html; charset=utf-8", body, allow_gzip=True, min_gzip_len=256)
            return

        if route == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "ECE441-RPi5-HVAC-Edge-Server",
                    "rpi_edge": True,
                    "hostname": socket.gethostname(),
                    "control": self.store.get_control_state(),
                    "mqtt": self.mqtt_bridge.get_status(),
                    "serial": self.serial_bridge.get_status() if self.serial_bridge else {"connected": False},
                    "storage": self.store.get_storage_stats(),
                },
            )
            return

        if route == "/api/state":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "hostname": socket.gethostname(),
                    "latest_telemetry": self.store.latest_overall,
                    "devices": self.store.latest_by_device,
                    "control": self.store.get_control_state(),
                    "mqtt": self.mqtt_bridge.get_status(),
                    "serial": self.serial_bridge.get_status() if self.serial_bridge else {"connected": False},
                    "storage": self.store.get_storage_stats(),
                },
            )
            return

        if route == "/api/telemetry":
            limit = int(qs.get("limit", ["120"])[0])
            source = qs.get("source", [None])[0]
            self._send_json(
                200,
                {
                    "status": "ok",
                    "samples": self.store.get_recent_telemetry(limit=limit, source=source),
                    "hourly_rollups": self.store.get_hourly_rollups(limit=24),
                    "control": self.store.get_control_state(),
                },
            )
            return

        if route == "/api/control":
            self._send_json(200, {"status": "ok", "control": self.store.get_control_state()})
            return

        if route == "/api/faults":
            limit = int(qs.get("limit", ["30"])[0])
            self._send_json(200, {"status": "ok", "faults": self.store.get_recent_faults(limit=limit)})
            return

        if route in ("/api/export/csv", "/api/telemetry.csv"):
            limit = int(qs.get("limit", ["1000"])[0])
            source = qs.get("source", [None])[0]
            csv_str = self.store.export_telemetry_csv(limit=limit, source=source)
            csv_bytes = csv_str.encode("utf-8")
            self._send_bytes(
                200,
                "text/csv; charset=utf-8",
                csv_bytes,
                filename="hvac_telemetry_data.csv",
                allow_gzip=True,
                min_gzip_len=128,
            )
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        data = self._read_json_body()

        if route == "/api/telemetry":
            samples = data.get("samples")
            if isinstance(samples, list):
                last_rec = None
                for item in samples[:100]:
                    if isinstance(item, dict):
                        last_rec = self.store.record_telemetry(item, default_source="sim", force_write=True)
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "flushed": len(samples[:100]),
                        "latest": last_rec,
                        "control": self.store.get_control_state(),
                    },
                )
                return

            rec = self.store.record_telemetry(data, default_source=data.get("source", "esp32"))
            self._send_json(
                200,
                {
                    "status": "ok",
                    "persisted": rec.get("persisted", False),
                    "telemetry": rec,
                    "control": self.store.get_control_state(),
                },
            )
            return

        if route == "/api/control":
            updated_by = str(data.get("updated_by", "client"))
            bump_seq = bool(data.get("bump_seq", True))
            ctrl = self.store.update_control_state(
                setpoint_c=data.get("setpoint_c"),
                setpoint_f=data.get("setpoint_f"),
                demand_limit_w=data.get("demand_limit_w"),
                mode_override=data.get("mode_override") or data.get("mode"),
                updated_by=updated_by,
                bump_seq=bump_seq,
            )
            mqtt_pub = self.mqtt_bridge.publish_control_state(ctrl)
            serial_pub = (
                self.serial_bridge.publish_control_state(ctrl, fan_speed=data.get("fan_speed"))
                if self.serial_bridge
                else False
            )
            self._send_json(
                200,
                {
                    "status": "ok",
                    "mqtt_published": mqtt_pub,
                    "serial_published": serial_pub,
                    "control": ctrl,
                },
            )
            return

        if route == "/dispatch":
            email = data.get("email", self.default_email)
            phone = data.get("phone", self.default_phone)
            carrier = data.get("carrier", self.default_carrier)
            # On the Pi edge server, only trigger outbound carrier SMS if explicitly enabled
            dry_run = bool(data.get("dry_run", False)) or (not self.enable_live_alerts)

            if data.get("row1") and data.get("row2") and data.get("row3"):
                row1 = str(data["row1"])
                row2 = str(data["row2"])
                row3 = str(data["row3"])
                code = str(data.get("code", "E-404"))
                severity = str(data.get("severity", "CRITICAL"))
                details = str(data.get("details", ""))
            else:
                fault_type = str(data.get("fault_type") or data.get("fault", "surge"))
                rec_obj = generate_fault_data(
                    fault_type,
                    room_c=float(data.get("room_c", 26.0)),
                    outside_c=float(data.get("outside_c", 28.0)),
                    humidity=float(data.get("humidity", 50.0)),
                    air_vel=float(data.get("air_vel", 1.8)),
                )
                row1, row2, row3 = rec_obj.row1_title, rec_obj.row2_temps, rec_obj.row3_action
                code, severity, details = rec_obj.diagnostic_code, rec_obj.severity.value, rec_obj.details

            fault_entry = self.store.record_fault(
                {
                    "device_id": data.get("device_id", "ESP32-SIM"),
                    "source": data.get("source", "sim"),
                    "code": code,
                    "severity": severity,
                    "row1": row1,
                    "row2": row2,
                    "row3": row3,
                    "room_temp_f": float(data.get("room_temp_f", 0.0)),
                    "feels_like_f": float(data.get("feels_like_f", 0.0)),
                    "outside_temp_f": float(data.get("outside_temp_f", 0.0)),
                },
                default_source="sim",
            )

            sms_text = dispatch_custom_alert(
                row1=row1,
                row2=row2,
                row3=row3,
                code=code,
                severity=severity,
                details=details,
                email=email,
                phone=phone,
                carrier=carrier,
                dry_run=dry_run,
            )

            self._send_json(
                200,
                {
                    "status": "logged_and_dispatched" if not dry_run else "logged_to_sqlite",
                    "fault_id": fault_entry["id"],
                    "sms_preview": sms_text,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                },
            )
            return

        self._send_json(404, {"error": f"Unknown endpoint {route}"})


def run_edge_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    db_path: str = "",
    mqtt_host: str = "127.0.0.1",
    mqtt_port: int = 1883,
    enable_live_alerts: bool = False,
) -> None:
    os.chdir(PROJECT_ROOT)
    if not db_path:
        db_path = os.path.join(PROJECT_ROOT, "rpi_server", "data", "hvac_edge.db")

    store = HVACEdgeStore(db_path=db_path)
    mqtt_bridge = MQTTEdgeBridge(store=store, broker_host=mqtt_host, broker_port=mqtt_port)
    mqtt_bridge.start()
    serial_bridge = SerialEdgeBridge(store=store)
    serial_bridge.start()

    RPiEdgeHTTPHandler.store = store
    RPiEdgeHTTPHandler.mqtt_bridge = mqtt_bridge
    RPiEdgeHTTPHandler.serial_bridge = serial_bridge
    RPiEdgeHTTPHandler.enable_live_alerts = enable_live_alerts

    server = ThreadingHTTPServer((host, port), RPiEdgeHTTPHandler)
    print("=" * 68, flush=True)
    print("🍓 ECE 441 RASPBERRY PI 5 SMART HVAC EDGE SERVER ONLINE", flush=True)
    print(f"   Console UI:     http://{host}:{port}/", flush=True)
    print(f"   Digital Twin:   http://{host}:{port}/simulation/index.html", flush=True)
    print(f"   Telemetry API:  http://{host}:{port}/api/telemetry", flush=True)
    print(f"   Control API:    http://{host}:{port}/api/control", flush=True)
    print(f"   SQLite DB:      {db_path}", flush=True)
    print(f"   MQTT Broker:    {mqtt_host}:{mqtt_port}", flush=True)
    print("   USB/Wokwi Bridge: Auto-scanning (/dev/ttyACM*, /dev/cu.usbmodem*, localhost:4000)", flush=True)
    print("=" * 68, flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Raspberry Pi Edge Server...", flush=True)
    finally:
        mqtt_bridge.stop()
        serial_bridge.stop()
        server.server_close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ECE 441 Raspberry Pi 5 Smart HVAC Edge Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0 for LAN access)")
    parser.add_argument("--port", type=int, default=8765, help="HTTP server port (default: 8765)")
    parser.add_argument("--db", default="", help="Path to SQLite database file")
    parser.add_argument("--mqtt-host", default="127.0.0.1", help="Mosquitto MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="Mosquitto MQTT broker port")
    parser.add_argument("--live-alerts", action="store_true", help="Enable live SMS/Email outbound dispatch")
    args = parser.parse_args()

    run_edge_server(
        host=args.host,
        port=args.port,
        db_path=args.db,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        enable_live_alerts=args.live_alerts,
    )
