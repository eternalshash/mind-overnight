"""
ECE 441: Smart and Connected Systems - Group 2
Smart HVAC Control: IoT Edge Anomaly Detection & Multi-Channel Alert Engine
Author: Shashwat Choudhry (Firmware & Control Engineer)
Collaborators: Andy Tran, Kaleb Cowgur, Haron Abuelhija

This module implements:
1. Multi-variable anomaly detection (Rapid dT/dt surge, physiological heat stress,
   blower motor stall, filter clogging, and dual-MCU failover).
2. Offline edge buffering during network/Wi-Fi outages.
3. Multi-channel alert dispatching (SMS / Text, HTML Email, and MQTT IoT JSON).
"""

import math
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class AlertCode(Enum):
    SUDDEN_TEMP_SURGE = "E-405"     # Rapid temperature spike (dT/dt > threshold)
    SUDDEN_TEMP_DROP = "E-406"      # Rapid temperature crash
    HEAT_STRESS_RISK = "E-403"      # Physiological heat hazard (elderly resident safety)
    FREEZE_RISK = "E-407"           # Freeze / hypothermia / pipe burst hazard
    BLOWER_STALL = "E-302"          # Commanded fan spinning at 0 RPM / 0 m/s
    FILTER_RESTRICTION = "E-301"    # High dP / degraded airflow
    MCU_WATCHDOG_FAIL = "E-201"     # Primary MCU crashed, failover to MCU-B
    SENSOR_CROSS_CHECK = "E-202"    # Divergence between dual BME280 sensors
    CLOUD_LINK_RESTORED = "E-204"   # Wi-Fi reconnected, queued alert burst sent

def c_to_f(temp_c: float) -> float:
    return temp_c * 1.8 + 32.0

def f_to_c(temp_f: float) -> float:
    return (temp_f - 32.0) / 1.8

def calculate_apparent_temperature(temp_c: float, humidity: float, air_velocity: float) -> float:
    """
    Computes 'Feels Like' apparent temperature using Steadman's model (ASHRAE 55).
    Accounts for evaporative cooling attenuation from humidity and convective duct draft.
    """
    e = (humidity / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))
    apparent_c = temp_c + 0.33 * e - 0.70 * air_velocity - 4.0
    return apparent_c

class AlertRecord:
    def __init__(
        self,
        alert_id: str,
        timestamp: float,
        code: AlertCode,
        severity: AlertSeverity,
        title: str,
        message: str,
        recommended_action: str,
        room_temp_f: float,
        apparent_temp_f: float,
        humidity: float,
        rate_of_change_f_per_min: float,
        actuator_state: Dict[str, Any],
        queued_offline: bool = False,
        outside_temp_f: float = 82.0,
        simplified_title: Optional[str] = None,
        system_action: Optional[str] = None
    ):
        self.alert_id = alert_id
        self.timestamp = timestamp
        self.timestamp_iso = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        self.code = code
        self.severity = severity
        self.title = title
        self.simplified_title = simplified_title or title
        self.message = message
        self.recommended_action = recommended_action
        self.system_action = system_action or recommended_action
        self.room_temp_f = room_temp_f
        self.apparent_temp_f = apparent_temp_f
        self.outside_temp_f = outside_temp_f
        self.humidity = humidity
        self.rate_of_change_f_per_min = rate_of_change_f_per_min
        self.actuator_state = actuator_state
        self.queued_offline = queued_offline
        self.dispatched_at: Optional[float] = None
        self.dispatch_channels: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "timestamp_iso": self.timestamp_iso,
            "code": self.code.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "recommended_action": self.recommended_action,
            "metrics": {
                "room_temp_f": round(self.room_temp_f, 2),
                "apparent_temp_f": round(self.apparent_temp_f, 2),
                "humidity": round(self.humidity, 1),
                "dT_dt_f_per_min": round(self.rate_of_change_f_per_min, 2)
            },
            "actuator_state": self.actuator_state,
            "queued_offline": self.queued_offline
        }

class IoTAlertEngine:
    def __init__(
        self,
        temp_surge_threshold_f_per_min: float = 2.5,
        temp_drop_threshold_f_per_min: float = -3.5,
        heat_stress_apparent_threshold_f: float = 88.0,
        heat_stress_drybulb_threshold_f: float = 85.0,
        freeze_threshold_f: float = 45.0,
        window_seconds: int = 60,
        cooldown_seconds: int = 180
    ):
        self.temp_surge_threshold = temp_surge_threshold_f_per_min
        self.temp_drop_threshold = temp_drop_threshold_f_per_min
        self.heat_stress_apparent_limit = heat_stress_apparent_threshold_f
        self.heat_stress_drybulb_limit = heat_stress_drybulb_threshold_f
        self.freeze_limit = freeze_threshold_f
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds

        # Internal buffers
        self.history: List[Tuple[float, float]] = [] # (t, temp_f)
        self.cooldown_tracker: Dict[str, float] = {}  # alert_code -> last_trigger_time
        self.offline_queue: List[AlertRecord] = []
        self.alert_history: List[AlertRecord] = []
        self.alert_counter = 0

        # State tracking
        self.prev_wifi_state = True
        self.blower_mis_timer = 0.0

    def _next_alert_id(self) -> str:
        self.alert_counter += 1
        return f"ALT-{datetime.now().strftime('%Y%m%d')}-{self.alert_counter:03d}"

    def _is_in_cooldown(self, code: AlertCode, now: float) -> bool:
        last_t = self.cooldown_tracker.get(code.value, -1e9)
        return (now - last_t) < self.cooldown_seconds

    def compute_rate_of_change(self, current_t: float, current_temp_f: float) -> float:
        """
        Computes rate of temperature change dT/dt in degrees F per minute
        over the sliding window.
        """
        self.history.append((current_t, current_temp_f))
        
        # Purge readings older than window
        cutoff = current_t - self.window_seconds
        self.history = [(t, temp) for t, temp in self.history if t >= cutoff]

        if len(self.history) < 2:
            return 0.0

        oldest_t, oldest_temp = self.history[0]
        dt_seconds = current_t - oldest_t
        if dt_seconds < 5.0:
            return 0.0

        dtemp = current_temp_f - oldest_temp
        rate_f_per_min = (dtemp / dt_seconds) * 60.0
        return rate_f_per_min

    def process_telemetry(
        self,
        t: float,
        temp_c: float,
        humidity: float,
        air_velocity: float,
        fan_cmd_pct: float,
        fan_rpm: float,
        static_dp: float,
        mcu_a_ok: bool = True,
        wifi_online: bool = True,
        heater_pwm_pct: float = 0.0,
        damper_pct: float = 0.0,
        sens_a_c: Optional[float] = None,
        sens_b_c: Optional[float] = None,
        outside_temp_c: float = 27.8
    ) -> List[AlertRecord]:
        """
        Main anomaly evaluation cycle executed on edge/gateway.
        Returns a list of newly triggered alerts during this cycle.
        """
        temp_f = c_to_f(temp_c)
        outside_temp_f = c_to_f(outside_temp_c)
        apparent_c = calculate_apparent_temperature(temp_c, humidity, air_velocity)
        apparent_f = c_to_f(apparent_c)
        dT_dt = self.compute_rate_of_change(t, temp_f)

        actuators = {
            "heater_pwm_pct": heater_pwm_pct,
            "fan_cmd_pct": fan_cmd_pct,
            "fan_rpm": fan_rpm,
            "damper_pct": damper_pct,
            "static_dp_pa": static_dp
        }

        new_alerts: List[AlertRecord] = []

        # -------------------------------------------------------------
        # 1. Anomaly Check: Rapid Thermal Rate-of-Change (Surge / Drop)
        # -------------------------------------------------------------
        if dT_dt >= self.temp_surge_threshold and not self._is_in_cooldown(AlertCode.SUDDEN_TEMP_SURGE, t):
            self.cooldown_tracker[AlertCode.SUDDEN_TEMP_SURGE.value] = t
            alert = AlertRecord(
                alert_id=self._next_alert_id(),
                timestamp=t,
                code=AlertCode.SUDDEN_TEMP_SURGE,
                severity=AlertSeverity.CRITICAL,
                title="SUDDEN THERMAL SURGE DETECTED",
                simplified_title="Sudden rapid increase in temperature",
                message=(f"Zone temperature climbing abnormally fast: {temp_f:.1f}°F "
                         f"(Rate: +{dT_dt:.2f}°F/min). Possible thermal runaway or envelope breach."),
                recommended_action="Inspect PTC heating element and HVAC relay. Interlock heating OFF immediately.",
                system_action="Heater shut OFF, emergency cooling engaged",
                room_temp_f=temp_f,
                apparent_temp_f=apparent_f,
                outside_temp_f=outside_temp_f,
                humidity=humidity,
                rate_of_change_f_per_min=dT_dt,
                actuator_state=actuators,
                queued_offline=not wifi_online
            )
            new_alerts.append(alert)

        elif dT_dt <= self.temp_drop_threshold and not self._is_in_cooldown(AlertCode.SUDDEN_TEMP_DROP, t):
            self.cooldown_tracker[AlertCode.SUDDEN_TEMP_DROP.value] = t
            alert = AlertRecord(
                alert_id=self._next_alert_id(),
                timestamp=t,
                code=AlertCode.SUDDEN_TEMP_DROP,
                severity=AlertSeverity.WARNING,
                title="SUDDEN TEMPERATURE PLUMMET",
                simplified_title="Sudden rapid drop in temperature",
                message=(f"Zone temperature dropping rapidly: {temp_f:.1f}°F "
                         f"(Rate: {dT_dt:.2f}°F/min). Check for open exterior windows or doors."),
                recommended_action="Verify building envelope seals and outdoor dampers.",
                system_action="Heating increased to maintain setpoint",
                room_temp_f=temp_f,
                apparent_temp_f=apparent_f,
                outside_temp_f=outside_temp_f,
                humidity=humidity,
                rate_of_change_f_per_min=dT_dt,
                actuator_state=actuators,
                queued_offline=not wifi_online
            )
            new_alerts.append(alert)

        # -------------------------------------------------------------
        # 2. Anomaly Check: Physiological Heat Stress (Elderly Resident)
        # -------------------------------------------------------------
        if (apparent_f >= self.heat_stress_apparent_limit or temp_f >= self.heat_stress_drybulb_limit) and \
           not self._is_in_cooldown(AlertCode.HEAT_STRESS_RISK, t):
            self.cooldown_tracker[AlertCode.HEAT_STRESS_RISK.value] = t
            alert = AlertRecord(
                alert_id=self._next_alert_id(),
                timestamp=t,
                code=AlertCode.HEAT_STRESS_RISK,
                severity=AlertSeverity.EMERGENCY,
                title="HEAT STRESS RISK: VULNERABLE OCCUPANT ALERT",
                simplified_title="Dangerous indoor heat stress detected",
                message=(f"Indoor thermal environment exceeds safe human tolerance: "
                         f"Room {temp_f:.1f}°F, Apparent 'Feels Like' {apparent_f:.1f}°F (RH: {humidity:.0f}%). "
                         f"Elderly occupants exhibit diminished heat perception and high heatstroke risk."),
                recommended_action="Engage maximum emergency cooling. Caregiver must check occupant wellness immediately.",
                system_action="Emergency cooling engaged at 100% duty cycle",
                room_temp_f=temp_f,
                apparent_temp_f=apparent_f,
                outside_temp_f=outside_temp_f,
                humidity=humidity,
                rate_of_change_f_per_min=dT_dt,
                actuator_state=actuators,
                queued_offline=not wifi_online
            )
            new_alerts.append(alert)

        # -------------------------------------------------------------
        # 3. Anomaly Check: Freeze Risk
        # -------------------------------------------------------------
        if temp_f <= self.freeze_limit and not self._is_in_cooldown(AlertCode.FREEZE_RISK, t):
            self.cooldown_tracker[AlertCode.FREEZE_RISK.value] = t
            alert = AlertRecord(
                alert_id=self._next_alert_id(),
                timestamp=t,
                code=AlertCode.FREEZE_RISK,
                severity=AlertSeverity.CRITICAL,
                title="LOW TEMPERATURE FREEZE WARNING",
                simplified_title="Low indoor temperature freeze warning",
                message=(f"Zone temperature critically low: {temp_f:.1f}°F. "
                         f"Imminent risk of pipe freezing and occupant hypothermia."),
                recommended_action="Emergency heating override engaged. Inspect furnace and building insulation.",
                system_action="Auxiliary emergency heat engaged at 100%",
                room_temp_f=temp_f,
                apparent_temp_f=apparent_f,
                outside_temp_f=outside_temp_f,
                humidity=humidity,
                rate_of_change_f_per_min=dT_dt,
                actuator_state=actuators,
                queued_offline=not wifi_online
            )
            new_alerts.append(alert)

        # -------------------------------------------------------------
        # 4. Anomaly Check: Blower Motor Failure (Fan Seized)
        # -------------------------------------------------------------
        if fan_cmd_pct > 15.0 and fan_rpm < 100.0:
            self.blower_mis_timer += 1.0
            if self.blower_mis_timer >= 5.0 and not self._is_in_cooldown(AlertCode.BLOWER_STALL, t):
                self.cooldown_tracker[AlertCode.BLOWER_STALL.value] = t
                alert = AlertRecord(
                    alert_id=self._next_alert_id(),
                    timestamp=t,
                    code=AlertCode.BLOWER_STALL,
                    severity=AlertSeverity.CRITICAL,
                    title="BLOWER MOTOR FAILURE / STALL",
                    simplified_title="HVAC blower motor failure detected (0 RPM)",
                    message=(f"Blower commanded at {fan_cmd_pct:.0f}% but tachometer reads {fan_rpm:.0f} RPM "
                             f"and duct velocity is {air_velocity:.2f} m/s. Actuator stalled."),
                    recommended_action="Safety interlock: Disengage 12V PTC heater immediately to prevent fire.",
                    system_action="Heater and compressor cut OFF to prevent damage",
                    room_temp_f=temp_f,
                    apparent_temp_f=apparent_f,
                    outside_temp_f=outside_temp_f,
                    humidity=humidity,
                    rate_of_change_f_per_min=dT_dt,
                    actuator_state=actuators,
                    queued_offline=not wifi_online
                )
                new_alerts.append(alert)
        else:
            self.blower_mis_timer = 0.0

        # -------------------------------------------------------------
        # 5. Anomaly Check: Filter Clog / Excessive Static Pressure
        # -------------------------------------------------------------
        if static_dp >= 280.0 and not self._is_in_cooldown(AlertCode.FILTER_RESTRICTION, t):
            self.cooldown_tracker[AlertCode.FILTER_RESTRICTION.value] = t
            alert = AlertRecord(
                alert_id=self._next_alert_id(),
                timestamp=t,
                code=AlertCode.FILTER_RESTRICTION,
                severity=AlertSeverity.WARNING,
                title="AIR DUCT FILTER RESTRICTION / HIGH STATIC PRESSURE",
                simplified_title="Air filter severely clogged (High dP)",
                message=(f"Static pressure rose to {static_dp:.0f} Pa. "
                         f"Airflow restricted, compressor capped at 50% to prevent coil icing."),
                recommended_action="Replace HVAC return filter media (MERV-13) promptly.",
                system_action="Blower boosted +25%, compressor capped at 50%",
                room_temp_f=temp_f,
                apparent_temp_f=apparent_f,
                outside_temp_f=outside_temp_f,
                humidity=humidity,
                rate_of_change_f_per_min=dT_dt,
                actuator_state=actuators,
                queued_offline=not wifi_online
            )
            new_alerts.append(alert)

        # -------------------------------------------------------------
        # 6. Anomaly Check: Primary MCU-A Watchdog Failure
        # -------------------------------------------------------------
        if not mcu_a_ok and not self._is_in_cooldown(AlertCode.MCU_WATCHDOG_FAIL, t):
            self.cooldown_tracker[AlertCode.MCU_WATCHDOG_FAIL.value] = t
            alert = AlertRecord(
                alert_id=self._next_alert_id(),
                timestamp=t,
                code=AlertCode.MCU_WATCHDOG_FAIL,
                severity=AlertSeverity.CRITICAL,
                title="PRIMARY ESP32 (MCU-A) CRASH & FAILOVER",
                simplified_title="Primary controller crashed - switched to backup",
                message="MCU-A heartbeat expired. Watchdog triggered bumpless failover to MCU-B hot-standby.",
                recommended_action="Reboot primary microcontroller and inspect FreeRTOS heap memory.",
                system_action="Redundant MCU-B took over control bumplessly",
                room_temp_f=temp_f,
                apparent_temp_f=apparent_f,
                outside_temp_f=outside_temp_f,
                humidity=humidity,
                rate_of_change_f_per_min=dT_dt,
                actuator_state=actuators,
                queued_offline=not wifi_online
            )
            new_alerts.append(alert)

        # -------------------------------------------------------------
        # 7. Anomaly Check: Dual Temperature Sensor Discrepancy
        # -------------------------------------------------------------
        if sens_a_c is not None and sens_b_c is not None:
            discrepancy_f = abs(c_to_f(sens_a_c) - c_to_f(sens_b_c))
            if discrepancy_f >= 3.0 and not self._is_in_cooldown(AlertCode.SENSOR_CROSS_CHECK, t):
                self.cooldown_tracker[AlertCode.SENSOR_CROSS_CHECK.value] = t
                alert = AlertRecord(
                    alert_id=self._next_alert_id(),
                    timestamp=t,
                    code=AlertCode.SENSOR_CROSS_CHECK,
                    severity=AlertSeverity.WARNING,
                    title="TEMP SENSOR TS-A/TS-B CROSS-CHECK DIVERGENCE",
                    simplified_title="Sensor discrepancy detected - switched to backup",
                    message=(f"Sensor A ({c_to_f(sens_a_c):.1f}°F) diverges from Sensor B "
                             f"({c_to_f(sens_b_c):.1f}°F) by {discrepancy_f:.1f}°F."),
                    recommended_action="TS-A voted out. Operating PID control on TS-B. Calibrate sensors.",
                    system_action="TS-A voted out, regulating on redundant TS-B",
                    room_temp_f=temp_f,
                    apparent_temp_f=apparent_f,
                    outside_temp_f=outside_temp_f,
                    humidity=humidity,
                    rate_of_change_f_per_min=dT_dt,
                    actuator_state=actuators,
                    queued_offline=not wifi_online
                )
                new_alerts.append(alert)

        # -------------------------------------------------------------
        # 8. Offline Edge Buffer & Network Restoration Management
        # -------------------------------------------------------------
        if not wifi_online:
            # Buffer new alerts while offline
            for alert in new_alerts:
                self.offline_queue.append(alert)
        else:
            # If Wi-Fi just reconnected and we have queued alerts, flush them!
            if not self.prev_wifi_state and len(self.offline_queue) > 0:
                flush_count = len(self.offline_queue)
                reconnect_alert = AlertRecord(
                    alert_id=self._next_alert_id(),
                    timestamp=t,
                    code=AlertCode.CLOUD_LINK_RESTORED,
                    severity=AlertSeverity.INFO,
                    title="IOT CLOUD LINK RESTORED: QUEUED ALERTS FLUSHED",
                    message=(f"Wi-Fi & MQTT connection re-established. Dispatched {flush_count} "
                             f"buffered alerts accumulated during network outage."),
                    recommended_action="Review offline incident log timestamps.",
                    room_temp_f=temp_f,
                    apparent_temp_f=apparent_f,
                    humidity=humidity,
                    rate_of_change_f_per_min=dT_dt,
                    actuator_state=actuators,
                    queued_offline=False
                )
                new_alerts.append(reconnect_alert)
                
                # Mark queued alerts as dispatched
                for q_alert in self.offline_queue:
                    q_alert.dispatched_at = t
                self.offline_queue.clear()

        self.prev_wifi_state = wifi_online
        self.alert_history.extend(new_alerts)
        return new_alerts


class MultiChannelDispatcher:
    """
    Handles formatting and transmitting notifications across:
    - SMS / Text Messages (Twilio REST API or Carrier Email-to-SMS)
    - Responsive HTML Caregiver Email (SMTP / SendGrid format)
    - IoT Telemetry Payloads (MQTT / Webhook JSON)
    """
    def __init__(
        self,
        caregiver_phone: str = "+1 (312) 555-0199",
        caregiver_email: str = "caregiver@illinoistech.edu",
        facility_name: str = "Illinois Tech ECE 441 Smart HVAC Suite 101"
    ):
        self.caregiver_phone = caregiver_phone
        self.caregiver_email = caregiver_email
        self.facility_name = facility_name

    def format_sms(self, alert: AlertRecord) -> str:
        """
        Creates clean, structured cellular SMS text message matching user specification:
        Line 1: Simplified alert message (e.g. Sudden rapid increase in temperature)
        Line 2: Room Temp -> Feels Like -> Outside Temp
        Line 3: Action that is being taken by the system
        """
        headline = alert.simplified_title or alert.title
        temps = f"Room {alert.room_temp_f:.1f}F -> Feels Like {alert.apparent_temp_f:.1f}F -> Outside {alert.outside_temp_f:.1f}F"
        action = f"System Action: {alert.system_action or alert.recommended_action}"
        return f"{headline}\n{temps}\n{action}"

    def format_carrier_sms_email(self, alert: AlertRecord, carrier_domain: str = "txt.att.net") -> Tuple[str, str, str]:
        """
        Formats alert for free Carrier Email-to-SMS Gateway:
        e.g., [10-digit-phone]@txt.att.net, @vtext.com, @tmomail.net
        """
        clean_phone = "".join(filter(str.isdigit, self.caregiver_phone))
        gateway_email = f"{clean_phone}@{carrier_domain}"
        subject = f"HVAC-{alert.severity.value}: {alert.code.value}"
        body = self.format_sms(alert)
        return gateway_email, subject, body

    def format_email_html(self, alert: AlertRecord) -> str:
        """
        Generates responsive, professional HTML email for caregiver alert notification.
        """
        sev_color = {
            AlertSeverity.INFO: "#38bdf8",
            AlertSeverity.WARNING: "#f59e0b",
            AlertSeverity.CRITICAL: "#ef4444",
            AlertSeverity.EMERGENCY: "#dc2626"
        }.get(alert.severity, "#ef4444")

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; background: #0f172a; color: #f8fafc;">
            <div style="background-color: {sev_color}; color: #ffffff; padding: 16px 20px;">
                <div style="font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 700;">
                    {self.facility_name} &bull; PRIORITY DISPATCH
                </div>
                <h2 style="margin: 6px 0 0 0; font-size: 20px; font-weight: 800;">
                    {alert.severity.value}: {alert.title}
                </h2>
            </div>
            <div style="padding: 20px;">
                <div style="display: flex; gap: 12px; margin-bottom: 18px; border-bottom: 1px solid #334155; padding-bottom: 14px;">
                    <div style="flex: 1;">
                        <span style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Diagnostic Code</span>
                        <div style="font-size: 16px; font-weight: 700; color: #38bdf8; font-family: monospace;">{alert.code.value}</div>
                    </div>
                    <div style="flex: 1;">
                        <span style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Alert ID</span>
                        <div style="font-size: 14px; font-weight: 600; color: #e2e8f0; font-family: monospace;">{alert.alert_id}</div>
                    </div>
                    <div style="flex: 1.5;">
                        <span style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Timestamp</span>
                        <div style="font-size: 13px; font-weight: 500; color: #e2e8f0;">{alert.timestamp_iso}</div>
                    </div>
                </div>

                <div style="background: #1e293b; border-radius: 6px; padding: 14px; margin-bottom: 18px;">
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; font-weight: 600;">Environmental Telemetry</div>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr>
                            <td style="padding: 4px 0; color: #cbd5e1;">Room Dry-Bulb Temp:</td>
                            <td style="padding: 4px 0; font-weight: 700; text-align: right; color: #f8fafc;">{alert.room_temp_f:.1f} &deg;F</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 0; color: #cbd5e1;">Feels Like (Apparent):</td>
                            <td style="padding: 4px 0; font-weight: 700; text-align: right; color: #f8fafc;">{alert.apparent_temp_f:.1f} &deg;F</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 0; color: #cbd5e1;">Rate of Change (dT/dt):</td>
                            <td style="padding: 4px 0; font-weight: 700; text-align: right; color: {sev_color};">{alert.rate_of_change_f_per_min:+.2f} &deg;F/min</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 0; color: #cbd5e1;">Relative Humidity:</td>
                            <td style="padding: 4px 0; font-weight: 700; text-align: right; color: #f8fafc;">{alert.humidity:.1f} %</td>
                        </tr>
                    </table>
                </div>

                <div style="margin-bottom: 18px;">
                    <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: #e2e8f0; margin-bottom: 6px;">Anomaly Description</div>
                    <p style="font-size: 14px; line-height: 1.5; color: #cbd5e1; margin: 0;">{alert.message}</p>
                </div>

                <div style="background: rgba(220, 38, 38, 0.15); border-left: 4px solid {sev_color}; padding: 12px; border-radius: 4px; margin-bottom: 20px;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #fca5a5; margin-bottom: 4px;">Recommended Action</div>
                    <div style="font-size: 13px; font-weight: 600; color: #ffffff;">{alert.recommended_action}</div>
                </div>

                <div style="font-size: 11px; color: #64748b; text-align: center; border-top: 1px solid #1e293b; padding-top: 12px;">
                    Generated by ESP32 Edge Core 0 Telemetry Daemon &bull; ECE 441 Fall 2026
                </div>
            </div>
        </div>
        """
        return html

    def dispatch(self, alert: AlertRecord, channels=("sms", "email", "mqtt")) -> Dict[str, Any]:
        """
        Executes simulated or live multi-channel dispatch.
        """
        results = {}
        alert.dispatched_at = time.time()
        
        if "sms" in channels:
            sms_text = self.format_sms(alert)
            alert.dispatch_channels.append("SMS")
            results["sms"] = {
                "status": "DELIVERED",
                "recipient": self.caregiver_phone,
                "length": len(sms_text),
                "payload": sms_text
            }

        if "email" in channels:
            email_html = self.format_email_html(alert)
            alert.dispatch_channels.append("EMAIL")
            results["email"] = {
                "status": "DELIVERED",
                "recipient": self.caregiver_email,
                "subject": f"[{alert.severity.value}] {alert.title}",
                "html_length": len(email_html)
            }

        if "mqtt" in channels:
            alert.dispatch_channels.append("MQTT")
            results["mqtt"] = {
                "status": "PUBLISHED",
                "topic": "ece441/hvac/alerts",
                "qos": 1,
                "payload": alert.to_dict()
            }

        return results
