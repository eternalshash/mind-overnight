#!/usr/bin/env python3
"""
================================================================================
IAMD GLOBAL DEFENSE SIMULATOR: INTEGRATED TACTICAL DASH APPLICATION
File: app.py
================================================================================
Full Plotly Dash web application implementing a multi-theater, multi-tier
Integrated Air & Missile Defense (IAMD) Command & Control HUD.

Integrates:
- `catalog.py`: Real-world weapon specifications, ranges, velocities, and site templates
- `physics_engine.py`: WGS84 geodesics, 3-DoF RK4 trajectory simulation, and telemetry
- `defense_system.py`: Multi-tier IAMD fire control, TPN guidance, and 100x Monte Carlo
- `map_views.py`: 2D Tactical Leaflet Map, 3D Digital Globe, and Missilemap Altitude Profiles
- `telemetry.py`: Military HUD Speedometer/Mach gauge, altimeter, flight phase badges,
  real-time active track matrix, and mission outcome indicators

Easter Egg:
- 10% probability trigger on strike launch:
  Spawns an animated simulated stealth fighter (F-22 Raptor / F-35 Lightning II) ingress path,
  releases mid-air stand-off weapon, and broadcasts high-priority tactical telemetry alert.
================================================================================
"""

import math
import random
import time
from typing import Dict, List, Any, Optional

import dash
from dash import html, dcc, dash_table, Input, Output, State, ALL, ctx
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
import dash_leaflet as dl

# Core domain modules
import catalog
import physics_engine
import defense_system
import map_views
import telemetry

# ==============================================================================
# 1. APPLICATION SETUP & THEME CONFIGURATION
# ==============================================================================
app = dash.Dash(
    __name__,
    title="IAMD GLOBAL DEFENSE SIMULATOR",
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)
server = app.server

MIL_DARK = {
    "bg_main": "#060a12",
    "card_bg": "#0b111e",
    "card_border": "#1b2538",
    "accent_cyan": "#00f0ff",
    "accent_green": "#00e676",
    "accent_amber": "#ffb300",
    "accent_red": "#ff1744",
    "accent_purple": "#d500f9",
    "text_main": "#f8fafc",
    "text_muted": "#8b949e",
    "font_mono": "'SF Mono', Monaco, Consolas, 'Courier New', monospace",
}

# ==============================================================================
# 2. SCENARIO PRESETS & SIMULATION DATA ENGINE
# ==============================================================================
SCENARIO_PRESETS = {
    "eastern_europe": {
        "name": "Eastern Europe / Black Sea (Iskander-M + Kinzhal vs. Patriot/S-400)",
        "theater_key": "eastern_europe",
        "description": "High-density multi-axis raid: Quasi-ballistic Iskander-M and Mach 10 Kinzhal vs. layered Patriot PAC-3 MSE and S-400 defense screen.",
        "duration_s": 120.0,
        "tracks": [
            {
                "id": "TRK-01",
                "name": "9K720 Iskander-M",
                "faction": "Aggressor",
                "type": "Quasi-Ballistic",
                "weapon_id": "iskander_m",
                "max_mach": 6.2,
                "apogee_km": 50.0,
                "range_km": 480.0,
                "flight_time_s": 95.0,
                "target": "Kyiv Strategic C2 Hub",
                "origin": "Rostov-on-Don Launch Complex",
                "warhead": "480 kg HE Blast Frag",
                "guidance": "GLONASS / Optical DSMAC",
                "intercept_time_s": 72.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-01",
                "launch_lat": 47.23, "launch_lon": 39.72,
                "target_lat": 50.45, "target_lon": 30.52,
            },
            {
                "id": "TRK-02",
                "name": "Kh-47M2 Kinzhal",
                "faction": "Aggressor",
                "type": "Hypersonic",
                "weapon_id": "kinzhal",
                "max_mach": 9.8,
                "apogee_km": 35.0,
                "range_km": 650.0,
                "flight_time_s": 75.0,
                "target": "Zhulyany Radar Array",
                "origin": "Air-Launch (MiG-31K Black Sea)",
                "warhead": "500 kg Penetrator",
                "guidance": "INS / Active Millimeter-Wave",
                "intercept_time_s": 58.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-01",
                "launch_lat": 44.50, "launch_lon": 34.00,
                "target_lat": 50.40, "target_lon": 30.45,
            },
            {
                "id": "TRK-03",
                "name": "Shahed-136 (Lead)",
                "faction": "Aggressor",
                "type": "Drone Swarm",
                "weapon_id": "shahed_136",
                "max_mach": 0.16,
                "apogee_km": 0.35,
                "range_km": 320.0,
                "flight_time_s": 240.0,
                "target": "Vasylkiv Forward Airbase",
                "origin": "Cape Chauda Pad Alpha",
                "warhead": "50 kg Thermobaric",
                "guidance": "CRPA Anti-Jam GNSS",
                "intercept_time_s": 48.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-02",
                "launch_lat": 45.00, "launch_lon": 35.85,
                "target_lat": 50.18, "target_lon": 30.30,
            },
            {
                "id": "TRK-04",
                "name": "Shahed-136 (Wingman)",
                "faction": "Aggressor",
                "type": "Drone Swarm",
                "weapon_id": "shahed_136",
                "max_mach": 0.16,
                "apogee_km": 0.28,
                "range_km": 310.0,
                "flight_time_s": 235.0,
                "target": "Vasylkiv Forward Airbase",
                "origin": "Cape Chauda Pad Beta",
                "warhead": "50 kg Blast Frag",
                "guidance": "CRPA Anti-Jam GNSS",
                "intercept_time_s": 52.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-02",
                "launch_lat": 45.02, "launch_lon": 35.88,
                "target_lat": 50.18, "target_lon": 30.30,
            },
            {
                "id": "INT-01",
                "name": "Patriot PAC-3 MSE",
                "faction": "Defender",
                "type": "Interceptor",
                "weapon_id": "patriot_pac3",
                "max_mach": 4.5,
                "apogee_km": 36.0,
                "range_km": 120.0,
                "flight_time_s": 40.0,
                "target": "TRK-01 / TRK-02",
                "origin": "Kyiv Patriot Battery 1",
                "warhead": "Kinetic Hit-to-Kill (HTK)",
                "guidance": "Ka-band Active Seeker + ACM",
                "intercept_time_s": 72.0,
                "outcome": "DIRECT HIT",
                "intercept_by": None,
                "launch_lat": 50.45, "launch_lon": 30.55,
                "target_lat": 48.80, "target_lon": 35.00,
            },
            {
                "id": "INT-02",
                "name": "Anduril Roadrunner-M",
                "faction": "Defender",
                "type": "C-UAS Interceptor",
                "weapon_id": "anduril_roadrunner_m",
                "max_mach": 0.90,
                "apogee_km": 6.0,
                "range_km": 80.0,
                "flight_time_s": 65.0,
                "target": "TRK-03 / TRK-04",
                "origin": "Vasylkiv Roadrunner Nest",
                "warhead": "High-Explosive Fragmentation",
                "guidance": "Lattice OS Autonomous Seeker",
                "intercept_time_s": 48.0,
                "outcome": "DIRECT HIT",
                "intercept_by": None,
                "launch_lat": 50.18, "launch_lon": 30.32,
                "target_lat": 48.00, "target_lon": 33.00,
            },
        ],
    },
    "persian_gulf": {
        "name": "Persian Gulf / Red Sea (Saturation Drone Swarm vs. Roadrunner & CIWS)",
        "theater_key": "persian_gulf",
        "description": "Maritime chokepoint defense: Low-cost saturation drone clusters & cruise missiles attacking naval assets defended by Phalanx CIWS and Anduril Roadrunner.",
        "duration_s": 120.0,
        "tracks": [
            {
                "id": "TRK-01",
                "name": "Quds-2 Cruise Missile",
                "faction": "Aggressor",
                "type": "Cruise Missile",
                "weapon_id": "kalibr",
                "max_mach": 0.82,
                "apogee_km": 0.15,
                "range_km": 420.0,
                "flight_time_s": 110.0,
                "target": "Strait Escort Destroyer",
                "origin": "Coastal TEL Emplacement",
                "warhead": "250 kg HE",
                "guidance": "Terrain Contour / GPS",
                "intercept_time_s": 65.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-01",
                "launch_lat": 26.50, "launch_lon": 55.00,
                "target_lat": 25.20, "target_lon": 56.40,
            },
            {
                "id": "TRK-02",
                "name": "Shahed-136 Attack Cluster",
                "faction": "Aggressor",
                "type": "Drone Swarm",
                "weapon_id": "shahed_136",
                "max_mach": 0.16,
                "apogee_km": 0.20,
                "range_km": 280.0,
                "flight_time_s": 180.0,
                "target": "Fujairah Energy Terminal",
                "origin": "Bandar Abbas Depot",
                "warhead": "50 kg Blast Frag",
                "guidance": "GNSS / Optical",
                "intercept_time_s": 50.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-02",
                "launch_lat": 27.18, "launch_lon": 56.27,
                "target_lat": 25.13, "target_lon": 56.34,
            },
            {
                "id": "INT-01",
                "name": "Anduril Roadrunner-M",
                "faction": "Defender",
                "type": "C-UAS Interceptor",
                "weapon_id": "anduril_roadrunner_m",
                "max_mach": 0.90,
                "apogee_km": 8.0,
                "range_km": 90.0,
                "flight_time_s": 70.0,
                "target": "TRK-01",
                "origin": "Naval Mobile Nest",
                "warhead": "High-Explosive Frag",
                "guidance": "Lattice AI Computer Vision",
                "intercept_time_s": 65.0,
                "outcome": "DIRECT HIT",
                "intercept_by": None,
                "launch_lat": 25.20, "launch_lon": 56.40,
                "target_lat": 26.00, "target_lon": 55.50,
            },
            {
                "id": "INT-02",
                "name": "Phalanx 20mm LPWS",
                "faction": "Defender",
                "type": "CIWS Rotary Cannon",
                "weapon_id": "phalanx_lpws",
                "max_mach": 3.1,
                "apogee_km": 2.0,
                "range_km": 3.5,
                "flight_time_s": 6.0,
                "target": "TRK-02",
                "origin": "Point Defense Mount Bravo",
                "warhead": "20mm Tungsten Tracer Stream",
                "guidance": "Ku-band Tracking Radar",
                "intercept_time_s": 50.0,
                "outcome": "DIRECT HIT",
                "intercept_by": None,
                "launch_lat": 25.13, "launch_lon": 56.34,
                "target_lat": 25.15, "target_lon": 56.32,
            },
        ],
    },
    "taiwan_strait": {
        "name": "Taiwan Strait (DF-17 Hypersonic Glide & DF-21D ASBM vs. THAAD & SM-3)",
        "theater_key": "taiwan_strait",
        "description": "Anti-Access Area-Denial (A2/AD) salvo: Waverider hypersonic glide vehicles and anti-ship ballistic missiles vs. Aegis SM-3 Block IIA and THAAD.",
        "duration_s": 120.0,
        "tracks": [
            {
                "id": "TRK-01",
                "name": "DF-17 Hypersonic Glide Vehicle",
                "faction": "Aggressor",
                "type": "Hypersonic HGV",
                "weapon_id": "df17",
                "max_mach": 8.5,
                "apogee_km": 55.0,
                "range_km": 850.0,
                "flight_time_s": 105.0,
                "target": "Taipei Early Warning Radar",
                "origin": "Fujian Missile Base",
                "warhead": "500 kg High-Explosive",
                "guidance": "BeiDou + Radar Scene Matching",
                "intercept_time_s": 76.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-01",
                "launch_lat": 26.08, "launch_lon": 119.30,
                "target_lat": 24.80, "target_lon": 121.20,
            },
            {
                "id": "TRK-02",
                "name": "DF-21D Carrier Killer ASBM",
                "faction": "Aggressor",
                "type": "Anti-Ship Ballistic",
                "weapon_id": "df21d",
                "max_mach": 10.0,
                "apogee_km": 280.0,
                "range_km": 1200.0,
                "flight_time_s": 115.0,
                "target": "Carrier Strike Group CVN-76",
                "origin": "Jiangxi Deep Complex",
                "warhead": "600 kg Armor Piercing / EMP",
                "guidance": "MaRV Millimeter-Wave Seeker",
                "intercept_time_s": 84.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-02",
                "launch_lat": 27.50, "launch_lon": 116.00,
                "target_lat": 23.00, "target_lon": 124.00,
            },
            {
                "id": "INT-01",
                "name": "THAAD Interceptor",
                "faction": "Defender",
                "type": "Exo/Endo Interceptor",
                "weapon_id": "thaad",
                "max_mach": 8.2,
                "apogee_km": 120.0,
                "range_km": 200.0,
                "flight_time_s": 45.0,
                "target": "TRK-01",
                "origin": "Taoyuan THAAD Site",
                "warhead": "Pure Kinetic Hit-to-Kill",
                "guidance": "AN/TPY-2 Radar Uplink + MWIR",
                "intercept_time_s": 76.0,
                "outcome": "DIRECT HIT",
                "intercept_by": None,
                "launch_lat": 24.95, "launch_lon": 121.25,
                "target_lat": 25.50, "target_lon": 120.50,
            },
            {
                "id": "INT-02",
                "name": "SM-3 Block IIA",
                "faction": "Defender",
                "type": "Exo-Atmospheric Interceptor",
                "weapon_id": "sm3_block_iia",
                "max_mach": 15.0,
                "apogee_km": 500.0,
                "range_km": 2000.0,
                "flight_time_s": 55.0,
                "target": "TRK-02",
                "origin": "Aegis Cruiser USS Shiloh",
                "warhead": "Kinetic Warhead (KW)",
                "guidance": "SPY-6 Midcourse + Dual-Color IR",
                "intercept_time_s": 84.0,
                "outcome": "DIRECT HIT",
                "intercept_by": None,
                "launch_lat": 23.20, "launch_lon": 123.80,
                "target_lat": 25.00, "target_lon": 120.00,
            },
        ],
    },
    "conus_homeland": {
        "name": "CONUS Strategic Homeland Defense (Minuteman III / Sarmat ICBM Track)",
        "theater_key": "conus_homeland",
        "description": "Strategic deterrence verification: Intercontinental suborbital exo-atmospheric trajectories exceeding 1,000 km apogee defended by Homeland GBD and SM-3 Block IIA.",
        "duration_s": 120.0,
        "tracks": [
            {
                "id": "TRK-01",
                "name": "RS-28 Sarmat ICBM Reentry",
                "faction": "Aggressor",
                "type": "Heavy ICBM",
                "weapon_id": "sarmat",
                "max_mach": 20.7,
                "apogee_km": 1150.0,
                "range_km": 8500.0,
                "flight_time_s": 118.0,
                "target": "NORAD Cheyenne Mountain",
                "origin": "Polar Trajectory Corridor",
                "warhead": "Heavy MIRV Bus",
                "guidance": "Astro-Inertial / GLONASS",
                "intercept_time_s": 88.0,
                "outcome": "INTERCEPTED",
                "intercept_by": "INT-01",
                "launch_lat": 68.00, "launch_lon": -90.00,
                "target_lat": 38.74, "target_lon": -104.84,
            },
            {
                "id": "INT-01",
                "name": "Ground-Based Interceptor (GBI / SM-3)",
                "faction": "Defender",
                "type": "Exo-Atmospheric Interceptor",
                "weapon_id": "sm3_block_iia",
                "max_mach": 15.0,
                "apogee_km": 800.0,
                "range_km": 2500.0,
                "flight_time_s": 50.0,
                "target": "TRK-01",
                "origin": "Fort Greely GMD Site",
                "warhead": "Exo-Atmospheric Kill Vehicle (EKV)",
                "guidance": "Long-Range X-Band Radar",
                "intercept_time_s": 88.0,
                "outcome": "DIRECT HIT",
                "intercept_by": None,
                "launch_lat": 44.00, "launch_lon": -105.00,
                "target_lat": 50.00, "target_lon": -100.00,
            },
        ],
    },
}


def calculate_track_telemetry_at_time(
    track: Dict[str, Any], t_sec: float
) -> Dict[str, Any]:
    """
    Computes precise kinematic state of a track at simulation time t_sec.
    Incorporates physical phase transitions (BOOST, MIDCOURSE, GLIDE, TERMINAL, LOITER, INTERCEPT).
    """
    total_time = max(10.0, float(track.get("flight_time_s", 90.0)))
    t = max(0.0, min(total_time, float(t_sec)))
    progress_frac = t / total_time
    progress_pct = progress_frac * 100.0

    max_mach = float(track.get("max_mach", 4.0))
    apogee_km = float(track.get("apogee_km", 40.0))
    apogee_m = apogee_km * 1000.0
    total_range_km = float(track.get("range_km", 400.0))

    t_type = track.get("type", "Ballistic").lower()
    faction = track.get("faction", "Aggressor")
    outcome = track.get("outcome", "IN FLIGHT")
    intercept_time = float(track.get("intercept_time_s", total_time + 10.0))

    # Determine status & phase
    is_intercepted = (outcome == "INTERCEPTED" and t >= intercept_time)
    is_direct_hit = (outcome == "DIRECT HIT" and t >= intercept_time)

    if is_intercepted:
        status = "INTERCEPTED"
        phase = "TERMINAL"
    elif is_direct_hit:
        status = "DIRECT HIT"
        phase = "INTERCEPT"
    elif progress_pct >= 99.0:
        status = "DETONATED" if faction == "Aggressor" else "MISS"
        phase = "TERMINAL"
    elif t <= 0.0:
        status = "STANDBY"
        phase = "BOOST"
    else:
        status = "IN FLIGHT"
        if "interceptor" in t_type or faction == "Defender":
            phase = "INTERCEPT"
        elif "drone" in t_type:
            phase = "LOITER" if 0.25 <= progress_frac <= 0.85 else "TERMINAL"
        elif "hypersonic" in t_type:
            if progress_frac < 0.20:
                phase = "BOOST"
            elif progress_frac < 0.75:
                phase = "GLIDE"
            else:
                phase = "TERMINAL"
        elif "cruise" in t_type:
            phase = "MIDCOURSE" if progress_frac < 0.85 else "TERMINAL"
        else:  # Ballistic
            if progress_frac < 0.20:
                phase = "BOOST"
            elif progress_frac < 0.75:
                phase = "MIDCOURSE"
            else:
                phase = "TERMINAL"

    # Velocity profile
    if "drone" in t_type:
        current_mach = max_mach * min(1.0, progress_frac * 4.0)
    elif "cruise" in t_type:
        current_mach = max_mach * min(1.0, progress_frac * 3.0)
    else:
        # Ballistic & Hypersonic acceleration and terminal drag
        if progress_frac < 0.25:
            current_mach = max_mach * (progress_frac / 0.25)
        elif progress_frac < 0.75:
            current_mach = max_mach * (1.0 - 0.15 * math.sin((progress_frac - 0.25) * math.pi))
        else:
            current_mach = max_mach * (0.85 - 0.3 * (progress_frac - 0.75) / 0.25)

    speed_mps = current_mach * 315.0
    speed_kmh = speed_mps * 3.6

    # Altitude profile (Parabolic / Waverider / Low-contour)
    if "drone" in t_type or "cruise" in t_type:
        alt_m = apogee_m * (0.7 + 0.3 * math.sin(progress_frac * 12.0))
        vertical_speed_mps = 15.0 * math.cos(progress_frac * 12.0)
    elif "hypersonic" in t_type:
        # Depressed boost to glide with atmospheric wave skip
        glide_alt = apogee_m * 0.7
        if progress_frac < 0.2:
            alt_m = glide_alt * (progress_frac / 0.2)
            vertical_speed_mps = glide_alt / (0.2 * total_time)
        elif progress_frac < 0.8:
            alt_m = glide_alt + (apogee_m * 0.2) * math.sin((progress_frac - 0.2) * 4 * math.pi)
            vertical_speed_mps = 25.0 * math.cos((progress_frac - 0.2) * 4 * math.pi)
        else:
            dive_frac = (progress_frac - 0.8) / 0.2
            alt_m = max(0.0, glide_alt * (1.0 - dive_frac**1.8))
            vertical_speed_mps = -glide_alt / (0.2 * total_time) * 1.5
    else:  # Parabolic Keplerian trajectory
        norm_x = min(1.0, progress_frac)
        alt_m = 4.0 * apogee_m * norm_x * (1.0 - norm_x)
        # Derivative d(alt)/dt
        if t < total_time:
            vertical_speed_mps = (4.0 * apogee_m / total_time) * (1.0 - 2.0 * norm_x)
        else:
            vertical_speed_mps = 0.0

    # Distance metrics
    dist_traveled_km = total_range_km * progress_frac
    dist_remaining_km = max(0.0, total_range_km - dist_traveled_km)
    time_remaining_s = max(0.0, total_time - t)

    # Coordinates
    l_lat = track.get("launch_lat", 45.0)
    l_lon = track.get("launch_lon", 35.0)
    t_lat = track.get("target_lat", 50.0)
    t_lon = track.get("target_lon", 30.0)
    cur_lat = l_lat + (t_lat - l_lat) * progress_frac
    cur_lon = l_lon + (t_lon - l_lon) * progress_frac

    return {
        "id": track["id"],
        "name": track["name"],
        "faction": faction,
        "type": track["type"],
        "weapon_id": track.get("weapon_id"),
        "target": track.get("target", "Asset"),
        "origin": track.get("origin", "Base"),
        "warhead": track.get("warhead", "Conventional HE"),
        "guidance": track.get("guidance", "INS/GPS"),
        "mach": round(current_mach, 2),
        "speed_kmh": round(speed_kmh, 1),
        "speed_mps": round(speed_mps, 1),
        "alt_m": max(0.0, round(alt_m, 1)),
        "alt_km": max(0.0, round(alt_m / 1000.0, 2)),
        "apogee_m": apogee_m,
        "apogee_km": apogee_km,
        "vertical_speed_mps": round(vertical_speed_mps, 1),
        "dist_traveled_km": round(dist_traveled_km, 1),
        "dist_remaining_km": round(dist_remaining_km, 1),
        "etof_s": round(total_time, 1),
        "time_remaining_s": round(time_remaining_s, 1),
        "progress_pct": round(progress_pct, 1),
        "phase": phase,
        "status": status,
        "lat": cur_lat,
        "lon": cur_lon,
    }


# ==============================================================================
# 3. EASTER EGG: STEALTH FIGHTER (F-22 RAPTOR / F-35) AIR-LAUNCH
# ==============================================================================
def roll_easter_egg() -> Dict[str, Any]:
    """10% probability trigger on strike launch spawning stealth ingress."""
    triggered = (random.random() < 0.10)
    aircraft = random.choice(["F-22A Raptor", "F-35A Lightning II"])
    return {
        "active": triggered,
        "aircraft": aircraft,
        "callsign": "RAPTOR-01 (94TH FS)" if "F-22" in aircraft else "LIGHTNING-11 (388TH FW)",
        "ingress_speed_mach": 1.5 if "F-22" in aircraft else 1.2,
        "ingress_alt_ft": 45000 if "F-22" in aircraft else 38000,
        "banner_text": (
            f"AIR-LAUNCH DETECTED: {aircraft.upper()} DEPLOYED WEAPON AT MACH 1.5, ALT 45,000 FT"
            if "F-22" in aircraft
            else f"AIR-LAUNCH DETECTED: {aircraft.upper()} DEPLOYED WEAPON AT MACH 1.2, ALT 38,000 FT"
        ),
        "path_coords": [
            [42.5, 31.0], [43.6, 32.8], [44.5, 34.2], [45.1, 35.6]
        ],
    }


# ==============================================================================
# 4. DASH APPLICATION LAYOUT
# ==============================================================================
def create_top_navbar() -> dbc.Navbar:
    """Builds top command bar with Title, Presets, Theater jump, and View toggle."""
    scenario_options = [
        {"label": f"🎯 {cfg['name']}", "value": key}
        for key, cfg in SCENARIO_PRESETS.items()
    ]

    theater_options = [
        {"label": f"🌍 {data['name']}", "value": key}
        for key, data in map_views.THEATER_PRESETS.items()
    ]

    return dbc.Navbar(
        dbc.Container(
            [
                # Left Title & DEFCON Status
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Span("🛡️ ", style={"fontSize": "1.4rem"}),
                                    html.Strong(
                                        "IAMD GLOBAL DEFENSE SIMULATOR",
                                        style={
                                            "letterSpacing": "1.8px",
                                            "fontSize": "1.05rem",
                                            "color": MIL_DARK["accent_cyan"],
                                            "fontFamily": MIL_DARK["font_mono"],
                                        },
                                    ),
                                    dbc.Badge(
                                        "DEFCON 2 // ARMED",
                                        color="danger",
                                        className="ms-2 px-2 py-1 text-uppercase",
                                        style={
                                            "fontSize": "0.68rem",
                                            "letterSpacing": "1px",
                                            "border": "1px solid #ff1744",
                                            "backgroundColor": "rgba(255,23,68,0.2)",
                                        },
                                    ),
                                ],
                                className="d-flex align-items-center",
                            ),
                            width="auto",
                        ),
                    ],
                    align="center",
                    className="g-0",
                ),
                # Middle Controls: Scenario Preset, Theater Quick-Jump, 2D/3D Toggle
                dbc.Row(
                    [
                        # Scenario Preset Selector
                        dbc.Col(
                            html.Div(
                                [
                                    html.Small("SCENARIO PRESET:", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem", "fontWeight": "700"}),
                                    dcc.Dropdown(
                                        id="scenario-preset-select",
                                        options=scenario_options,
                                        value="eastern_europe",
                                        clearable=False,
                                        style={
                                            "backgroundColor": "#0d131f",
                                            "color": "#000000",
                                            "minWidth": "240px",
                                            "fontSize": "0.78rem",
                                            "fontFamily": MIL_DARK["font_mono"],
                                        },
                                    ),
                                ]
                            ),
                            width="auto",
                        ),
                        # Theater Quick-Jump
                        dbc.Col(
                            html.Div(
                                [
                                    html.Small("THEATER JUMP:", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem", "fontWeight": "700"}),
                                    dcc.Dropdown(
                                        id="theater-selector",
                                        options=theater_options,
                                        value="eastern_europe",
                                        clearable=False,
                                        style={
                                            "backgroundColor": "#0d131f",
                                            "color": "#000000",
                                            "minWidth": "190px",
                                            "fontSize": "0.78rem",
                                            "fontFamily": MIL_DARK["font_mono"],
                                        },
                                    ),
                                ]
                            ),
                            width="auto",
                        ),
                        # 2D/3D View Mode Toggle
                        dbc.Col(
                            html.Div(
                                [
                                    html.Small("TACTICAL VIEW:", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem", "fontWeight": "700"}),
                                    dcc.RadioItems(
                                        id="view-mode-toggle",
                                        options=[
                                            {"label": " 🛰️ 2D Map ", "value": "2d"},
                                            {"label": " 🌐 3D Globe ", "value": "3d"},
                                        ],
                                        value="2d",
                                        inline=True,
                                        style={
                                            "color": "#ffffff",
                                            "fontSize": "0.78rem",
                                            "fontFamily": MIL_DARK["font_mono"],
                                            "paddingTop": "4px",
                                        },
                                    ),
                                ]
                            ),
                            width="auto",
                        ),
                    ],
                    align="center",
                    className="g-3 my-1",
                ),
                # Right Buttons: Launch Strike Salvo & Monte Carlo Modal
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Button(
                                [html.Span("🚀 "), "STRIKE SALVO"],
                                id="btn-launch-strike",
                                color="danger",
                                size="sm",
                                className="px-3 fw-bold",
                                style={"letterSpacing": "1px", "fontFamily": MIL_DARK["font_mono"]},
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            dbc.Button(
                                [html.Span("🎲 "), "100x MONTE CARLO"],
                                id="btn-open-monte-carlo",
                                color="warning",
                                size="sm",
                                className="px-3 fw-bold text-dark",
                                style={"letterSpacing": "1px", "fontFamily": MIL_DARK["font_mono"]},
                            ),
                            width="auto",
                        ),
                    ],
                    align="center",
                    className="g-2",
                ),
            ],
            fluid=True,
        ),
        color="#080c16",
        dark=True,
        sticky="top",
        style={"borderBottom": f"1px solid {MIL_DARK['card_border']}", "boxShadow": "0 4px 18px rgba(0,0,0,0.6)"},
    )

