"""
ECE 441: Smart and Connected Systems
Plug-and-Play Mosquitto MQTT Bridge for Raspberry Pi 5 Edge Server
File: rpi_server/mqtt_bridge.py

Subscribes to ESP32 telemetry & fault topics on the local Mosquitto broker
(port 1883) and publishes retained setpoint/mode commands back to the ESP32.
Degrades gracefully if paho-mqtt or a local broker is unavailable (e.g., on laptop).
"""

import json
import threading
import time
from typing import Any, Callable, Dict, Optional

from .storage import HVACEdgeStore

TOPIC_TELEMETRY_G2 = "ece441/group2/hvac/telemetry"
TOPIC_TELEMETRY_ALT = "ece441/hvac/telemetry"
TOPIC_ALERTS_G2 = "ece441/group2/hvac/alerts"
TOPIC_ALERTS_ALT = "ece441/hvac/alerts"
TOPIC_SETPOINT_PUB = "ece441/group2/hvac/setpoint"


class MQTTEdgeBridge:
    def __init__(
        self,
        store: HVACEdgeStore,
        broker_host: str = "127.0.0.1",
        broker_port: int = 1883,
        on_fault_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.store = store
        self.broker_host = broker_host
        self.broker_port = int(broker_port)
        self.on_fault_callback = on_fault_callback

        self.connected = False
        self.available = False
        self.messages_rx = 0
        self.messages_tx = 0
        self.last_error: str = ""
        self._client = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError:
            self.available = False
            self.last_error = "paho-mqtt not installed (HTTP REST still active)"
            return False

        self.available = True
        try:
            if hasattr(mqtt, "CallbackAPIVersion"):
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="RPi5_HVAC_EdgeServer")
            else:
                client = mqtt.Client(client_id="RPi5_HVAC_EdgeServer")
        except Exception:
            client = mqtt.Client()

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        self._client = client

        t = threading.Thread(target=self._connect_loop, daemon=True)
        t.start()
        return True

    def _connect_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self.connected and self._client is not None:
                try:
                    self._client.connect(self.broker_host, self.broker_port, keepalive=60)
                    self._client.loop_start()
                    # Publish current control state as retained so newly-booted ESP32s sync immediately
                    time.sleep(0.5)
                    if self.connected:
                        self.publish_control_state(self.store.get_control_state())
                    break
                except Exception as exc:
                    self.last_error = str(exc)
            self._stop_event.wait(5.0)

    def _on_connect(self, client, userdata, flags, rc, *args) -> None:
        rc_val = getattr(rc, "value", rc)
        if rc_val == 0:
            self.connected = True
            self.last_error = ""
            client.subscribe(
                [
                    (TOPIC_TELEMETRY_G2, 0),
                    (TOPIC_TELEMETRY_ALT, 0),
                    (TOPIC_ALERTS_G2, 1),
                    (TOPIC_ALERTS_ALT, 1),
                ]
            )
        else:
            self.connected = False
            self.last_error = f"MQTT connect rc={rc_val}"

    def _on_disconnect(self, client, userdata, *args) -> None:
        self.connected = False

    def _on_message(self, client, userdata, msg) -> None:
        self.messages_rx += 1
        topic = msg.topic
        raw_str = msg.payload.decode("utf-8", errors="ignore").strip()
        if not raw_str:
            return
        try:
            payload = json.loads(raw_str)
        except Exception:
            payload = {"raw": raw_str}

        if "telemetry" in topic and isinstance(payload, dict):
            payload.setdefault("source", "esp32-mqtt")
            payload.setdefault("device_id", "ESP32-HVAC-G2")
            self.store.record_telemetry(payload, default_source="esp32-mqtt")
        elif "alerts" in topic and isinstance(payload, dict):
            payload.setdefault("source", "esp32-mqtt")
            fault_rec = self.store.record_fault(payload, default_source="esp32-mqtt")
            if self.on_fault_callback:
                self.on_fault_callback(fault_rec)

    def publish_control_state(self, ctrl: Dict[str, Any]) -> bool:
        if not self.connected or self._client is None:
            return False
        msg_obj = {
            "command_seq": ctrl["command_seq"],
            "setpoint_c": ctrl["setpoint_c"],
            "setpoint_f": ctrl["setpoint_f"],
            "demand_limit_w": ctrl["demand_limit_w"],
            "mode": ctrl["mode_override"],
        }
        try:
            info = self._client.publish(TOPIC_SETPOINT_PUB, json.dumps(msg_obj), qos=1, retain=True)
            self.messages_tx += 1
            return info.rc == 0
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "connected": self.connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "topic_telemetry": TOPIC_TELEMETRY_G2,
            "topic_setpoint": TOPIC_SETPOINT_PUB,
            "messages_rx": self.messages_rx,
            "messages_tx": self.messages_tx,
            "last_error": self.last_error,
        }

    def stop(self) -> None:
        self._stop_event.set()
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
        self.connected = False
