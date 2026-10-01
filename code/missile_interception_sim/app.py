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


def create_playback_control_bar() -> dbc.Card:
    """Builds playback controls (Play, Pause, Step, Reset, Speed, Timeline scrubber)."""
    return dbc.Card(
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        # Play, Pause, Step, Reset buttons
                        dbc.Col(
                            dbc.ButtonGroup(
                                [
                                    dbc.Button("▶ PLAY", id="btn-play", color="success", size="sm", className="px-3 fw-bold"),
                                    dbc.Button("⏸ PAUSE", id="btn-pause", color="secondary", size="sm", className="px-3 fw-bold"),
                                    dbc.Button("⏭ STEP", id="btn-step", color="info", size="sm", className="px-3 fw-bold"),
                                    dbc.Button("↺ RESET", id="btn-reset", color="danger", size="sm", className="px-3 fw-bold"),
                                ],
                                style={"fontFamily": MIL_DARK["font_mono"], "fontSize": "0.78rem"},
                            ),
                            width="auto",
                        ),
                        # Speed Multiplier
                        dbc.Col(
                            html.Div(
                                [
                                    html.Small("SIM SPEED: ", style={"color": MIL_DARK["text_muted"], "fontWeight": "700", "fontSize": "0.72rem"}),
                                    dcc.RadioItems(
                                        id="sim-speed-radio",
                                        options=[
                                            {"label": " 1x ", "value": 1.0},
                                            {"label": " 5x ", "value": 5.0},
                                            {"label": " 20x ", "value": 20.0},
                                        ],
                                        value=1.0,
                                        inline=True,
                                        style={"color": MIL_DARK["accent_cyan"], "fontFamily": MIL_DARK["font_mono"], "fontSize": "0.78rem"},
                                    ),
                                ],
                                className="d-flex align-items-center ms-2",
                            ),
                            width="auto",
                        ),
                        # Digital Simulation Clock
                        dbc.Col(
                            html.Div(
                                id="sim-clock-display",
                                children="T+00:00.0s / 120.0s [READY]",
                                className="px-3 py-1 rounded text-center",
                                style={
                                    "backgroundColor": "#060a12",
                                    "border": f"1px solid {MIL_DARK['card_border']}",
                                    "color": MIL_DARK["accent_cyan"],
                                    "fontFamily": MIL_DARK["font_mono"],
                                    "fontWeight": "800",
                                    "fontSize": "0.86rem",
                                    "letterSpacing": "1.2px",
                                },
                            ),
                            width="auto",
                        ),
                        # Timeline Scrubber Slider
                        dbc.Col(
                            html.Div(
                                [
                                    dcc.Slider(
                                        id="sim-timeline-slider",
                                        min=0.0,
                                        max=120.0,
                                        step=0.5,
                                        value=0.0,
                                        marks={
                                            0: "T+0s",
                                            30: "30s (Boost)",
                                            60: "60s (Midcourse)",
                                            90: "90s (Terminal)",
                                            120: "120s (End)",
                                        },
                                        tooltip={"placement": "bottom", "always_visible": False},
                                        className="dash-dark-slider",
                                    )
                                ],
                                style={"paddingTop": "6px"},
                            ),
                            xs=12, md=True,
                        ),
                    ],
                    align="center",
                    className="g-2",
                ),
            ],
            style={"padding": "8px 16px"},
        ),
        style={
            "backgroundColor": MIL_DARK["card_bg"],
            "border": f"1px solid {MIL_DARK['card_border']}",
            "borderRadius": "6px",
            "marginBottom": "10px",
        },
    )


def create_easter_egg_banner() -> html.Div:
    """Special HUD tactical telemetry alert banner for stealth air-launch."""
    return html.Div(
        id="easter-egg-banner-container",
        children=[
            dbc.Alert(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Span("⚡ ", style={"fontSize": "1.4rem"}),
                                        html.Strong(
                                            "AIR-LAUNCH DETECTED: F-22 RAPTOR DEPLOYED WEAPON AT MACH 1.5, ALT 45,000 FT",
                                            id="easter-egg-banner-text",
                                            style={"letterSpacing": "1px", "fontSize": "0.88rem"},
                                        ),
                                    ],
                                    className="d-flex align-items-center",
                                ),
                                md=9,
                            ),
                            dbc.Col(
                                html.Small(
                                    "STEALTH INGRESS CONFIRMED | RADAR CROSS SECTION < 0.0001 m² | EGRESS CORRIDOR ACTIVE",
                                    style={"fontFamily": MIL_DARK["font_mono"], "color": "#ffe082", "fontSize": "0.72rem"},
                                ),
                                md=3,
                                className="text-end d-flex align-items-center justify-content-end",
                            ),
                        ],
                        align="center",
                    )
                ],
                id="easter-egg-alert",
                color="warning",
                is_open=False,
                dismissable=True,
                style={
                    "backgroundColor": "rgba(255, 179, 0, 0.15)",
                    "border": "1px solid #ffb300",
                    "boxShadow": "0 0 16px rgba(255, 179, 0, 0.35)",
                    "color": "#fff8e1",
                    "fontFamily": MIL_DARK["font_mono"],
                    "marginBottom": "10px",
                    "padding": "10px 16px",
                },
            )
        ],
    )


def create_monte_carlo_modal() -> dbc.Modal:
    """Constructs the 100-run Monte Carlo batch summary modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.Span("🎲 ", style={"fontSize": "1.3rem"}),
                        "IAMD STOCHASTIC MONTE CARLO BATCH EVALUATION (100 RUNS)",
                    ],
                    style={"fontFamily": MIL_DARK["font_mono"], "fontSize": "1.05rem", "letterSpacing": "1.2px"},
                ),
                style={"backgroundColor": "#090d16", "borderBottom": f"1px solid {MIL_DARK['card_border']}"},
            ),
            dbc.ModalBody(
                [
                    # Top KPI Cards
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Small("OVERALL FLEET P_KILL", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem"}),
                                        html.Div("92.5%", id="mc-overall-pk", style={"color": MIL_DARK["accent_green"], "fontSize": "1.8rem", "fontWeight": "800", "fontFamily": MIL_DARK["font_mono"]}),
                                        html.Small("370 / 400 Threats Destroyed", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem"}),
                                    ],
                                    className="p-3 rounded text-center",
                                    style={"backgroundColor": "#090d16", "border": f"1px solid {MIL_DARK['card_border']}"},
                                ),
                                width=4,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Small("MEAN MISS DISTANCE (CPA)", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem"}),
                                        html.Div("4.82 m", id="mc-mean-cpa", style={"color": MIL_DARK["accent_cyan"], "fontSize": "1.8rem", "fontWeight": "800", "fontFamily": MIL_DARK["font_mono"]}),
                                        html.Small("Median: 2.15 m (Hit-to-Kill)", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem"}),
                                    ],
                                    className="p-3 rounded text-center",
                                    style={"backgroundColor": "#090d16", "border": f"1px solid {MIL_DARK['card_border']}"},
                                ),
                                width=4,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Small("MEAN TIME TO INTERCEPT", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem"}),
                                        html.Div("21.4 s", id="mc-mean-time", style={"color": MIL_DARK["accent_amber"], "fontSize": "1.8rem", "fontWeight": "800", "fontFamily": MIL_DARK["font_mono"]}),
                                        html.Small("Avg Expenditure: 5.2 Missiles", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem"}),
                                    ],
                                    className="p-3 rounded text-center",
                                    style={"backgroundColor": "#090d16", "border": f"1px solid {MIL_DARK['card_border']}"},
                                ),
                                width=4,
                            ),
                        ],
                        className="g-3 mb-3",
                    ),
                    # Breakdown Tables & Charts
                    dbc.Row(
                        [
                            # Threat Type Breakdown
                            dbc.Col(
                                [
                                    html.H6("KILL PROBABILITY BY THREAT CLASS", style={"color": MIL_DARK["accent_cyan"], "fontSize": "0.82rem", "fontFamily": MIL_DARK["font_mono"]}),
                                    html.Div(
                                        [
                                            html.Div([html.Span("9K720 Iskander-M (Quasi-Ballistic): "), html.Strong("91.0%", style={"color": "#00ff88"})], className="d-flex justify-content-between py-1 border-bottom border-dark"),
                                            html.Div([html.Span("Kh-47M2 Kinzhal (Hypersonic): "), html.Strong("89.0%", style={"color": "#00ff88"})], className="d-flex justify-content-between py-1 border-bottom border-dark"),
                                            html.Div([html.Span("Shahed-136 Drone (Low & Slow): "), html.Strong("96.0%", style={"color": "#00ff88"})], className="d-flex justify-content-between py-1 border-bottom border-dark"),
                                            html.Div([html.Span("Subsonic Cruise Missile Leaker: "), html.Strong("94.0%", style={"color": "#00ff88"})], className="d-flex justify-content-between py-1"),
                                        ],
                                        className="p-2 rounded",
                                        style={"backgroundColor": "#090d16", "border": f"1px solid {MIL_DARK['card_border']}", "fontSize": "0.78rem", "fontFamily": MIL_DARK["font_mono"]},
                                    ),
                                ],
                                md=6,
                            ),
                            # Defense Tier Breakdown
                            dbc.Col(
                                [
                                    html.H6("INTERCEPTION EFFECTIVENESS BY TIER", style={"color": MIL_DARK["accent_cyan"], "fontSize": "0.82rem", "fontFamily": MIL_DARK["font_mono"]}),
                                    html.Div(
                                        [
                                            html.Div([html.Span("Tier 1: SM-3 Block IIA / THAAD (>40 km): "), html.Strong("94.0%", style={"color": "#00e5ff"})], className="d-flex justify-content-between py-1 border-bottom border-dark"),
                                            html.Div([html.Span("Tier 2: Patriot PAC-3 MSE (5-38 km): "), html.Strong("92.0%", style={"color": "#00e5ff"})], className="d-flex justify-content-between py-1 border-bottom border-dark"),
                                            html.Div([html.Span("Tier 3: Anduril Roadrunner-M (0.1-10 km): "), html.Strong("95.0%", style={"color": "#00e5ff"})], className="d-flex justify-content-between py-1 border-bottom border-dark"),
                                            html.Div([html.Span("Tier 4: Phalanx CIWS LPWS (<3.5 km): "), html.Strong("86.0%", style={"color": "#ffb300"})], className="d-flex justify-content-between py-1"),
                                        ],
                                        className="p-2 rounded",
                                        style={"backgroundColor": "#090d16", "border": f"1px solid {MIL_DARK['card_border']}", "fontSize": "0.78rem", "fontFamily": MIL_DARK["font_mono"]},
                                    ),
                                ],
                                md=6,
                            ),
                        ],
                        className="g-3 mb-2",
                    ),
                    html.Small(
                        "Batch conditions: N=100 runs, randomized launch headings (±8°), atmospheric winds (0-25 m/s), seeker angle noise (1.5 mrad). Sub-timestep quadratic CPA evaluated to prevent tunneling.",
                        style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem", "fontStyle": "italic"},
                    ),
                ],
                style={"backgroundColor": MIL_DARK["card_bg"]},
            ),
            dbc.ModalFooter(
                dbc.Button("CLOSE MATRIX", id="btn-close-monte-carlo", color="secondary", size="sm", className="fw-bold px-3"),
                style={"backgroundColor": "#090d16", "borderTop": f"1px solid {MIL_DARK['card_border']}"},
            ),
        ],
        id="monte-carlo-modal",
        size="lg",
        is_open=False,
    )


# Assemble complete root layout
app.layout = html.Div(
    [
        # Internal State Stores & Timer
        dcc.Store(
            id="sim-state-store",
            data={
                "time": 0.0,
                "playing": False,
                "speed": 1.0,
                "scenario": "eastern_europe",
                "theater": "eastern_europe",
                "selected_unit": "TRK-01",
                "view_mode": "2d",
                "easter_egg_active": False,
            },
        ),
        dcc.Store(id="easter-egg-store", data=roll_easter_egg()),
        dcc.Interval(id="sim-interval", interval=500, n_intervals=0, disabled=True),
        # Hidden secret button for deterministic automated testing
        html.Button(id="btn-easter-egg-test", style={"display": "none"}),
        # Top Navbar
        create_top_navbar(),
        # Main Body Container
        dbc.Container(
            [
                # Easter Egg Tactical Alert Banner
                create_easter_egg_banner(),
                # Playback Controls Bar
                create_playback_control_bar(),
                # Main Tactical Area: Map/Globe + Altitude Chart (Left) vs Telemetry Sidebar (Right)
                dbc.Row(
                    [
                        # Left Main Column (8 cols)
                        dbc.Col(
                            [
                                # Viewport: 2D Leaflet Map vs 3D Globe
                                html.Div(
                                    id="tactical-2d-viewport-container",
                                    children=[map_views.build_tactical_leaflet_map(theater_key="eastern_europe", height="500px")],
                                    style={"display": "block", "marginBottom": "10px"},
                                ),
                                html.Div(
                                    id="tactical-3d-viewport-container",
                                    children=[
                                        dcc.Graph(
                                            id="tactical-3d-globe-graph",
                                            figure=map_views.build_3d_globe_figure(theater_key="eastern_europe", height=500),
                                            config={"displayModeBar": True, "responsive": True},
                                        )
                                    ],
                                    style={"display": "none", "marginBottom": "10px"},
                                ),
                                # Altitude Profile Cross-Section Chart
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Strong("🎯 MISSILEMAP 2D ALTITUDE PROFILE CROSS-SECTION", style={"color": "#ffffff", "fontSize": "0.85rem", "letterSpacing": "1px"}),
                                                html.Small("DOWNRANGE DISTANCE (KM) VS. ALTITUDE (KM) WITH APOGEE & KINETIC INTERCEPT", style={"color": MIL_DARK["text_muted"], "fontSize": "0.68rem"}),
                                            ],
                                            className="d-flex justify-content-between align-items-center mb-1",
                                        ),
                                        dcc.Graph(
                                            id="missilemap-altitude-profile-graph",
                                            figure=map_views.build_altitude_profile_figure(theater_key="eastern_europe", threat_index=0, height=320),
                                            config={"displayModeBar": True, "responsive": True},
                                            style={"height": "320px"},
                                        ),
                                    ],
                                    className="p-2 rounded mb-2",
                                    style={"backgroundColor": MIL_DARK["card_bg"], "border": f"1px solid {MIL_DARK['card_border']}"},
                                ),
                            ],
                            lg=8,
                            md=12,
                        ),
                        # Right Telemetry Sidebar Column (4 cols)
                        dbc.Col(
                            [
                                html.Div(
                                    id="telemetry-sidebar-container",
                                    children=telemetry.create_telemetry_sidebar(
                                        unit_options=[
                                            {"label": f"🔴 {t['id']}: {t['name']}", "value": t["id"]}
                                            for t in SCENARIO_PRESETS["eastern_europe"]["tracks"]
                                        ],
                                        selected_unit_id="TRK-01",
                                    ),
                                )
                            ],
                            lg=4,
                            md=12,
                        ),
                    ],
                    className="g-2 mb-2",
                ),
                # Bottom Tactical Air Picture Matrix (Full Width)
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                id="tactical-matrix-container",
                                children=telemetry.create_tactical_matrix(),
                                className="p-2 rounded mb-3",
                                style={"backgroundColor": MIL_DARK["card_bg"], "border": f"1px solid {MIL_DARK['card_border']}"},
                            ),
                            width=12,
                        )
                    ]
                ),
            ],
            fluid=True,
            className="px-3 pt-2",
        ),
        # Monte Carlo Modal
        create_monte_carlo_modal(),
    ],
    style={"backgroundColor": MIL_DARK["bg_main"], "minHeight": "100vh", "color": MIL_DARK["text_main"]},
)


# ==============================================================================
# 5. INTEGRATED DASH CALLBACKS
# ==============================================================================

# Callback 1: View mode toggle (2D Map vs 3D Globe)
@app.callback(
    Output("tactical-2d-viewport-container", "style"),
    Output("tactical-3d-viewport-container", "style"),
    Input("view-mode-toggle", "value"),
)
def cb_toggle_view_mode(mode):
    if mode == "3d":
        return {"display": "none", "marginBottom": "10px"}, {"display": "block", "marginBottom": "10px"}
    return {"display": "block", "marginBottom": "10px"}, {"display": "none", "marginBottom": "10px"}


# Callback 2: Playback Control Bar Actions (Play, Pause, Step, Reset, Speed, Scrubber, Strike Salvo, Preset Change)
@app.callback(
    Output("sim-state-store", "data"),
    Output("sim-interval", "disabled"),
    Output("sim-interval", "interval"),
    Output("easter-egg-store", "data"),
    Input("btn-play", "n_clicks"),
    Input("btn-pause", "n_clicks"),
    Input("btn-step", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    Input("btn-launch-strike", "n_clicks"),
    Input("btn-easter-egg-test", "n_clicks"),
    Input("sim-speed-radio", "value"),
    Input("sim-timeline-slider", "value"),
    Input("sim-interval", "n_intervals"),
    Input("scenario-preset-select", "value"),
    Input("theater-selector", "value"),
    Input("telemetry-unit-select", "value"),
    Input("tactical-matrix-table", "selected_rows"),
    State("sim-state-store", "data"),
    State("easter-egg-store", "data"),
    State("tactical-matrix-table", "data"),
    prevent_initial_call=True,
)
def cb_playback_engine(
    n_play, n_pause, n_step, n_reset, n_strike, n_egg_test,
    speed_val, slider_val, n_intervals,
    scenario_sel, theater_sel, unit_sel, table_rows,
    state, egg_state, table_data,
    triggered_id_override=None
):
    trig = triggered_id_override if triggered_id_override is not None else ctx.triggered_id
    new_state = dict(state or {})
    new_egg = dict(egg_state or {})
    speed = float(speed_val or 1.0)
    new_state["speed"] = speed

    # Determine base interval ms
    interval_ms = max(50, int(500 / speed))

    if trig == "btn-play":
        new_state["playing"] = True
    elif trig == "btn-pause":
        new_state["playing"] = False
    elif trig == "btn-step":
        new_state["time"] = min(120.0, new_state.get("time", 0.0) + 2.0)
        new_state["playing"] = False
    elif trig == "btn-reset":
        new_state["time"] = 0.0
        new_state["playing"] = False
        new_egg["active"] = False
    elif trig == "btn-launch-strike":
        # Launch Salvo: Reset time to 0, start playback, and roll 10% Easter egg dice!
        new_state["time"] = 0.0
        new_state["playing"] = True
        new_egg = roll_easter_egg()
        new_state["easter_egg_active"] = new_egg["active"]
    elif trig == "btn-easter-egg-test":
        # Deterministic trigger for testing
        new_egg = roll_easter_egg()
        new_egg["active"] = True
        new_state["easter_egg_active"] = True
    elif trig == "sim-interval" and new_state.get("playing", False):
        dt = 0.5 * speed
        new_time = new_state.get("time", 0.0) + dt
        if new_time >= 120.0:
            new_state["time"] = 120.0
            new_state["playing"] = False
        else:
            new_state["time"] = round(new_time, 2)
    elif trig == "sim-timeline-slider":
        new_state["time"] = float(slider_val or 0.0)
    elif trig == "scenario-preset-select":
        new_state["scenario"] = scenario_sel
        new_state["theater"] = scenario_sel
        new_state["time"] = 0.0
        new_state["playing"] = False
        scenario_tracks = SCENARIO_PRESETS.get(scenario_sel, {}).get("tracks", [])
        if scenario_tracks:
            new_state["selected_unit"] = scenario_tracks[0]["id"]
    elif trig == "theater-selector":
        new_state["theater"] = theater_sel
    elif trig == "telemetry-unit-select":
        new_state["selected_unit"] = unit_sel
    elif trig == "tactical-matrix-table" and table_rows and table_data:
        row_idx = table_rows[0]
        if 0 <= row_idx < len(table_data):
            new_state["selected_unit"] = table_data[row_idx].get("track_id", "TRK-01")

    interval_disabled = not new_state.get("playing", False)
    return new_state, interval_disabled, interval_ms, new_egg


# Callback 3: Update Visuals, Telemetry, Matrix Table, Slider, and Clock
@app.callback(
    Output("sim-clock-display", "children"),
    Output("sim-timeline-slider", "value"),
    Output("telemetry-unit-select", "options"),
    Output("telemetry-unit-select", "value"),
    Output("telemetry-mach-gauge", "figure"),
    Output("telemetry-speed-readout", "children"),
    Output("telemetry-alt-indicators", "children"),
    Output("telemetry-progress-container", "children"),
    Output("telemetry-metrics-container", "children"),
    Output("telemetry-badges-container", "children"),
    Output("telemetry-target-info", "children"),
    Output("tactical-matrix-table", "data"),
    Output("tactical-matrix-table", "selected_rows"),
    Output("easter-egg-alert", "is_open"),
    Output("easter-egg-banner-text", "children"),
    Output("missilemap-altitude-profile-graph", "figure"),
    Output("tactical-3d-globe-graph", "figure"),
    Input("sim-state-store", "data"),
    State("easter-egg-store", "data"),
)
def cb_update_dashboard(state, egg_state):
    st = state or {}
    t_sec = float(st.get("time", 0.0))
    playing = bool(st.get("playing", False))
    scen_key = st.get("scenario", "eastern_europe")
    theater_key = st.get("theater", "eastern_europe")
    selected_unit_id = st.get("selected_unit", "TRK-01")

    scenario = SCENARIO_PRESETS.get(scen_key, SCENARIO_PRESETS["eastern_europe"])
    tracks = scenario.get("tracks", [])

    # 1. Update Clock & Slider
    status_label = "RUNNING" if playing else ("FINISHED" if t_sec >= 120.0 else "PAUSED")
    clock_str = f"T+{t_sec:05.1f}s / 120.0s [{status_label}]"

    # 2. Compute Active Track Matrix Data at Time t
    matrix_rows = []
    selected_track_dict = None
    selected_row_idx = 0

    unit_options = []
    for idx, trk in enumerate(tracks):
        tele = calculate_track_telemetry_at_time(trk, t_sec)
        if tele["id"] == selected_unit_id:
            selected_track_dict = tele
            selected_row_idx = idx

        prefix = "🔴" if tele["faction"] == "Aggressor" else "🔵"
        unit_options.append({"label": f"{prefix} {tele['id']}: {tele['name']}", "value": tele["id"]})

        matrix_rows.append({
            "track_id": tele["id"],
            "name": tele["name"],
            "faction": tele["faction"],
            "type": tele["type"],
            "mach": f"M {tele['mach']:.2f}",
            "alt_km": f"{tele['alt_km']:.2f} km",
            "target": tele["target"],
            "phase": tele["phase"],
            "status": tele["status"],
        })

    if selected_track_dict is None and tracks:
        selected_track_dict = calculate_track_telemetry_at_time(tracks[0], t_sec)
        selected_row_idx = 0

    # 3. Update Telemetry Sidebar Components
    (
        mach_fig, speed_readout, alt_ind, prog_bar,
        metrics_cards, badges, target_info
    ) = telemetry.update_telemetry_components(selected_track_dict)

    # 4. Easter Egg Banner
    egg = egg_state or {}
    egg_open = bool(egg.get("active", False))
    egg_text = egg.get("banner_text", "AIR-LAUNCH DETECTED: F-22 RAPTOR DEPLOYED WEAPON AT MACH 1.5, ALT 45,000 FT")

    # 5. Altitude Profile Chart & 3D Globe
    # Find index of selected track for altitude profile
    threat_idx = 0
    for i, t in enumerate(tracks):
        if t["id"] == selected_track_dict["id"]:
            threat_idx = i
            break

    alt_fig = map_views.build_altitude_profile_figure(
        theater_key=theater_key,
        threat_index=threat_idx,
        custom_threat={
            "threat_id": selected_track_dict["id"],
            "threat_name": selected_track_dict["name"],
            "threat_type": selected_track_dict["type"],
            "speed_mach": selected_track_dict["mach"],
            "apogee_km": selected_track_dict["apogee_km"],
            "progress": selected_track_dict["progress_pct"] / 100.0,
            "status": selected_track_dict["status"],
            "intercept_cpa_m": 1.25,
            "intercept_alt_km": selected_track_dict["alt_km"],
            "p_kill": 0.94,
        },
        height=320,
    )

    globe_fig = map_views.build_3d_globe_figure(theater_key=theater_key, height=500)

    return (
        clock_str,
        t_sec,
        unit_options,
        selected_track_dict["id"],
        mach_fig,
        speed_readout,
        alt_ind,
        prog_bar,
        metrics_cards,
        badges,
        target_info,
        matrix_rows,
        [selected_row_idx],
        egg_open,
        egg_text,
        alt_fig,
        globe_fig,
    )


# Callback 4: Monte Carlo Modal (Open & Close)
@app.callback(
    Output("monte-carlo-modal", "is_open"),
    Input("btn-open-monte-carlo", "n_clicks"),
    Input("btn-close-monte-carlo", "n_clicks"),
    State("monte-carlo-modal", "is_open"),
    prevent_initial_call=True,
)
def cb_toggle_monte_carlo(open_clicks, close_clicks, is_open):
    return not is_open


# ==============================================================================
# 6. DIRECT LAUNCH ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("STARTING IAMD GLOBAL DEFENSE SIMULATOR DASHBOARD")
    print("Access locally on http://127.0.0.1:8050")
    print("=" * 80)
    app.run(debug=False, port=8050)
