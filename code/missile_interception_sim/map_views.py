#!/usr/bin/env python3
"""
================================================================================
TACTICAL MAP PRESENTATION & ADVANCED CHART COMPONENTS (MAP_VIEWS.PY)
Multi-Theater Integrated Air and Missile Defense (IAMD) Command & Control
================================================================================

Components included:
1. 2D Tactical Map using `dash-leaflet`:
   - Dark military-style basemap tiles (CartoDB Dark Matter / Esri Dark Canvas)
   - Draggable markers for Attacker Launch Sites, Defender Batteries, and Target HVAs
   - Radar Weapon Engagement Zone (WEZ) circles around defender batteries
   - Dynamic Polylines / Geodesic arcs for active ballistic missiles, hypersonic glide vehicles,
     cruise missiles, and autonomous drone swarm trajectories
   - Animated / real-time threat tracking markers with velocity, altitude, and ETA readouts
   - Detonation burst markers (gold stars / red explosions) at kinetic intercept and impact locations
   - Theater quick-jump support:
     * Eastern Europe / Black Sea
     * Persian Gulf / Red Sea
     * Taiwan Strait / Indo-Pacific
     * CONUS Homeland
2. Altitude Profile Chart (Missilemap style):
   - Plotly 2D chart (`dcc.Graph`) with Downrange Distance (km) vs. Altitude (km)
   - Multi-phase threat flight curve (Boost, Midcourse, Terminal)
   - Apogee marker with exact ballistic readouts
   - Interceptor climb curve and lead-collision vector
   - Kinetic intercept point with CPA miss distance, altitude, and P_kill annotations
   - Stratified atmospheric zones (Troposphere, Stratosphere, Mesosphere, Karman Line)
3. 3D Digital Globe Mode:
   - Plotly 3D scatter (`go.Scatter3d`) rendering spherical Earth with continents and grid
   - 3D suborbital parabolic arcs rising off the planetary surface
   - 3D radar engagement domes over defender batteries
   - 3D kinetic intercept detonation bursts and interceptor climb vectors
   - Dynamic theater-centric camera orientation
4. Dash Component Containers & Callback Integrations:
   - Unified multi-view container with 2D/3D mode toggling
   - Theater quick-jump selectors and layer filtering
   - Callback hooks for interactive dragging, theater switching, and threat inspection
================================================================================
"""

import math
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State, ALL
import dash_leaflet as dl


# ==============================================================================
# 1. TACTICAL TILE LAYERS & STYLING CONSTANTS
# ==============================================================================

TILE_CARTO_DARK_MATTER = {
    "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    "subdomains": ["a", "b", "c", "d"],
    "maxZoom": 19
}

TILE_OPENSTREETMAP = {
    "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    "subdomains": ["a", "b", "c"],
    "maxZoom": 19
}

TILE_OPENTOPOMAP = {
    "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    "attribution": 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
    "subdomains": ["a", "b", "c"],
    "maxZoom": 17
}

# Alias ensuring 100% open-source zero-API-key fallback
TILE_ESRI_DARK_CANVAS = TILE_CARTO_DARK_MATTER

EARTH_RADIUS_KM = 6371.0


# ==============================================================================
# 2. HIGH-TECH VECTOR SVG ICONS FOR LEAFLET
# ==============================================================================

def _encode_svg_uri(svg_string: str) -> str:
    """Encode SVG string into a standard data URI."""
    clean = " ".join(svg_string.strip().split())
    return f"data:image/svg+xml;utf8,{urllib.parse.quote(clean)}"


# Attacker Launch Site Icon: Red crosshair reticle with missile silo silhouette
_SVG_ATTACKER_LAUNCH = """
<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34">
  <defs>
    <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#ff1a35" flood-opacity="0.9"/>
    </filter>
  </defs>
  <circle cx="17" cy="17" r="14" fill="#180709" stroke="#ff2244" stroke-width="2.5" filter="url(#glow-red)"/>
  <circle cx="17" cy="17" r="8" fill="#ff2244" opacity="0.25"/>
  <line x1="17" y1="2" x2="17" y2="32" stroke="#ff4455" stroke-width="1.8" stroke-dasharray="3,2"/>
  <line x1="2" y1="17" x2="32" y2="17" stroke="#ff4455" stroke-width="1.8" stroke-dasharray="3,2"/>
  <polygon points="17,7 22,23 17,20 12,23" fill="#ffffff"/>
  <circle cx="17" cy="17" r="2" fill="#ff2244"/>
</svg>
"""
ATTACKER_LAUNCH_ICON_URI = _encode_svg_uri(_SVG_ATTACKER_LAUNCH)

# Defender Battery Icon: Emerald green radar shield with emission arcs
_SVG_DEFENDER_BATTERY = """
<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34">
  <defs>
    <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#00ff88" flood-opacity="0.9"/>
    </filter>
  </defs>
  <path d="M17 3 L30 8 V18 C30 25.5 17 31 17 31 C17 31 4 25.5 4 18 V8 Z" 
        fill="#041810" stroke="#00ff88" stroke-width="2.4" filter="url(#glow-green)"/>
  <circle cx="17" cy="17" r="4.5" fill="#00ff88"/>
  <path d="M12 12 A7 7 0 0 1 22 12" fill="none" stroke="#00ff88" stroke-width="1.8"/>
  <path d="M9 9 A11 11 0 0 1 25 9" fill="none" stroke="#00ff88" stroke-width="1.4" opacity="0.75"/>
</svg>
"""
DEFENDER_BATTERY_ICON_URI = _encode_svg_uri(_SVG_DEFENDER_BATTERY)

# Defended Target Asset (HVA) Icon: Amber / Gold diamond fortress with targeting star
_SVG_TARGET_ASSET = """
<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34">
  <defs>
    <filter id="glow-gold" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#ffb700" flood-opacity="0.9"/>
    </filter>
  </defs>
  <polygon points="17,2 32,17 17,32 2,17" 
           fill="#1e1503" stroke="#ffb700" stroke-width="2.5" filter="url(#glow-gold)"/>
  <polygon points="17,7 27,17 17,27 7,17" fill="#ffb700" opacity="0.3"/>
  <circle cx="17" cy="17" r="4" fill="#ffd700"/>
  <polygon points="17,10 18.5,14.5 23,15 19.5,18 20.5,22.5 17,20 13.5,22.5 14.5,18 11,15 15.5,14.5" fill="#ffffff"/>
</svg>
"""
TARGET_ASSET_ICON_URI = _encode_svg_uri(_SVG_TARGET_ASSET)

# Threat Real-Time Position Icon: Pulsing target vector chevron
_SVG_THREAT_POSITION = """
<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 26 26">
  <defs>
    <filter id="glow-pink" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="#ff0055" flood-opacity="1"/>
    </filter>
  </defs>
  <circle cx="13" cy="13" r="10" fill="#ff0055" opacity="0.25"/>
  <circle cx="13" cy="13" r="6" fill="#ff0055" stroke="#ffffff" stroke-width="1.8" filter="url(#glow-pink)"/>
  <circle cx="13" cy="13" r="2.5" fill="#ffffff"/>
</svg>
"""
THREAT_POSITION_ICON_URI = _encode_svg_uri(_SVG_THREAT_POSITION)

# Kinetic Intercept Detonation Burst Icon: 12-point radiant starburst
_SVG_DETONATION_BURST = """
<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
  <defs>
    <filter id="glow-burst" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#ffea00" flood-opacity="1"/>
    </filter>
  </defs>
  <polygon points="20,1 24,13 36,9 29,19 39,26 26,27 23,39 17,28 5,31 11,20 1,14 14,13" 
           fill="#ffee00" stroke="#ff3300" stroke-width="2.2" filter="url(#glow-burst)"/>
  <circle cx="20" cy="20" r="7.5" fill="#ff3300"/>
  <circle cx="20" cy="20" r="3.5" fill="#ffffff"/>
</svg>
"""
DETONATION_BURST_ICON_URI = _encode_svg_uri(_SVG_DETONATION_BURST)

# Leaker Impact Burst Icon: Red crater explosion
_SVG_LEAKER_IMPACT = """
<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <polygon points="19,2 23,13 35,10 27,20 37,28 25,27 21,37 16,27 4,30 10,19 1,13 13,13" 
           fill="#ff1a1a" stroke="#ffffff" stroke-width="2"/>
  <circle cx="19" cy="19" r="6" fill="#990000"/>
  <circle cx="19" cy="19" r="2" fill="#ffffff"/>
</svg>
"""
LEAKER_IMPACT_ICON_URI = _encode_svg_uri(_SVG_LEAKER_IMPACT)


# ==============================================================================
# 3. GEODESIC & SPATIAL KINEMATIC UTILITIES
# ==============================================================================

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def great_circle_intermediate_point(lat1: float, lon1: float, lat2: float, lon2: float, f: float) -> Tuple[float, float]:
    """Calculate intermediate point along great-circle track at fractional distance f in [0, 1]."""
    if f <= 0.0:
        return lat1, lon1
    if f >= 1.0:
        return lat2, lon2

    r_lat1 = math.radians(lat1)
    r_lon1 = math.radians(lon1)
    r_lat2 = math.radians(lat2)
    r_lon2 = math.radians(lon2)

    d = 2.0 * math.asin(math.sqrt(
        math.sin((r_lat2 - r_lat1) / 2.0) ** 2 +
        math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1) / 2.0) ** 2
    ))

    if d < 1e-7:
        return lat1, lon1

    a = math.sin((1.0 - f) * d) / math.sin(d)
    b = math.sin(f * d) / math.sin(d)

    x = a * math.cos(r_lat1) * math.cos(r_lon1) + b * math.cos(r_lat2) * math.cos(r_lon2)
    y = a * math.cos(r_lat1) * math.sin(r_lon1) + b * math.cos(r_lat2) * math.sin(r_lon2)
    z = a * math.sin(r_lat1) + b * math.sin(r_lat2)

    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))
    return lat, lon


def lat_lon_to_cartesian(lat: float, lon: float, alt_km: float = 0.0, radius: float = EARTH_RADIUS_KM) -> Tuple[float, float, float]:
    """Transform geographic (lat, lon, alt_km) coordinates to 3D Cartesian (x, y, z) coordinates."""
    r_eff = radius + alt_km
    phi = math.radians(lat)
    lam = math.radians(lon)
    x = r_eff * math.cos(phi) * math.cos(lam)
    y = r_eff * math.cos(phi) * math.sin(lam)
    z = r_eff * math.sin(phi)
    return x, y, z


def generate_trajectory_waypoints(
    lat1: float, lon1: float, lat2: float, lon2: float,
    threat_type: str = "ballistic",
    apogee_km: float = 120.0,
    n_points: int = 50
) -> List[Dict[str, float]]:
    """
    Generate realistic 3D waypoints (lat, lon, alt_km, downrange_km) along flight trajectory.
    Incorporates distinct kinematic signatures for:
    - ballistic: parabolic suborbital arc
    - hypersonic: atmospheric pull-up and skip-glide with sinusoidal lateral weave
    - cruise: low-altitude terrain hugging with evasive doglegs
    - drone: low-speed meandering swarm path
    """
    total_range_km = haversine_distance_km(lat1, lon1, lat2, lon2)
    waypoints: List[Dict[str, float]] = []

    for i in range(n_points):
        u = i / float(n_points - 1)
        base_lat, base_lon = great_circle_intermediate_point(lat1, lon1, lat2, lon2, u)
        downrange_km = u * total_range_km

        if threat_type.lower() in ["ballistic", "quasi-ballistic", "srbm", "mrbm", "icbm"]:
            alt_km = 4.0 * apogee_km * u * (1.0 - u)
            lat, lon = base_lat, base_lon
        elif threat_type.lower() in ["hypersonic", "hypersonic glide", "hgv"]:
            # Pull-up into skip-glide layer ~35 km with cross-track weave
            if u < 0.15:
                alt_km = 35.0 * math.sin((u / 0.15) * (math.pi / 2.0))
            elif u > 0.85:
                alt_km = 35.0 * math.cos(((u - 0.85) / 0.15) * (math.pi / 2.0))
            else:
                alt_km = 35.0 + 3.0 * math.sin(6.0 * math.pi * u)
            # Lateral weave offset
            cross_deg = 0.35 * math.sin(4.0 * math.pi * u)
            lat = base_lat + cross_deg * 0.7
            lon = base_lon + cross_deg * 0.7
        elif threat_type.lower() in ["cruise", "supersonic cruise", "ashm"]:
            # Low altitude 0.5 - 1.5 km with waypoint dogleg
            alt_km = 0.8 + 0.4 * math.sin(3.0 * math.pi * u)
            cross_deg = 0.20 * math.sin(2.0 * math.pi * u)
            lat = base_lat + cross_deg
            lon = base_lon - cross_deg * 0.5
        elif threat_type.lower() in ["drone", "drone swarm", "loitering"]:
            # Very low altitude 0.2 - 0.5 km with wandering loitering path
            alt_km = 0.35 + 0.15 * math.sin(5.0 * math.pi * u)
            cross_deg = 0.15 * math.sin(6.0 * math.pi * u)
            lat = base_lat + cross_deg
            lon = base_lon + cross_deg * 0.8
        else:
            alt_km = 4.0 * apogee_km * u * (1.0 - u)
            lat, lon = base_lat, base_lon

        waypoints.append({
            "lat": lat,
            "lon": lon,
            "alt_km": max(0.0, alt_km),
            "downrange_km": downrange_km,
            "fraction": u
        })

    return waypoints


def generate_interceptor_trajectory(
    battery_lat: float, battery_lon: float,
    intercept_lat: float, intercept_lon: float,
    intercept_alt_km: float,
    n_points: int = 30
) -> List[Dict[str, float]]:
    """Generate interceptor flyout curve from defender battery to predicted kinetic intercept point."""
    interceptor_points: List[Dict[str, float]] = []
    total_dist_km = haversine_distance_km(battery_lat, battery_lon, intercept_lat, intercept_lon)

    for i in range(n_points):
        u = i / float(n_points - 1)
        base_lat, base_lon = great_circle_intermediate_point(battery_lat, battery_lon, intercept_lat, intercept_lon, u)
        # Interceptor climbs rapidly with high acceleration curve
        alt_km = intercept_alt_km * (math.sin(u * math.pi / 2.0) ** 1.3)
        downrange_km = u * total_dist_km
        interceptor_points.append({
            "lat": base_lat,
            "lon": base_lon,
            "alt_km": alt_km,
            "downrange_km": downrange_km,
            "fraction": u
        })
    return interceptor_points


# ==============================================================================
# 4. THEATER PRESETS & OPERATIONAL DATA
# ==============================================================================

THEATER_PRESETS: Dict[str, Dict[str, Any]] = {
    "eastern_europe": {
        "slug": "eastern_europe",
        "name": "Eastern Europe / Black Sea",
        "center": [47.5, 33.5],
        "zoom": 6,
        "description": "High-intensity multi-axis theater featuring Iskander-M ballistic missiles, Kalibr cruise missiles, Kinzhal aero-ballistic hypersonic threats, and dense Shahed drone swarms engaged by Patriot PAC-3 CRI and NASAMS air defense systems.",
        "attacker_launch_sites": [
            {
                "id": "launch-rostov",
                "name": "Rostov Tactical Missile Complex",
                "lat": 47.24,
                "lon": 39.71,
                "faction": "Aggressor Strike Force",
                "systems": ["9M723 Iskander-M (SRBM)", "9M728 Cruise Missile"],
                "status": "Active / Launch Sequence Initialized"
            },
            {
                "id": "launch-sevastopol",
                "name": "Sevastopol Naval Coastal Complex",
                "lat": 44.62,
                "lon": 33.53,
                "faction": "Aggressor Naval Strike Command",
                "systems": ["3M54 Kalibr Land-Attack Cruise", "P-800 Oniks"],
                "status": "Active / Submerged & Shore Launchers Ready"
            },
            {
                "id": "launch-voronezh",
                "name": "Voronezh Aero-Ballistic Launch Corridor",
                "lat": 51.67,
                "lon": 39.21,
                "faction": "Aggressor Long-Range Aviation",
                "systems": ["Kh-47M2 Kinzhal (Aero-Ballistic Hypersonic)"],
                "status": "Active / MiG-31K Sortie Inbound"
            },
            {
                "id": "launch-gomel",
                "name": "Gomel Loitering Munitions Hub",
                "lat": 52.43,
                "lon": 30.98,
                "faction": "Aggressor Unmanned Aviation Brigade",
                "systems": ["Geran-2 (Shahed-136 Swarm)", "Lancet-3"],
                "status": "Active / Swarm Launch in Progress"
            }
        ],
        "defender_batteries": [
            {
                "id": "bat-kyiv-patriot",
                "name": "Patriot PAC-3 CRI Battery Bravo (Kyiv Capital Defense)",
                "lat": 50.45,
                "lon": 30.52,
                "system": "MIM-104 Patriot (PAC-3 CRI / MSE)",
                "wez_radius_km": 70.0,
                "radar": "AN/MPQ-65 Phased Array Radar",
                "missiles_available": 32,
                "status": "Tracking / Weapons Free"
            },
            {
                "id": "bat-odesa-nasams",
                "name": "NASAMS Tier-2 Battery Alpha (Odesa Defense Sector)",
                "lat": 46.48,
                "lon": 30.72,
                "system": "NASAMS-3 (AMRAAM-ER / AIM-9X)",
                "wez_radius_km": 45.0,
                "radar": "AN/MPQ-64F1 Sentinel 3D Radar",
                "missiles_available": 24,
                "status": "Tracking / Engagement Queued"
            },
            {
                "id": "bat-constanta-patriot",
                "name": "NATO Patriot Battery Charlie (Mihail Kogalniceanu AFB)",
                "lat": 44.36,
                "lon": 28.48,
                "system": "Patriot PAC-3 MSE System",
                "wez_radius_km": 80.0,
                "radar": "AN/MPQ-65 Enhanced Radar Array",
                "missiles_available": 28,
                "status": "Combat Ready / Autonomous Sentry"
            }
        ],
        "target_assets": [
            {
                "id": "target-kyiv-c2",
                "name": "Kyiv National Strategic Command & Control HQ",
                "lat": 50.45,
                "lon": 30.52,
                "type": "C4ISR Strategic Underground Bunker",
                "strategic_value": 160.0,
                "blast_tolerance_km": 25.0,
                "status": "Operational / Maximum Defense Alert"
            },
            {
                "id": "target-odesa-port",
                "name": "Odesa Black Sea Grain & Deep-Water Naval Terminal",
                "lat": 46.49,
                "lon": 30.74,
                "type": "Critical Maritime Infrastructure & Logistics",
                "strategic_value": 120.0,
                "blast_tolerance_km": 30.0,
                "status": "Operational / Shielded by Air Defense"
            },
            {
                "id": "target-yuzhno-npp",
                "name": "Yuzhnoukrainsk Nuclear Power Grid Facility",
                "lat": 47.81,
                "lon": 31.22,
                "type": "National Critical Energy Generation Grid",
                "strategic_value": 145.0,
                "blast_tolerance_km": 20.0,
                "status": "Operational / Protected Sector"
            }
        ],
        "threat_trajectories": [
            {
                "threat_id": "THREAT-EE-001",
                "threat_name": "Iskander-M Quasi-Ballistic 9M723",
                "threat_type": "quasi-ballistic",
                "launch_site_id": "launch-rostov",
                "target_id": "target-kyiv-c2",
                "assigned_battery_id": "bat-kyiv-patriot",
                "speed_mach": 6.4,
                "apogee_km": 54.0,
                "progress": 0.74,
                "intercept_fraction": 0.76,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.48,
                "intercept_alt_km": 26.8,
                "p_kill": 0.98
            },
            {
                "threat_id": "THREAT-EE-002",
                "threat_name": "Kalibr 3M54 Land-Attack Cruise Missile",
                "threat_type": "cruise",
                "launch_site_id": "launch-sevastopol",
                "target_id": "target-odesa-port",
                "assigned_battery_id": "bat-odesa-nasams",
                "speed_mach": 0.88,
                "apogee_km": 1.2,
                "progress": 0.82,
                "intercept_fraction": 0.84,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.32,
                "intercept_alt_km": 0.95,
                "p_kill": 0.99
            },
            {
                "threat_id": "THREAT-EE-003",
                "threat_name": "Kh-47M2 Kinzhal Hypersonic Aero-Ballistic",
                "threat_type": "hypersonic",
                "launch_site_id": "launch-voronezh",
                "target_id": "target-yuzhno-npp",
                "assigned_battery_id": "bat-kyiv-patriot",
                "speed_mach": 9.2,
                "apogee_km": 42.0,
                "progress": 0.68,
                "intercept_fraction": 0.72,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.74,
                "intercept_alt_km": 28.5,
                "p_kill": 0.95
            },
            {
                "threat_id": "THREAT-EE-004",
                "threat_name": "Geran-2 Drone Swarm Cluster (16 UAVs)",
                "threat_type": "drone",
                "launch_site_id": "launch-gomel",
                "target_id": "target-kyiv-c2",
                "assigned_battery_id": "bat-kyiv-patriot",
                "speed_mach": 0.22,
                "apogee_km": 0.45,
                "progress": 0.55,
                "intercept_fraction": 0.58,
                "status": "IN_FLIGHT",
                "intercept_cpa_m": 0.0,
                "intercept_alt_km": 0.35,
                "p_kill": 0.92
            }
        ]
    },

    "persian_gulf": {
        "slug": "persian_gulf",
        "name": "Persian Gulf / Red Sea",
        "center": [24.5, 50.0],
        "zoom": 6,
        "description": "Strategic maritime and energy defense corridor featuring Medium-Range Ballistic Missiles (MRBM), Anti-Ship Ballistic Missiles, and long-range cruise salvos intercepted by THAAD exo-atmospheric interceptors, Patriot PAC-3, and US Navy Aegis destroyers.",
        "attacker_launch_sites": [
            {
                "id": "launch-shiraz",
                "name": "Shiraz Underground Missile Silo Complex",
                "lat": 29.59,
                "lon": 52.58,
                "faction": "Regional Aggressor Ballistic Command",
                "systems": ["Khyber Shekan MRBM", "Emad Heavy Ballistic"],
                "status": "Active / Silo Hatch Open"
            },
            {
                "id": "launch-bandar-abbas",
                "name": "Bandar Abbas Coastal Missile Bastion",
                "lat": 27.18,
                "lon": 56.27,
                "faction": "Aggressor Naval Coastal Guard",
                "systems": ["Fateh-110 Precision Guided", "Zolfaghar SRBM"],
                "status": "Active / Mobile TELs Deployed"
            },
            {
                "id": "launch-hodeidah",
                "name": "Hodeidah Red Sea Anti-Ship Launch Array",
                "lat": 14.79,
                "lon": 42.95,
                "faction": "Red Sea Asymmetric Militia",
                "systems": ["Quds-3 Land-Attack Cruise", "Al-Mandab Anti-Ship"],
                "status": "Active / Launch Coordinates Transmitted"
            },
            {
                "id": "launch-bushehr",
                "name": "Bushehr Coastal Sector Facility",
                "lat": 28.92,
                "lon": 50.84,
                "faction": "Aggressor Aviation & Missile Division",
                "systems": ["Paveh Long-Range Cruise Missile"],
                "status": "Active / Low-Level Salvo Fired"
            }
        ],
        "defender_batteries": [
            {
                "id": "bat-dhafra-thaad",
                "name": "THAAD Battery 1 (Al Dhafra Airbase, UAE)",
                "lat": 24.25,
                "lon": 54.55,
                "system": "Terminal High Altitude Area Defense (THAAD)",
                "wez_radius_km": 150.0,
                "radar": "AN/TPY-2 Forward-Based X-Band Radar",
                "missiles_available": 48,
                "status": "Tracking / Exo-Atmospheric Weapons Free"
            },
            {
                "id": "bat-rastanura-patriot",
                "name": "Patriot PAC-3 MSE (Ras Tanura Energy Defense)",
                "lat": 26.67,
                "lon": 50.16,
                "system": "MIM-104 Patriot (PAC-3 MSE)",
                "wez_radius_km": 80.0,
                "radar": "AN/MPQ-65 Multi-Function Radar",
                "missiles_available": 32,
                "status": "Tracking / Locked on Threat Corridor"
            },
            {
                "id": "bat-aegis-hormuz",
                "name": "US Navy DDG-51 Flight III Aegis Destroyer (Hormuz Patrol)",
                "lat": 26.25,
                "lon": 55.75,
                "system": "Aegis Baseline 9 / 10 (SM-6 Dual II / SM-3)",
                "wez_radius_km": 160.0,
                "radar": "AN/SPY-6(V)1 Air & Missile Defense Radar",
                "missiles_available": 56,
                "status": "Tracking / Integrated Fire Control Ready"
            }
        ],
        "target_assets": [
            {
                "id": "target-rastanura",
                "name": "Ras Tanura Strategic Oil Refining & Export Terminal",
                "lat": 26.67,
                "lon": 50.16,
                "type": "Global Critical Energy Infrastructure",
                "strategic_value": 160.0,
                "blast_tolerance_km": 30.0,
                "status": "Operational / Patriot Defended"
            },
            {
                "id": "target-dhafra-afb",
                "name": "Al Dhafra Coalition Airbase & Strategic Wing",
                "lat": 24.25,
                "lon": 54.55,
                "type": "Coalition 5th-Gen Aviation Airbase & C2",
                "strategic_value": 150.0,
                "blast_tolerance_km": 25.0,
                "status": "Operational / THAAD Shielded"
            },
            {
                "id": "target-bahrain-5thfleet",
                "name": "NSA Bahrain / US 5th Fleet Headquarters",
                "lat": 26.21,
                "lon": 50.60,
                "type": "Naval Component Command & Communications Hub",
                "strategic_value": 155.0,
                "blast_tolerance_km": 20.0,
                "status": "Operational / High Threat Alert"
            }
        ],
        "threat_trajectories": [
            {
                "threat_id": "THREAT-PG-001",
                "threat_name": "Khyber Shekan MRBM (Mach 8.0)",
                "threat_type": "mrbm",
                "launch_site_id": "launch-shiraz",
                "target_id": "target-dhafra-afb",
                "assigned_battery_id": "bat-dhafra-thaad",
                "speed_mach": 8.2,
                "apogee_km": 95.0,
                "progress": 0.77,
                "intercept_fraction": 0.79,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.55,
                "intercept_alt_km": 68.2,
                "p_kill": 0.97
            },
            {
                "threat_id": "THREAT-PG-002",
                "threat_name": "Paveh Long-Range Cruise Missile",
                "threat_type": "cruise",
                "launch_site_id": "launch-bushehr",
                "target_id": "target-rastanura",
                "assigned_battery_id": "bat-rastanura-patriot",
                "speed_mach": 0.85,
                "apogee_km": 1.4,
                "progress": 0.70,
                "intercept_fraction": 0.73,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.40,
                "intercept_alt_km": 1.1,
                "p_kill": 0.98
            },
            {
                "threat_id": "THREAT-PG-003",
                "threat_name": "Anti-Ship Ballistic Missile Fateh-110",
                "threat_type": "ballistic",
                "launch_site_id": "launch-bandar-abbas",
                "target_id": "target-bahrain-5thfleet",
                "assigned_battery_id": "bat-aegis-hormuz",
                "speed_mach": 4.5,
                "apogee_km": 48.0,
                "progress": 0.65,
                "intercept_fraction": 0.68,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.62,
                "intercept_alt_km": 24.8,
                "p_kill": 0.96
            }
        ]
    },

    "taiwan_strait": {
        "slug": "taiwan_strait",
        "name": "Taiwan Strait / Indo-Pacific",
        "center": [24.2, 120.5],
        "zoom": 7,
        "description": "High-density cross-strait saturation scenario involving DF-17 Hypersonic Glide Vehicles, DF-16 ballistic salvos, supersonic anti-ship missiles, and massive loitering UAV swarms defended by Tien Kung III, Patriot PAC-3 CRI, and Aegis BMD destroyers.",
        "attacker_launch_sites": [
            {
                "id": "launch-quanzhou",
                "name": "Quanzhou PLARF Brigade 611 Missile Base",
                "lat": 24.90,
                "lon": 118.60,
                "faction": "Opposing Rocket Force",
                "systems": ["DF-16 Medium Ballistic", "DF-11AZT SRBM"],
                "status": "Active / Coordinated Saturation Salvo"
            },
            {
                "id": "launch-ganzhou",
                "name": "Ganzhou DF-17 Hypersonic Glide Regiment",
                "lat": 25.85,
                "lon": 114.93,
                "faction": "Opposing Hypersonic Strike Group",
                "systems": ["DF-17 Hypersonic Glide Vehicle (HGV)"],
                "status": "Active / Boost Phase Initiated"
            },
            {
                "id": "launch-ningde",
                "name": "Ningde Coastal TEL Launcher Facility",
                "lat": 26.66,
                "lon": 119.55,
                "faction": "Opposing Coastal Anti-Ship Brigade",
                "systems": ["YJ-18 Supersonic Anti-Ship Cruise", "YJ-12"],
                "status": "Active / Low-Level Salvo En Route"
            },
            {
                "id": "launch-meizhou",
                "name": "Meizhou Bay Unmanned Swarm Staging Area",
                "lat": 25.15,
                "lon": 119.00,
                "faction": "Opposing Drone Swarm Division",
                "systems": ["WZ-7 Recon / Loitering Strike Swarm"],
                "status": "Active / Cross-Strait Autonomous Swarm"
            }
        ],
        "defender_batteries": [
            {
                "id": "bat-taipei-patriot",
                "name": "Patriot PAC-3 CRI Battery (Taipei Nangang Complex)",
                "lat": 25.04,
                "lon": 121.61,
                "system": "MIM-104 Patriot (PAC-3 CRI)",
                "wez_radius_km": 70.0,
                "radar": "AN/MPQ-65 Phased Array Radar",
                "missiles_available": 32,
                "status": "Tracking / Weapons Free"
            },
            {
                "id": "bat-tienkung-taichung",
                "name": "Tien Kung III (Sky Bow 3) Battery (Taichung Sector)",
                "lat": 24.18,
                "lon": 120.60,
                "system": "Tien Kung III Advanced Air Defense System",
                "wez_radius_km": 95.0,
                "radar": "Chang Shan AESA Phased Array",
                "missiles_available": 36,
                "status": "Tracking / Active Target Allocation"
            },
            {
                "id": "bat-aegis-taiwan-east",
                "name": "US Navy Aegis Cruiser (Eastern Taiwan Screen)",
                "lat": 23.50,
                "lon": 122.80,
                "system": "Aegis Baseline 9 / SM-6 & SM-3 Block IB",
                "wez_radius_km": 170.0,
                "radar": "AN/SPY-1D(V) 3D Radar",
                "missiles_available": 64,
                "status": "Tracking / Multi-Tier Engagement Screen"
            }
        ],
        "target_assets": [
            {
                "id": "target-hengshan-c2",
                "name": "Heng Shan Joint Military Command Bunker (Taipei)",
                "lat": 25.13,
                "lon": 121.55,
                "type": "Supreme National Joint Armed Forces C2",
                "strategic_value": 160.0,
                "blast_tolerance_km": 20.0,
                "status": "Operational / Patriot Defended"
            },
            {
                "id": "target-hsinchu-airbase",
                "name": "Hsinchu Strategic Airbase & High-Tech Semiconductor Hub",
                "lat": 24.81,
                "lon": 120.94,
                "type": "Critical Semiconductor & 1st Tactical Fighter Wing",
                "strategic_value": 150.0,
                "blast_tolerance_km": 25.0,
                "status": "Operational / Tien Kung Protected"
            },
            {
                "id": "target-kaohsiung-naval",
                "name": "Kaohsiung Deep-Water Strategic Naval Complex",
                "lat": 22.61,
                "lon": 120.28,
                "type": "Deep-Water Fleet Naval Base & Repair Drydocks",
                "strategic_value": 135.0,
                "blast_tolerance_km": 30.0,
                "status": "Operational / Active Air Defense"
            }
        ],
        "threat_trajectories": [
            {
                "threat_id": "THREAT-TW-001",
                "threat_name": "DF-17 Hypersonic Glide Vehicle (Mach 9.5)",
                "threat_type": "hypersonic",
                "launch_site_id": "launch-ganzhou",
                "target_id": "target-hengshan-c2",
                "assigned_battery_id": "bat-taipei-patriot",
                "speed_mach": 9.5,
                "apogee_km": 40.0,
                "progress": 0.72,
                "intercept_fraction": 0.75,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.68,
                "intercept_alt_km": 31.4,
                "p_kill": 0.94
            },
            {
                "threat_id": "THREAT-TW-002",
                "threat_name": "DF-16 Medium-Range Ballistic Missile",
                "threat_type": "ballistic",
                "launch_site_id": "launch-quanzhou",
                "target_id": "target-hsinchu-airbase",
                "assigned_battery_id": "bat-tienkung-taichung",
                "speed_mach": 6.8,
                "apogee_km": 78.0,
                "progress": 0.78,
                "intercept_fraction": 0.81,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.38,
                "intercept_alt_km": 25.2,
                "p_kill": 0.98
            },
            {
                "threat_id": "THREAT-TW-003",
                "threat_name": "YJ-18 Supersonic Sea-Skimming Cruise Missile",
                "threat_type": "cruise",
                "launch_site_id": "launch-ningde",
                "target_id": "target-kaohsiung-naval",
                "assigned_battery_id": "bat-aegis-taiwan-east",
                "speed_mach": 2.8,
                "apogee_km": 0.8,
                "progress": 0.64,
                "intercept_fraction": 0.67,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.50,
                "intercept_alt_km": 0.65,
                "p_kill": 0.97
            }
        ]
    },

    "conus_homeland": {
        "slug": "conus_homeland",
        "name": "CONUS Homeland",
        "center": [46.0, -108.0],
        "zoom": 4,
        "description": "Strategic North American continental defense architecture simulating exo-atmospheric ICBM trajectories intercepted by Ground-Based Interceptors (GBI) at Fort Greely and Vandenberg SFB, augmented by THAAD and Aegis BMD Homeland defense screens.",
        "attacker_launch_sites": [
            {
                "id": "launch-arctic-gate",
                "name": "Suborbital Arctic Polar Entry Gate",
                "lat": 68.0,
                "lon": -140.0,
                "faction": "Strategic Adversary Ballistic Corps",
                "systems": ["Heavy ICBM (Sarmat / Topol-M Class)", "Avangard HGV"],
                "status": "Active / Exo-Atmospheric Descent Inbound"
            },
            {
                "id": "launch-pacific-ssbn",
                "name": "Eastern Pacific SSBN Bastion Launch Sector",
                "lat": 35.0,
                "lon": -145.0,
                "faction": "Adversary SSBN Submarine Fleet",
                "systems": ["Submarine-Launched Ballistic Missile (SLBM)"],
                "status": "Active / Sub-Surface Missile Breakout"
            },
            {
                "id": "launch-atlantic-corridor",
                "name": "North Atlantic Hypersonic Corridor",
                "lat": 55.0,
                "lon": -45.0,
                "faction": "Strategic Aerospace Intercontinental Strike",
                "systems": ["Fractional Orbital Hypersonic Glide Vehicle"],
                "status": "Active / High-Mach Polar Trajectory"
            }
        ],
        "defender_batteries": [
            {
                "id": "bat-fort-greely-gmd",
                "name": "Ground-Based Midcourse Defense (Fort Greely, AK)",
                "lat": 63.97,
                "lon": -145.73,
                "system": "Ground-Based Interceptor (GBI / Exo-Atmospheric Kill Vehicle)",
                "wez_radius_km": 1200.0,
                "radar": "Sea-Based X-Band Radar (SBX-1) & Cobra Dane",
                "missiles_available": 40,
                "status": "Tracking / Space Kill Vehicle Queued"
            },
            {
                "id": "bat-vandenberg-gmd",
                "name": "GMD Missile Defense Silos (Vandenberg SFB, CA)",
                "lat": 34.74,
                "lon": -120.57,
                "system": "Ground-Based Interceptor (GBI)",
                "wez_radius_km": 1000.0,
                "radar": "Upgraded Early Warning Radar (UEWR)",
                "missiles_available": 20,
                "status": "Tracking / Weapons Free"
            },
            {
                "id": "bat-fort-bliss-thaad",
                "name": "THAAD Homeland Defense Battery (Fort Bliss, TX)",
                "lat": 31.85,
                "lon": -106.40,
                "system": "Terminal High Altitude Area Defense (THAAD)",
                "wez_radius_km": 250.0,
                "radar": "AN/TPY-2 Radar",
                "missiles_available": 48,
                "status": "Combat Ready / Terminal Layer Active"
            }
        ],
        "target_assets": [
            {
                "id": "target-norad-cheyenne",
                "name": "NORAD Cheyenne Mountain Strategic Complex (CO)",
                "lat": 38.74,
                "lon": -104.85,
                "type": "National Strategic Aerospace Warning & Command",
                "strategic_value": 160.0,
                "blast_tolerance_km": 25.0,
                "status": "Operational / GBI Midcourse Protected"
            },
            {
                "id": "target-offutt-stratcom",
                "name": "US Strategic Command HQ (Offutt AFB, NE)",
                "lat": 41.11,
                "lon": -95.91,
                "type": "Nuclear Command, Control & Communications (NC3)",
                "strategic_value": 160.0,
                "blast_tolerance_km": 25.0,
                "status": "Operational / High Threat Readiness"
            },
            {
                "id": "target-malmstrom-silos",
                "name": "Malmstrom AFB Nuclear Deterrent Silo Wing (MT)",
                "lat": 47.50,
                "lon": -111.18,
                "type": "Intercontinental Nuclear Deterrent Silo Field",
                "strategic_value": 150.0,
                "blast_tolerance_km": 30.0,
                "status": "Operational / Protected Field"
            }
        ],
        "threat_trajectories": [
            {
                "threat_id": "THREAT-US-001",
                "threat_name": "Heavy ICBM Suborbital Warhead (Mach 22.0)",
                "threat_type": "icbm",
                "launch_site_id": "launch-arctic-gate",
                "target_id": "target-norad-cheyenne",
                "assigned_battery_id": "bat-fort-greely-gmd",
                "speed_mach": 22.4,
                "apogee_km": 1150.0,
                "progress": 0.74,
                "intercept_fraction": 0.76,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.42,
                "intercept_alt_km": 420.0,
                "p_kill": 0.96
            },
            {
                "threat_id": "THREAT-US-002",
                "threat_name": "Submarine-Launched Ballistic Missile (SLBM)",
                "threat_type": "ballistic",
                "launch_site_id": "launch-pacific-ssbn",
                "target_id": "target-malmstrom-silos",
                "assigned_battery_id": "bat-vandenberg-gmd",
                "speed_mach": 14.5,
                "apogee_km": 550.0,
                "progress": 0.70,
                "intercept_fraction": 0.73,
                "status": "INTERCEPTED",
                "intercept_cpa_m": 0.58,
                "intercept_alt_km": 195.0,
                "p_kill": 0.95
            }
        ]
    }
}


# ==============================================================================
# 5. 2D TACTICAL MAP BUILDER (DASH-LEAFLET)
# ==============================================================================
