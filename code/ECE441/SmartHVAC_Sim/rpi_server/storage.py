"""
ECE 441: Smart and Connected Systems
SD-Card-Friendly SQLite Time-Series & Control State Store for Raspberry Pi 5
File: rpi_server/storage.py

Implements a 3-tier retention architecture optimized for microSD longevity:
  1. telemetry_raw    - High-resolution (<=0.5 Hz) samples, auto-pruned at 14 days
  2. telemetry_hourly - 1-hour aggregated energy/thermal rollups, kept 365 days
  3. fault_events     - Diagnostic & 3-row caregiver alert records, kept indefinitely
  4. control_state    - Persistent bidirectional setpoint/mode commands for ESP32 & Sim
"""

import csv
import io
import math
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def c_to_f(temp_c: float) -> float:
    return temp_c * 9.0 / 5.0 + 32.0


def f_to_c(temp_f: float) -> float:
    return (temp_f - 32.0) * 5.0 / 9.0


def calc_apparent_c(temp_c: float, humidity: float, air_vel_ms: float) -> float:
    """Steadman apparent ('Feels Like') temperature in Celsius."""
    e = (humidity / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))
    return temp_c + 0.33 * e - 0.70 * air_vel_ms - 4.0


def normalize_telemetry_payload(raw: Dict[str, Any], default_source: str = "esp32") -> Dict[str, Any]:
    """
    Normalizes telemetry JSON from either:
      - Physical ESP32 firmware (temp, humidity, apparent, velocity, power, heater_pwm, fan_pwm)
      - Digital Twin simulator (temp_c/room_temp_f, apparent_c/feels_like_f, air_vel_ms, etc.)
    """
    source = str(raw.get("source") or default_source).strip()[:32]
    device_id = str(raw.get("device_id") or ("ESP32-SIM" if "sim" in source else "ESP32-HVAC-G2")).strip()[:48]

    if "temp_c" in raw and raw["temp_c"] is not None:
        temp_c = float(raw["temp_c"])
    elif "temp" in raw and raw["temp"] is not None:
        temp_c = float(raw["temp"])
    elif "room_temp_f" in raw and raw["room_temp_f"] is not None:
        temp_c = f_to_c(float(raw["room_temp_f"]))
    else:
        temp_c = 23.0

    humidity = float(raw.get("humidity", raw.get("rh", 48.0)))
    air_vel_ms = float(raw.get("air_vel_ms", raw.get("velocity", raw.get("duct_vel_ms", 0.0))))

    if "apparent_c" in raw and raw["apparent_c"] is not None:
        apparent_c = float(raw["apparent_c"])
    elif "apparent" in raw and raw["apparent"] is not None:
        apparent_c = float(raw["apparent"])
    elif "feels_like_f" in raw and raw["feels_like_f"] is not None:
        apparent_c = f_to_c(float(raw["feels_like_f"]))
    else:
        apparent_c = calc_apparent_c(temp_c, humidity, air_vel_ms)

    power_w = float(raw.get("power_w", raw.get("power", 0.0)))
    heater_pwm = int(raw.get("heater_pwm", 0))
    fan_pwm = int(raw.get("fan_pwm", 0))
    static_pa = float(raw.get("static_pa", 0.0))

    if "setpoint_c" in raw and raw["setpoint_c"] is not None:
        setpoint_c = float(raw["setpoint_c"])
    elif "setpoint_f" in raw and raw["setpoint_f"] is not None:
        setpoint_c = f_to_c(float(raw["setpoint_f"]))
    elif "setpoint" in raw and raw["setpoint"] is not None:
        setpoint_c = float(raw["setpoint"])
    else:
        setpoint_c = 23.0

    mode = str(raw.get("mode", "AUTO")).strip()[:32]
    active_mcu = str(raw.get("active_mcu", "A")).strip()[:8]
    voc_ppb = float(raw.get("voc_ppb", 0.0))
    co2_ppm = float(raw.get("co2_ppm", 0.0))
    pm25_ug = float(raw.get("pm25_ug", 0.0))

    now_ts = float(raw.get("ts") or time.time())

    return {
        "ts": now_ts,
        "iso_time": datetime.fromtimestamp(now_ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": device_id,
        "source": source,
        "temp_c": round(temp_c, 2),
        "temp_f": round(c_to_f(temp_c), 1),
        "humidity": round(humidity, 1),
        "apparent_c": round(apparent_c, 2),
        "apparent_f": round(c_to_f(apparent_c), 1),
        "air_vel_ms": round(air_vel_ms, 2),
        "static_pa": round(static_pa, 1),
        "power_w": round(power_w, 2),
        "heater_pwm": max(0, min(255, heater_pwm)),
        "fan_pwm": max(0, min(255, fan_pwm)),
        "setpoint_c": round(setpoint_c, 2),
        "setpoint_f": round(c_to_f(setpoint_c), 1),
        "mode": mode,
        "active_mcu": active_mcu,
        "voc_ppb": round(voc_ppb, 0),
        "co2_ppm": round(co2_ppm, 0),
        "pm25_ug": round(pm25_ug, 1),
        "v_mosfet_gs": round(float(raw.get("v_mosfet_gs", 5.0 * max(0, min(255, fan_pwm)) / 255.0)), 2),
        "v_fan_eff": round(float(raw.get("v_fan_eff", 4.99 * max(0, min(255, fan_pwm)) / 255.0)), 2),
        "i_fan_a": round(float(raw.get("i_fan_a", 0.3493 * max(0, min(255, fan_pwm)) / 255.0)), 4),
        "r_5v_rail_ohm": round(float(raw.get("r_5v_rail_ohm", 5.0 / (0.045 + 0.3493 * max(0, min(255, fan_pwm)) / 255.0))), 2),
        "r_total_circuit_ohm": round(float(raw.get("r_total_circuit_ohm", 12.0 / ((4.1667 if heater_pwm > 10 else 0.0) + 5.0 * (0.045 + 0.3493 * max(0, min(255, fan_pwm)) / 255.0) / (12.0 * 0.88)))), 2),
    }


class HVACEdgeStore:
    def __init__(
        self,
        db_path: str,
        raw_retention_days: int = 14,
        hourly_retention_days: int = 365,
        min_write_interval_s: float = 2.0,
    ):
        self.db_path = os.path.abspath(db_path)
        self.raw_retention_days = raw_retention_days
        self.hourly_retention_days = hourly_retention_days
        self.min_write_interval_s = min_write_interval_s

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._last_write_ts: Dict[str, float] = {}
        self._last_prune_ts: float = 0.0
        self.latest_by_device: Dict[str, Dict[str, Any]] = {}
        self.latest_overall: Optional[Dict[str, Any]] = None

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            # WAL + NORMAL sync protects microSD flash cells while remaining crash-safe
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA temp_store=MEMORY;")
            cur.execute("PRAGMA busy_timeout=5000;")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_raw (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    device_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    temp_c REAL NOT NULL,
                    humidity REAL NOT NULL,
                    apparent_c REAL NOT NULL,
                    air_vel_ms REAL NOT NULL,
                    static_pa REAL NOT NULL DEFAULT 0,
                    power_w REAL NOT NULL DEFAULT 0,
                    heater_pwm INTEGER NOT NULL DEFAULT 0,
                    fan_pwm INTEGER NOT NULL DEFAULT 0,
                    setpoint_c REAL NOT NULL DEFAULT 23.0,
                    mode TEXT NOT NULL DEFAULT 'AUTO',
                    active_mcu TEXT NOT NULL DEFAULT 'A',
                    voc_ppb REAL NOT NULL DEFAULT 0,
                    co2_ppm REAL NOT NULL DEFAULT 0,
                    pm25_ug REAL NOT NULL DEFAULT 0
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_raw_ts ON telemetry_raw(ts DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_raw_dev ON telemetry_raw(device_id, ts DESC);")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_hourly (
                    hour_bucket INTEGER NOT NULL,
                    device_id TEXT NOT NULL,
                    samples INTEGER NOT NULL DEFAULT 0,
                    sum_temp_c REAL NOT NULL DEFAULT 0,
                    min_temp_c REAL NOT NULL,
                    max_temp_c REAL NOT NULL,
                    sum_apparent_c REAL NOT NULL DEFAULT 0,
                    sum_humidity REAL NOT NULL DEFAULT 0,
                    sum_power_w REAL NOT NULL DEFAULT 0,
                    energy_wh REAL NOT NULL DEFAULT 0,
                    heater_on_s REAL NOT NULL DEFAULT 0,
                    fan_on_s REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (hour_bucket, device_id)
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS fault_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    device_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    code TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    row1 TEXT NOT NULL,
                    row2 TEXT NOT NULL,
                    row3 TEXT NOT NULL,
                    room_temp_f REAL NOT NULL DEFAULT 0,
                    feels_like_f REAL NOT NULL DEFAULT 0,
                    outside_temp_f REAL NOT NULL DEFAULT 0
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_fault_events_ts ON fault_events(ts DESC);")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS control_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    command_seq INTEGER NOT NULL DEFAULT 0,
                    setpoint_c REAL NOT NULL DEFAULT 23.0,
                    demand_limit_w REAL NOT NULL DEFAULT 1000.0,
                    mode_override TEXT NOT NULL DEFAULT 'AUTO',
                    fan_override_pct INTEGER NOT NULL DEFAULT -1,
                    updated_by TEXT NOT NULL DEFAULT 'boot',
                    updated_at REAL NOT NULL
                );
                """
            )
            try:
                cur.execute("ALTER TABLE control_state ADD COLUMN fan_override_pct INTEGER NOT NULL DEFAULT -1;")
            except sqlite3.OperationalError:
                pass
            cur.execute(
                """
                INSERT OR IGNORE INTO control_state (id, command_seq, setpoint_c, demand_limit_w, mode_override, fan_override_pct, updated_by, updated_at)
                VALUES (1, 0, 23.0, 1000.0, 'AUTO', -1, 'boot', ?);
                """,
                (time.time(),),
            )
            self._conn.commit()

            # Load latest row into memory cache if existing DB has data
            row = cur.execute("SELECT * FROM telemetry_raw ORDER BY ts DESC LIMIT 1;").fetchone()
            if row:
                rec = self._row_to_telemetry_dict(row)
                self.latest_overall = rec
                self.latest_by_device[rec["device_id"]] = rec

    def _row_to_telemetry_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["temp_f"] = round(c_to_f(d["temp_c"]), 1)
        d["apparent_f"] = round(c_to_f(d["apparent_c"]), 1)
        d["setpoint_f"] = round(c_to_f(d["setpoint_c"]), 1)
        d["iso_time"] = datetime.fromtimestamp(d["ts"], tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        return d

    def record_telemetry(self, payload: Dict[str, Any], default_source: str = "esp32", force_write: bool = False) -> Dict[str, Any]:
        rec = normalize_telemetry_payload(payload, default_source=default_source)
        dev = rec["device_id"]
        now = rec["ts"]

        with self._lock:
            prev_ts = self._last_write_ts.get(dev, 0.0)
            self.latest_by_device[dev] = rec
            self.latest_overall = rec

            dt_s = max(0.0, min(60.0, now - prev_ts)) if prev_ts > 0 else 2.0
            should_persist = force_write or (now - prev_ts >= self.min_write_interval_s)

            if should_persist:
                self._last_write_ts[dev] = now
                cur = self._conn.cursor()
                cur.execute(
                    """
                    INSERT INTO telemetry_raw (
                        ts, device_id, source, temp_c, humidity, apparent_c,
                        air_vel_ms, static_pa, power_w, heater_pwm, fan_pwm,
                        setpoint_c, mode, active_mcu, voc_ppb, co2_ppm, pm25_ug
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        rec["ts"],
                        rec["device_id"],
                        rec["source"],
                        rec["temp_c"],
                        rec["humidity"],
                        rec["apparent_c"],
                        rec["air_vel_ms"],
                        rec["static_pa"],
                        rec["power_w"],
                        rec["heater_pwm"],
                        rec["fan_pwm"],
                        rec["setpoint_c"],
                        rec["mode"],
                        rec["active_mcu"],
                        rec["voc_ppb"],
                        rec["co2_ppm"],
                        rec["pm25_ug"],
                    ),
                )

                hour_bucket = int(now // 3600) * 3600
                energy_wh_inc = rec["power_w"] * (dt_s / 3600.0)
                heater_on_inc = dt_s if rec["heater_pwm"] > 10 else 0.0
                fan_on_inc = dt_s if rec["fan_pwm"] > 20 else 0.0

                cur.execute(
                    """
                    INSERT INTO telemetry_hourly (
                        hour_bucket, device_id, samples, sum_temp_c, min_temp_c, max_temp_c,
                        sum_apparent_c, sum_humidity, sum_power_w, energy_wh, heater_on_s, fan_on_s
                    ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(hour_bucket, device_id) DO UPDATE SET
                        samples = samples + 1,
                        sum_temp_c = sum_temp_c + excluded.sum_temp_c,
                        min_temp_c = MIN(min_temp_c, excluded.min_temp_c),
                        max_temp_c = MAX(max_temp_c, excluded.max_temp_c),
                        sum_apparent_c = sum_apparent_c + excluded.sum_apparent_c,
                        sum_humidity = sum_humidity + excluded.sum_humidity,
                        sum_power_w = sum_power_w + excluded.sum_power_w,
                        energy_wh = energy_wh + excluded.energy_wh,
                        heater_on_s = heater_on_s + excluded.heater_on_s,
                        fan_on_s = fan_on_s + excluded.fan_on_s;
                    """,
                    (
                        hour_bucket,
                        rec["device_id"],
                        rec["temp_c"],
                        rec["temp_c"],
                        rec["temp_c"],
                        rec["apparent_c"],
                        rec["humidity"],
                        rec["power_w"],
                        energy_wh_inc,
                        heater_on_inc,
                        fan_on_inc,
                    ),
                )
                self._conn.commit()
                self._maybe_prune_locked(now)

            rec["persisted"] = should_persist
            return rec

    def _maybe_prune_locked(self, now: float) -> None:
        if now - self._last_prune_ts < 3600.0:
            return
        self._last_prune_ts = now
        raw_cutoff = now - (self.raw_retention_days * 86400.0)
        hourly_cutoff = int((now - (self.hourly_retention_days * 86400.0)) // 3600) * 3600
        cur = self._conn.cursor()
        cur.execute("DELETE FROM telemetry_raw WHERE ts < ?;", (raw_cutoff,))
        cur.execute("DELETE FROM telemetry_hourly WHERE hour_bucket < ?;", (hourly_cutoff,))
        self._conn.commit()

    def prune_now(self) -> Dict[str, int]:
        now = time.time()
        with self._lock:
            raw_cutoff = now - (self.raw_retention_days * 86400.0)
            hourly_cutoff = int((now - (self.hourly_retention_days * 86400.0)) // 3600) * 3600
            cur = self._conn.cursor()
            c1 = cur.execute("DELETE FROM telemetry_raw WHERE ts < ?;", (raw_cutoff,)).rowcount
            c2 = cur.execute("DELETE FROM telemetry_hourly WHERE hour_bucket < ?;", (hourly_cutoff,)).rowcount
            self._conn.commit()
            return {"pruned_raw": c1, "pruned_hourly": c2}

    def record_fault(self, data: Dict[str, Any], default_source: str = "esp32") -> Dict[str, Any]:
        now = float(data.get("ts") or time.time())
        device_id = str(data.get("device_id") or ("ESP32-SIM" if "sim" in default_source else "ESP32-HVAC-G2"))[:48]
        source = str(data.get("source") or default_source)[:32]
        code = str(data.get("code") or "E-404")[:16]
        severity = str(data.get("severity") or "CRITICAL")[:16]
        row1 = str(data.get("row1") or "HVAC Fault Detected").replace("->", "|").strip()
        row2 = str(data.get("row2") or "").replace("->", "|").strip()
        row3 = str(data.get("row3") or "").replace("->", "|").strip()
        room_f = float(data.get("room_temp_f", 0.0))
        feels_f = float(data.get("feels_like_f", 0.0))
        out_f = float(data.get("outside_temp_f", 0.0))

        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO fault_events (
                    ts, device_id, source, code, severity, row1, row2, row3,
                    room_temp_f, feels_like_f, outside_temp_f
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (now, device_id, source, code, severity, row1, row2, row3, room_f, feels_f, out_f),
            )
            fault_id = cur.lastrowid
            self._conn.commit()

        return {
            "id": fault_id,
            "ts": now,
            "iso_time": datetime.fromtimestamp(now, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "device_id": device_id,
            "source": source,
            "code": code,
            "severity": severity,
            "row1": row1,
            "row2": row2,
            "row3": row3,
        }

    def get_control_state(self) -> Dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM control_state WHERE id = 1;").fetchone()
            d = dict(row)
        d["setpoint_f"] = round(c_to_f(d["setpoint_c"]), 1)
        d["iso_updated"] = datetime.fromtimestamp(d["updated_at"], tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        return d

    def update_control_state(
        self,
        setpoint_c: Optional[float] = None,
        setpoint_f: Optional[float] = None,
        demand_limit_w: Optional[float] = None,
        mode_override: Optional[str] = None,
        fan_override_pct: Optional[int] = None,
        updated_by: str = "dashboard",
        bump_seq: bool = True,
    ) -> Dict[str, Any]:
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute("SELECT * FROM control_state WHERE id = 1;").fetchone()
            new_sp_c = float(row["setpoint_c"])
            if setpoint_c is not None:
                new_sp_c = float(setpoint_c)
            elif setpoint_f is not None:
                new_sp_c = f_to_c(float(setpoint_f))
            new_sp_c = max(15.0, min(30.0, round(new_sp_c, 2)))

            new_lim = float(row["demand_limit_w"])
            if demand_limit_w is not None:
                new_lim = max(200.0, min(5000.0, round(float(demand_limit_w), 0)))

            new_mode = str(row["mode_override"])
            if mode_override is not None:
                new_mode = str(mode_override).strip().upper()[:16]

            row_dict = dict(row)
            new_fan_ovr = int(row_dict.get("fan_override_pct", -1))
            if fan_override_pct is not None:
                fv = int(round(float(fan_override_pct)))
                new_fan_ovr = -1 if fv < 0 else max(0, min(100, fv))

            new_seq = int(row["command_seq"]) + (1 if bump_seq else 0)
            now = time.time()

            cur.execute(
                """
                UPDATE control_state
                SET command_seq = ?, setpoint_c = ?, demand_limit_w = ?,
                    mode_override = ?, fan_override_pct = ?, updated_by = ?, updated_at = ?
                WHERE id = 1;
                """,
                (new_seq, new_sp_c, new_lim, new_mode, new_fan_ovr, str(updated_by)[:32], now),
            )
            self._conn.commit()

        return self.get_control_state()

    def get_recent_telemetry(self, limit: int = 120, source: Optional[str] = None) -> List[Dict[str, Any]]:
        limit = max(1, min(1000, int(limit)))
        with self._lock:
            if source:
                rows = self._conn.execute(
                    "SELECT * FROM telemetry_raw WHERE source = ? ORDER BY ts DESC LIMIT ?;",
                    (source, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM telemetry_raw ORDER BY ts DESC LIMIT ?;",
                    (limit,),
                ).fetchall()
        return [self._row_to_telemetry_dict(r) for r in reversed(rows)]

    def export_telemetry_csv(self, limit: int = 1000, source: Optional[str] = None) -> str:
        samples = self.get_recent_telemetry(limit=limit, source=source)
        output = io.StringIO()
        fieldnames = [
            "timestamp_iso",
            "unix_ts",
            "device_id",
            "source",
            "room_temp_f",
            "room_temp_c",
            "feels_like_f",
            "feels_like_c",
            "humidity_pct",
            "air_velocity_ms",
            "static_pressure_pa",
            "power_w",
            "heater_pwm",
            "fan_pwm",
            "setpoint_f",
            "setpoint_c",
            "mode",
            "active_mcu",
            "voc_ppb",
            "co2_ppm",
            "pm25_ug",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for s in samples:
            writer.writerow(
                {
                    "timestamp_iso": s.get("iso_time", ""),
                    "unix_ts": s.get("ts", 0),
                    "device_id": s.get("device_id", ""),
                    "source": s.get("source", ""),
                    "room_temp_f": s.get("temp_f", 0.0),
                    "room_temp_c": s.get("temp_c", 0.0),
                    "feels_like_f": s.get("apparent_f", 0.0),
                    "feels_like_c": s.get("apparent_c", 0.0),
                    "humidity_pct": s.get("humidity", 0.0),
                    "air_velocity_ms": s.get("air_vel_ms", 0.0),
                    "static_pressure_pa": s.get("static_pa", 0.0),
                    "power_w": s.get("power_w", 0.0),
                    "heater_pwm": s.get("heater_pwm", 0),
                    "fan_pwm": s.get("fan_pwm", 0),
                    "setpoint_f": s.get("setpoint_f", 0.0),
                    "setpoint_c": s.get("setpoint_c", 0.0),
                    "mode": s.get("mode", ""),
                    "active_mcu": s.get("active_mcu", ""),
                    "voc_ppb": s.get("voc_ppb", 0.0),
                    "co2_ppm": s.get("co2_ppm", 0.0),
                    "pm25_ug": s.get("pm25_ug", 0.0),
                }
            )
        return output.getvalue()

    def get_hourly_rollups(self, limit: int = 24) -> List[Dict[str, Any]]:
        limit = max(1, min(720, int(limit)))
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM telemetry_hourly ORDER BY hour_bucket DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        out = []
        for r in reversed(rows):
            n = max(1, r["samples"])
            avg_c = r["sum_temp_c"] / n
            avg_app_c = r["sum_apparent_c"] / n
            out.append(
                {
                    "hour_bucket": r["hour_bucket"],
                    "hour_label": datetime.fromtimestamp(r["hour_bucket"], tz=timezone.utc).astimezone().strftime("%m-%d %H:00"),
                    "device_id": r["device_id"],
                    "samples": r["samples"],
                    "avg_temp_c": round(avg_c, 2),
                    "avg_temp_f": round(c_to_f(avg_c), 1),
                    "min_temp_f": round(c_to_f(r["min_temp_c"]), 1),
                    "max_temp_f": round(c_to_f(r["max_temp_c"]), 1),
                    "avg_apparent_f": round(c_to_f(avg_app_c), 1),
                    "avg_humidity": round(r["sum_humidity"] / n, 1),
                    "avg_power_w": round(r["sum_power_w"] / n, 1),
                    "energy_wh": round(r["energy_wh"], 2),
                    "heater_on_s": round(r["heater_on_s"], 1),
                    "fan_on_s": round(r["fan_on_s"], 1),
                }
            )
        return out

    def get_recent_faults(self, limit: int = 30) -> List[Dict[str, Any]]:
        limit = max(1, min(200, int(limit)))
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM fault_events ORDER BY ts DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["iso_time"] = datetime.fromtimestamp(d["ts"], tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
            out.append(d)
        return out

    def get_storage_stats(self) -> Dict[str, Any]:
        with self._lock:
            raw_count = self._conn.execute("SELECT COUNT(*) FROM telemetry_raw;").fetchone()[0]
            hourly_count = self._conn.execute("SELECT COUNT(*) FROM telemetry_hourly;").fetchone()[0]
            fault_count = self._conn.execute("SELECT COUNT(*) FROM fault_events;").fetchone()[0]

        db_bytes = 0
        for suffix in ("", "-wal", "-shm"):
            p = self.db_path + suffix
            if os.path.exists(p):
                db_bytes += os.path.getsize(p)

        disk = shutil.disk_usage(os.path.dirname(self.db_path))
        return {
            "db_path": self.db_path,
            "db_size_kb": round(db_bytes / 1024.0, 1),
            "db_size_mb": round(db_bytes / (1024.0 * 1024.0), 3),
            "raw_rows": raw_count,
            "hourly_rows": hourly_count,
            "fault_rows": fault_count,
            "raw_retention_days": self.raw_retention_days,
            "hourly_retention_days": self.hourly_retention_days,
            "min_write_interval_s": self.min_write_interval_s,
            "disk_free_gb": round(disk.free / (1024.0 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024.0 ** 3), 2),
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
