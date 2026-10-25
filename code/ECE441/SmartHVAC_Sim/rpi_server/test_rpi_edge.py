"""
ECE 441: Smart and Connected Systems
Automated Integration & Unit Test Suite: Raspberry Pi 5 Edge Server
File: rpi_server/test_rpi_edge.py

Verifies:
1. Unified payload normalization for both physical ESP32 and Digital Twin Simulator.
2. SD-card-safe SQLite WAL persistence, 2s write-throttling, hourly rollups, and 14-day pruning.
3. Live HTTP REST endpoints (/health, /api/telemetry, /api/control, /api/state, /dispatch).
4. Bidirectional command_seq propagation back to ESP32 & Simulator clients.
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rpi_server.edge_server import RPiEdgeHTTPHandler
from rpi_server.mqtt_bridge import MQTTEdgeBridge
from rpi_server.storage import HVACEdgeStore


class TestRPiEdgeServer(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_hvac_edge.db")
        self.store = HVACEdgeStore(
            db_path=self.db_path,
            raw_retention_days=14,
            hourly_retention_days=365,
            min_write_interval_s=1.0,
        )
        self.mqtt_bridge = MQTTEdgeBridge(store=self.store, broker_host="127.0.0.1", broker_port=59999)

        RPiEdgeHTTPHandler.store = self.store
        RPiEdgeHTTPHandler.mqtt_bridge = self.mqtt_bridge
        RPiEdgeHTTPHandler.enable_live_alerts = False

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), RPiEdgeHTTPHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.tmpdir.cleanup()

    def _http_json(self, method: str, path: str, body: dict = None) -> dict:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = Request(url, data=data, headers=headers, method=method)
        with urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            return json.loads(resp.read().decode("utf-8"))

    def test_esp32_and_sim_unified_telemetry_ingestion(self) -> None:
        # 1. Physical ESP32 payload schema (matches src/main.cpp)
        esp_resp = self._http_json(
            "POST",
            "/api/telemetry",
            {
                "device_id": "ESP32-HVAC-G2",
                "source": "esp32",
                "temp": 24.5,
                "humidity": 52.0,
                "apparent": 25.1,
                "velocity": 1.85,
                "power": 42.0,
                "heater_pwm": 0,
                "fan_pwm": 140,
                "setpoint_c": 23.0,
                "mode": "COOLING",
            },
        )
        self.assertEqual(esp_resp["status"], "ok")
        self.assertTrue(esp_resp["persisted"])
        self.assertAlmostEqual(esp_resp["telemetry"]["temp_f"], 76.1, places=1)

        # 2. Digital Twin Sim payload schema (matches simulation/index.html)
        sim_resp = self._http_json(
            "POST",
            "/api/telemetry",
            {
                "device_id": "ESP32-SIM",
                "source": "sim",
                "temp_c": 22.8,
                "humidity": 47.0,
                "apparent_c": 22.6,
                "air_vel_ms": 2.4,
                "static_pa": 14.0,
                "power_w": 185.0,
                "heater_pwm": 0,
                "fan_pwm": 76,
                "setpoint_c": 23.0,
                "mode": "IDLE",
            },
        )
        self.assertTrue(sim_resp["persisted"])

        # 3. Verify SQLite state & rollups
        state = self._http_json("GET", "/api/state")
        self.assertEqual(state["storage"]["raw_rows"], 2)
        self.assertGreaterEqual(state["storage"]["hourly_rows"], 1)
        self.assertIn("ESP32-HVAC-G2", state["devices"])
        self.assertIn("ESP32-SIM", state["devices"])

    def test_bidirectional_control_command_sync(self) -> None:
        ctrl_resp = self._http_json(
            "POST",
            "/api/control",
            {"setpoint_f": 70.0, "demand_limit_w": 850, "mode_override": "COOL", "updated_by": "test"},
        )
        self.assertEqual(ctrl_resp["control"]["command_seq"], 1)
        self.assertAlmostEqual(ctrl_resp["control"]["setpoint_f"], 70.0, places=1)
        self.assertEqual(ctrl_resp["control"]["demand_limit_w"], 850)

        # Next ESP32 telemetry check-in receives updated command_seq & setpoint immediately
        tel_resp = self._http_json(
            "POST",
            "/api/telemetry",
            {"device_id": "ESP32-HVAC-G2", "source": "esp32", "temp": 24.0, "humidity": 50.0, "ts": time.time() + 5},
        )
        self.assertEqual(tel_resp["control"]["command_seq"], 1)
        self.assertAlmostEqual(tel_resp["control"]["setpoint_c"], 21.11, places=1)

    def test_retention_pruning_and_sd_write_throttling(self) -> None:
        now = time.time()
        # Insert 20-day-old sample first (at old_ts, auto-prune cutoff hasn't passed old_ts yet)
        old_ts = now - (20 * 86400)
        self.store.record_telemetry({"device_id": "OLD-NODE", "temp": 21.0, "ts": old_ts}, force_write=True)
        self.assertEqual(self.store.get_storage_stats()["raw_rows"], 1)

        # Rapid burst at current time -> triggers automatic 14-day prune of OLD-NODE + throttles 2nd burst write
        r1 = self.store.record_telemetry({"device_id": "BURST", "temp": 22.0, "ts": now})
        r2 = self.store.record_telemetry({"device_id": "BURST", "temp": 22.5, "ts": now + 0.1})
        self.assertTrue(r1["persisted"])
        self.assertFalse(r2["persisted"])
        self.assertEqual(self.store.latest_by_device["BURST"]["temp_c"], 22.5)
        # OLD-NODE was automatically pruned, leaving only the 1 persisted BURST row
        self.assertEqual(self.store.get_storage_stats()["raw_rows"], 1)
        samples = self.store.get_recent_telemetry(limit=10)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["device_id"], "BURST")

    def test_fault_dispatch_persists_to_sqlite_in_dry_run(self) -> None:
        resp = self._http_json(
            "POST",
            "/dispatch",
            {"fault_type": "blower", "device_id": "ESP32-SIM", "source": "sim", "dry_run": True},
        )
        self.assertEqual(resp["status"], "logged_to_sqlite")
        faults = self._http_json("GET", "/api/faults")
        self.assertEqual(len(faults["faults"]), 1)
        self.assertEqual(faults["faults"][0]["code"], "E-302")


if __name__ == "__main__":
    unittest.main()
