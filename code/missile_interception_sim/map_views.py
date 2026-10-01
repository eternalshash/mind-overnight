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

def build_tactical_leaflet_map(
    theater_key: str = "eastern_europe",
    show_wez: bool = True,
    show_interceptors: bool = True,
    show_bursts: bool = True,
    active_threats: bool = True,
    height: str = "660px",
    custom_launch_sites: Optional[List[Dict[str, Any]]] = None,
    custom_batteries: Optional[List[Dict[str, Any]]] = None,
    custom_targets: Optional[List[Dict[str, Any]]] = None
) -> dl.MapContainer:
    """
    Construct an interactive 2D Tactical Map using dash-leaflet:
    - Dark military basemap tiles (CartoDB Dark Matter)
    - Draggable red markers for Attacker Launch Sites
    - Draggable green/cyan markers for Defender Batteries with radar WEZ circles
    - Draggable gold markers for Defended Target HVAs
    - Dynamic Polylines / Geodesic arcs for active missile and drone trajectories
    - Animated / real-time threat tracking markers with velocity, altitude, and ETA readouts
    - Detonation burst markers (gold stars / red explosions) at kinetic intercept and impact locations
    """
    theater = THEATER_PRESETS.get(theater_key, THEATER_PRESETS["eastern_europe"])
    center = theater["center"]
    zoom = theater["zoom"]

    launch_sites = custom_launch_sites if custom_launch_sites is not None else theater["attacker_launch_sites"]
    batteries = custom_batteries if custom_batteries is not None else theater["defender_batteries"]
    targets = custom_targets if custom_targets is not None else theater["target_assets"]
    trajectories = theater.get("threat_trajectories", [])

    children: List[Any] = []

    # 1. Dark Basemap Tile Layer (CartoDB Dark Matter)
    children.append(
        dl.TileLayer(
            id={"type": "tactical-tile-layer", "theater": theater_key},
            url=TILE_CARTO_DARK_MATTER["url"],
            attribution=TILE_CARTO_DARK_MATTER["attribution"],
            maxZoom=TILE_CARTO_DARK_MATTER["maxZoom"]
        )
    )

    # Lookup dictionaries for fast coordinate reference
    launch_dict = {s["id"]: s for s in launch_sites}
    target_dict = {t["id"]: t for t in targets}
    battery_dict = {b["id"]: b for b in batteries}

    # 2. Attacker Launch Sites (Draggable Red Markers)
    for site in launch_sites:
        site_id = site["id"]
        lat, lon = site["lat"], site["lon"]
        tooltip_content = f"🔴 LAUNCH SITE: {site['name']} ({lat:.2f}°, {lon:.2f}°)"
        popup_content = html.Div([
            html.H5(site["name"], style={"color": "#ff3344", "margin": "0 0 5px 0", "fontWeight": "bold"}),
            html.P(f"Faction: {site.get('faction', 'Opposing Force')}", style={"margin": "2px 0", "fontSize": "12px"}),
            html.P(f"Coordinates: {lat:.4f}°N, {lon:.4f}°E", style={"margin": "2px 0", "fontSize": "11px", "color": "#aaaaaa"}),
            html.Hr(style={"borderColor": "#444444", "margin": "6px 0"}),
            html.P("Available Threat Inventories:", style={"margin": "2px 0", "fontSize": "11px", "fontWeight": "bold"}),
            html.Ul([html.Li(sys, style={"fontSize": "11px", "color": "#ff8899"}) for sys in site.get("systems", [])], style={"paddingLeft": "18px", "margin": "4px 0"}),
            html.Div(f"Status: {site.get('status', 'Operational')}", style={"fontSize": "11px", "color": "#00ff88", "marginTop": "4px"}),
            html.Div("ℹ️ Draggable: Click and drag marker to relocate aggressor launch origin.", style={"fontSize": "10px", "color": "#888888", "marginTop": "6px", "fontStyle": "italic"})
        ], style={"color": "#ffffff", "backgroundColor": "#161b22", "padding": "8px", "borderRadius": "4px", "minWidth": "220px"})

        children.append(
            dl.Marker(
                id={"type": "attacker-launch-site", "id": site_id},
                position=[lat, lon],
                draggable=True,
                icon=dict(
                    iconUrl=ATTACKER_LAUNCH_ICON_URI,
                    iconSize=[34, 34],
                    iconAnchor=[17, 17],
                    popupAnchor=[0, -17]
                ),
                children=[
                    dl.Tooltip(tooltip_content),
                    dl.Popup(popup_content)
                ]
            )
        )

    # 3. Defender Batteries (Draggable Green/Cyan Markers with Radar WEZ Circles)
    for bat in batteries:
        bat_id = bat["id"]
        lat, lon = bat["lat"], bat["lon"]
        wez_km = bat.get("wez_radius_km", 70.0)
        wez_meters = wez_km * 1000.0

        # Radar WEZ Circle
        if show_wez:
            children.append(
                dl.Circle(
                    id={"type": "radar-wez-circle", "id": f"{bat_id}-wez"},
                    center=[lat, lon],
                    radius=wez_meters,
                    color="#00ff88",
                    fillColor="#00ff88",
                    fillOpacity=0.10,
                    weight=1.6,
                    dashArray="5, 5",
                    children=[
                        dl.Tooltip(f"Radar WEZ: {bat['name']} (Radius: {wez_km:.0f} km)")
                    ]
                )
            )

        tooltip_content = f"🛡️ DEFENDER: {bat['name']} (WEZ: {wez_km:.0f} km)"
        popup_content = html.Div([
            html.H5(bat["name"], style={"color": "#00ff88", "margin": "0 0 5px 0", "fontWeight": "bold"}),
            html.P(f"System: {bat.get('system', 'Air Defense Battery')}", style={"margin": "2px 0", "fontSize": "12px"}),
            html.P(f"Radar Sensor: {bat.get('radar', 'AESA Radar Array')}", style={"margin": "2px 0", "fontSize": "11px", "color": "#00e5ff"}),
            html.P(f"Engagement WEZ Radius: {wez_km:.1f} km ({wez_km * 0.539957:.1f} nmi)", style={"margin": "2px 0", "fontSize": "11px"}),
            html.P(f"Ready Munitions: {bat.get('missiles_available', 32)} Interceptors", style={"margin": "2px 0", "fontSize": "11px", "color": "#ffea00"}),
            html.Hr(style={"borderColor": "#444444", "margin": "6px 0"}),
            html.Div(f"Operational State: {bat.get('status', 'Weapons Free')}", style={"fontSize": "11px", "color": "#00ff88"}),
            html.Div("ℹ️ Draggable: Click and drag marker to reposition IAMD battery on theater grid.", style={"fontSize": "10px", "color": "#888888", "marginTop": "6px", "fontStyle": "italic"})
        ], style={"color": "#ffffff", "backgroundColor": "#161b22", "padding": "8px", "borderRadius": "4px", "minWidth": "230px"})

        children.append(
            dl.Marker(
                id={"type": "defender-battery", "id": bat_id},
                position=[lat, lon],
                draggable=True,
                icon=dict(
                    iconUrl=DEFENDER_BATTERY_ICON_URI,
                    iconSize=[34, 34],
                    iconAnchor=[17, 17],
                    popupAnchor=[0, -17]
                ),
                children=[
                    dl.Tooltip(tooltip_content),
                    dl.Popup(popup_content)
                ]
            )
        )

    # 4. Defended Target Assets / HVAs (Draggable Gold Markers)
    for tgt in targets:
        tgt_id = tgt["id"]
        lat, lon = tgt["lat"], tgt["lon"]
        strat_val = tgt.get("strategic_value", 100.0)

        tooltip_content = f"⭐ TARGET HVA: {tgt['name']} (Value: {strat_val:.0f})"
        popup_content = html.Div([
            html.H5(tgt["name"], style={"color": "#ffb700", "margin": "0 0 5px 0", "fontWeight": "bold"}),
            html.P(f"Classification: {tgt.get('type', 'Strategic Command Infrastructure')}", style={"margin": "2px 0", "fontSize": "12px"}),
            html.P(f"Strategic Value Score: {strat_val:.1f} / 160.0", style={"margin": "2px 0", "fontSize": "11px", "color": "#ffd700", "fontWeight": "bold"}),
            html.P(f"Blast Tolerance Radius: {tgt.get('blast_tolerance_km', 25.0):.1f} km", style={"margin": "2px 0", "fontSize": "11px"}),
            html.Hr(style={"borderColor": "#444444", "margin": "6px 0"}),
            html.Div(f"Status: {tgt.get('status', 'Operational')}", style={"fontSize": "11px", "color": "#00e5ff"}),
            html.Div("ℹ️ Draggable: Relocate defended asset to evaluate spatial defense posture.", style={"fontSize": "10px", "color": "#888888", "marginTop": "6px", "fontStyle": "italic"})
        ], style={"color": "#ffffff", "backgroundColor": "#161b22", "padding": "8px", "borderRadius": "4px", "minWidth": "220px"})

        children.append(
            dl.Marker(
                id={"type": "target-asset", "id": tgt_id},
                position=[lat, lon],
                draggable=True,
                icon=dict(
                    iconUrl=TARGET_ASSET_ICON_URI,
                    iconSize=[34, 34],
                    iconAnchor=[17, 17],
                    popupAnchor=[0, -17]
                ),
                children=[
                    dl.Tooltip(tooltip_content),
                    dl.Popup(popup_content)
                ]
            )
        )

    # 5. Dynamic Trajectories, Threat Markers, and Detonation Bursts
    color_map = {
        "ballistic": "#ff3344",
        "quasi-ballistic": "#ff3344",
        "mrbm": "#ff2244",
        "icbm": "#ff0033",
        "hypersonic": "#ff00bb",
        "cruise": "#ff9900",
        "drone": "#ffea00"
    }

    for idx, threat in enumerate(trajectories):
        t_id = threat["threat_id"]
        t_type = threat["threat_type"].lower()
        l_site = launch_dict.get(threat["launch_site_id"])
        tgt = target_dict.get(threat["target_id"])
        bat = battery_dict.get(threat["assigned_battery_id"])

        if not l_site or not tgt:
            continue

        color = color_map.get(t_type, "#ff4444")
        waypoints = generate_trajectory_waypoints(
            l_site["lat"], l_site["lon"], tgt["lat"], tgt["lon"],
            threat_type=t_type,
            apogee_km=threat.get("apogee_km", 60.0),
            n_points=60
        )

        all_coords = [[wp["lat"], wp["lon"]] for wp in waypoints]
        progress = threat.get("progress", 0.70)
        progress_idx = int(progress * (len(waypoints) - 1))
        cur_wp = waypoints[progress_idx]

        # Flown Path (Solid Bright Line)
        flown_coords = all_coords[:progress_idx + 1]
        if len(flown_coords) > 1:
            children.append(
                dl.Polyline(
                    id={"type": "threat-flown-polyline", "id": f"{t_id}-flown"},
                    positions=flown_coords,
                    color=color,
                    weight=3.2,
                    opacity=0.95,
                    children=[
                        dl.Tooltip(f"Trajectory: {threat.get('threat_name', t_id)} [Active Track]")
                    ]
                )
            )

        # Projected Path (Dashed Semi-Transparent Line)
        proj_coords = all_coords[progress_idx:]
        if len(proj_coords) > 1:
            children.append(
                dl.Polyline(
                    id={"type": "threat-projected-polyline", "id": f"{t_id}-proj"},
                    positions=proj_coords,
                    color=color,
                    weight=2.0,
                    opacity=0.45,
                    dashArray="5, 6"
                )
            )

        # Animated Real-Time Threat Position Marker
        if active_threats:
            speed_mach = threat.get("speed_mach", 4.0)
            alt_km = cur_wp["alt_km"]
            children.append(
                dl.Marker(
                    id={"type": "threat-active-marker", "id": f"{t_id}-pos"},
                    position=[cur_wp["lat"], cur_wp["lon"]],
                    icon=dict(
                        iconUrl=THREAT_POSITION_ICON_URI,
                        iconSize=[26, 26],
                        iconAnchor=[13, 13]
                    ),
                    children=[
                        dl.Tooltip(
                            f"🚀 {threat.get('threat_name', t_id)} | Alt: {alt_km:.1f} km | Speed: Mach {speed_mach:.1f} | State: {threat['status']}"
                        )
                    ]
                )
            )

        # Kinetic Intercept or Impact Detonation Burst
        if show_bursts:
            status = threat.get("status", "IN_FLIGHT")
            if status == "INTERCEPTED":
                int_frac = threat.get("intercept_fraction", 0.75)
                int_lat, int_lon = great_circle_intermediate_point(
                    l_site["lat"], l_site["lon"], tgt["lat"], tgt["lon"], int_frac
                )
                cpa_m = threat.get("intercept_cpa_m", 0.5)
                int_alt = threat.get("intercept_alt_km", 25.0)
                p_kill = threat.get("p_kill", 0.96) * 100.0

                # Interceptor Vector from Battery to Intercept Point
                if show_interceptors and bat:
                    int_track = [[bat["lat"], bat["lon"]], [int_lat, int_lon]]
                    children.append(
                        dl.Polyline(
                            id={"type": "interceptor-vector", "id": f"{t_id}-int-vector"},
                            positions=int_track,
                            color="#00e5ff",
                            weight=2.4,
                            dashArray="4, 4",
                            opacity=0.85,
                            children=[
                                dl.Tooltip(f"Interceptor Vector: {bat['name']} -> Kinetic Intercept Point")
                            ]
                        )
                    )

                burst_tooltip = f"💥 KINETIC INTERCEPT CONFIRMED | CPA: {cpa_m:.2f} m | Alt: {int_alt:.1f} km | P_kill: {p_kill:.1f}%"
                burst_popup = html.Div([
                    html.H5("💥 KINETIC HIT CONFIRMED", style={"color": "#ffea00", "margin": "0 0 4px 0", "fontWeight": "bold"}),
                    html.P(f"Target Threat: {threat.get('threat_name', t_id)}", style={"margin": "2px 0", "fontSize": "12px", "color": "#ffffff"}),
                    html.P(f"Defending Battery: {bat['name'] if bat else 'Assigned IAMD Battery'}", style={"margin": "2px 0", "fontSize": "11px", "color": "#00ff88"}),
                    html.Hr(style={"borderColor": "#444444", "margin": "6px 0"}),
                    html.P(f"Intercept Altitude: {int_alt:.1f} km MSL", style={"margin": "2px 0", "fontSize": "11px"}),
                    html.P(f"Sub-Timestep CPA Miss Distance: {cpa_m:.2f} meters", style={"margin": "2px 0", "fontSize": "11px", "color": "#00e5ff", "fontWeight": "bold"}),
                    html.P(f"Calculated Interception Kill Probability: {p_kill:.1f}%", style={"margin": "2px 0", "fontSize": "11px", "color": "#00ff88", "fontWeight": "bold"}),
                    html.Div("Outcome: Catastrophic Kinetic Warhead Deflagration", style={"fontSize": "10px", "color": "#ffcc00", "marginTop": "6px", "fontWeight": "bold"})
                ], style={"backgroundColor": "#161b22", "padding": "8px", "borderRadius": "4px", "minWidth": "240px"})

                children.append(
                    dl.Marker(
                        id={"type": "detonation-burst-marker", "id": f"{t_id}-burst"},
                        position=[int_lat, int_lon],
                        icon=dict(
                            iconUrl=DETONATION_BURST_ICON_URI,
                            iconSize=[38, 38],
                            iconAnchor=[19, 19]
                        ),
                        children=[
                            dl.Tooltip(burst_tooltip),
                            dl.Popup(burst_popup)
                        ]
                    )
                )

            elif status == "IMPACT":
                # Leaker Impact Burst at Target HVA
                children.append(
                    dl.Marker(
                        id={"type": "leaker-impact-marker", "id": f"{t_id}-impact"},
                        position=[tgt["lat"], tgt["lon"]],
                        icon=dict(
                            iconUrl=LEAKER_IMPACT_ICON_URI,
                            iconSize=[36, 36],
                            iconAnchor=[18, 18]
                        ),
                        children=[
                            dl.Tooltip(f"🔥 LEAKER IMPACT: {tgt['name']} sustained kinetic damage!"),
                            dl.Popup(html.Div([
                                html.H5("⚠️ LEAKER TARGET IMPACT", style={"color": "#ff3344", "margin": "0"}),
                                html.P(f"Penetrated defenses and struck {tgt['name']}.", style={"fontSize": "12px", "color": "#ffffff"})
                            ], style={"backgroundColor": "#161b22", "padding": "8px"}))
                        ]
                    )
                )

    # 6. Leaflet Map Controls
    children.append(dl.ScaleControl(position="bottomleft", metric=True, imperial=True))
    children.append(dl.FullScreenControl(position="topright"))

    return dl.MapContainer(
        id="tactical-2d-leaflet-map",
        center=center,
        zoom=zoom,
        children=children,
        style={
            "width": "100%",
            "height": height,
            "borderRadius": "8px",
            "border": "1px solid #30363d",
            "backgroundColor": "#0d1117"
        }
    )


# ==============================================================================
# 6. ALTITUDE PROFILE CHART BUILDER (MISSILEMAP STYLE)
# ==============================================================================

def build_altitude_profile_figure(
    theater_key: str = "eastern_europe",
    threat_index: int = 0,
    custom_threat: Optional[Dict[str, Any]] = None,
    height: int = 440
) -> go.Figure:
    """
    Construct a high-fidelity Plotly 2D Altitude Profile Chart (Missilemap style):
    - Downrange Distance (km) on X-axis vs. Altitude (km) on Y-axis
    - Stratified atmospheric zones (Troposphere, Stratosphere, Mesosphere, Karman Line)
    - Simultaneous curves for:
      * Multi-phase Threat Trajectory (Boost burnout, Midcourse flight, Terminal dive)
      * Apogee Marker with ballistic altitude and range annotation
      * Interceptor Climb Curve originating from defender battery downrange position
      * Kinetic Intercept Point with detonation burst marker and CPA callout
      * Defended Target Asset marker at ground level
    """
    theater = THEATER_PRESETS.get(theater_key, THEATER_PRESETS["eastern_europe"])
    trajectories = theater.get("threat_trajectories", [])

    if custom_threat is not None:
        th = custom_threat
    elif trajectories and 0 <= threat_index < len(trajectories):
        th = trajectories[threat_index]
    else:
        th = {
            "threat_id": "DEFAULT-001",
            "threat_name": "Generic Ballistic Trajectory",
            "threat_type": "ballistic",
            "launch_site_id": "launch-rostov",
            "target_id": "target-kyiv-c2",
            "assigned_battery_id": "bat-kyiv-patriot",
            "speed_mach": 6.2,
            "apogee_km": 115.0,
            "progress": 0.75,
            "intercept_fraction": 0.77,
            "status": "INTERCEPTED",
            "intercept_cpa_m": 0.52,
            "intercept_alt_km": 32.5,
            "p_kill": 0.96
        }

    # Retrieve associated sites
    launch_sites = {s["id"]: s for s in theater["attacker_launch_sites"]}
    target_assets = {t["id"]: t for t in theater["target_assets"]}
    defender_bats = {b["id"]: b for b in theater["defender_batteries"]}

    ls = launch_sites.get(th.get("launch_site_id", ""), {"name": "Aggressor Launch Site", "lat": 47.0, "lon": 39.0})
    tgt = target_assets.get(th.get("target_id", ""), {"name": "Defended HVA Target", "lat": 50.0, "lon": 30.0})
    bat = defender_bats.get(th.get("assigned_battery_id", ""), {"name": "Defender Battery", "lat": 50.4, "lon": 30.5})

    total_range_km = haversine_distance_km(ls["lat"], ls["lon"], tgt["lat"], tgt["lon"])
    if total_range_km < 10.0:
        total_range_km = 800.0

    # Downrange position of defender battery relative to launch site
    bat_dist_from_launch = haversine_distance_km(ls["lat"], ls["lon"], bat["lat"], bat["lon"])
    # Cap battery distance inside downrange plot
    bat_downrange_km = min(total_range_km * 0.95, max(total_range_km * 0.5, bat_dist_from_launch))

    apogee_km = float(th.get("apogee_km", 115.0))
    t_type = th.get("threat_type", "ballistic").lower()

    # Generate Altitude Profile Curves
    n_pts = 120
    x_threat = np.linspace(0.0, total_range_km, n_pts)
    z_threat = np.zeros(n_pts)

    for i, x in enumerate(x_threat):
        u = x / total_range_km
        if t_type in ["ballistic", "quasi-ballistic", "srbm", "mrbm", "icbm"]:
            # Parabolic trajectory
            z_threat[i] = 4.0 * apogee_km * u * (1.0 - u)
        elif t_type in ["hypersonic", "hgv"]:
            # Pull-up into skip-glide
            if u < 0.12:
                z_threat[i] = 36.0 * math.sin((u / 0.12) * math.pi / 2.0)
            elif u > 0.88:
                z_threat[i] = 36.0 * math.cos(((u - 0.88) / 0.12) * math.pi / 2.0)
            else:
                z_threat[i] = 36.0 + 2.5 * math.sin(6.0 * math.pi * u)
        elif t_type in ["cruise", "supersonic cruise", "ashm"]:
            z_threat[i] = 0.9 + 0.3 * math.sin(3.0 * math.pi * u)
        else: # drone
            z_threat[i] = 0.35 + 0.1 * math.sin(5.0 * math.pi * u)

    z_max_plot = max(120.0, apogee_km * 1.25)
    fig = go.Figure()

    # Atmospheric Strata Background Shading
    fig.add_hrect(
        y0=0, y1=12, fillcolor="#0b1b2b", opacity=0.45, line_width=0, layer="below",
        annotation_text="Troposphere (0-12 km) | Commercial Aviation & Dense Weather",
        annotation_position="top left", annotation_font=dict(color="#4a7090", size=10)
    )
    fig.add_hrect(
        y0=12, y1=50, fillcolor="#0e1724", opacity=0.45, line_width=0, layer="below",
        annotation_text="Stratosphere (12-50 km) | Hypersonic Glide & Terminal SAM Intercept Window",
        annotation_position="top left", annotation_font=dict(color="#4a7090", size=10)
    )
    fig.add_hrect(
        y0=50, y1=85, fillcolor="#09101a", opacity=0.45, line_width=0, layer="below",
        annotation_text="Mesosphere (50-85 km) | Upper Tier Engagement Corridor",
        annotation_position="top left", annotation_font=dict(color="#4a7090", size=10)
    )
    if z_max_plot >= 100.0:
        fig.add_hline(
            y=100.0, line_dash="dash", line_color="#ff0055", line_width=1.5,
            annotation_text="Karman Line (100 km) — Boundary of Space / Exo-Atmospheric Tier",
            annotation_position="top left", annotation_font=dict(color="#ff3377", size=10.5, family="monospace")
        )

    # 1. Threat Trajectory Curve
    threat_line_color = "#ff3344" if t_type != "hypersonic" else "#ff00bb"
    fig.add_trace(go.Scatter(
        x=x_threat,
        y=z_threat,
        mode="lines",
        name=f"Threat: {th.get('threat_name', 'Aggressor Missile')}",
        line=dict(color=threat_line_color, width=3.5),
        hovertemplate="<b>Downrange:</b> %{x:.1f} km<br><b>Altitude:</b> %{y:.1f} km<extra></extra>"
    ))

    # Boost Phase Burnout Marker
    boost_x = total_range_km * 0.10
    boost_z = np.interp(boost_x, x_threat, z_threat)
    fig.add_trace(go.Scatter(
        x=[boost_x],
        y=[boost_z],
        mode="markers+text",
        name="Booster Burnout / Stage Separation",
        marker=dict(size=8, color="#ff8800", symbol="triangle-up", line=dict(color="#ffffff", width=1)),
        text=["Booster Burnout"],
        textposition="top left",
        textfont=dict(color="#ff8800", size=10),
        hovertemplate="<b>Booster Burnout:</b> Downrange %{x:.1f} km, Alt %{y:.1f} km<extra></extra>"
    ))

    # 2. Apogee Marker
    apogee_idx = int(np.argmax(z_threat))
    x_apogee = x_threat[apogee_idx]
    z_apogee = z_threat[apogee_idx]

    fig.add_trace(go.Scatter(
        x=[x_apogee],
        y=[z_apogee],
        mode="markers+text",
        name="Ballistic Apogee Peak",
        marker=dict(size=14, color="#ffea00", symbol="star", line=dict(color="#ff3300", width=1.5)),
        text=[f"APOGEE: {z_apogee:.1f} km (Range {x_apogee:.0f} km)"],
        textposition="top center",
        textfont=dict(color="#ffea00", size=11, family="monospace"),
        hovertemplate=f"<b>Peak Apogee:</b> {z_apogee:.1f} km<br><b>Downrange:</b> {x_apogee:.1f} km<br><b>Velocity:</b> Mach {th.get('speed_mach', 6.0):.1f}<extra></extra>"
    ))

    # 3. Defender Battery Launch Point & Radar Sector
    fig.add_trace(go.Scatter(
        x=[bat_downrange_km],
        y=[0.0],
        mode="markers+text",
        name=f"Defender: {bat.get('name', 'Battery')}",
        marker=dict(size=13, color="#00ff88", symbol="square", line=dict(color="#ffffff", width=1.5)),
        text=[f"BATTERY: {bat.get('name', 'IAMD Unit')[:24]}"],
        textposition="bottom center",
        textfont=dict(color="#00ff88", size=10.5),
        hovertemplate=f"<b>Defender Battery:</b> {bat.get('name', 'IAMD')}<br><b>Downrange:</b> {bat_downrange_km:.1f} km<extra></extra>"
    ))

    # 4. Kinetic Intercept Point & Interceptor Climb Curve
    int_frac = float(th.get("intercept_fraction", 0.76))
    x_int = total_range_km * int_frac
    z_int = float(np.interp(x_int, x_threat, z_threat))

    # Realistic Interceptor Climb Arc (from battery ground position to intercept point)
    n_climb = 40
    x_climb = np.linspace(bat_downrange_km, x_int, n_climb)
    u_climb = np.linspace(0.0, 1.0, n_climb)
    z_climb = z_int * (np.sin(u_climb * np.pi / 2.0) ** 1.3)

    fig.add_trace(go.Scatter(
        x=x_climb,
        y=z_climb,
        mode="lines",
        name=f"Interceptor Climb Curve ({bat.get('system', 'PAC-3 CRI')})",
        line=dict(color="#00e5ff", width=2.8, dash="dash"),
        hovertemplate="<b>Interceptor Downrange:</b> %{x:.1f} km<br><b>Altitude:</b> %{y:.1f} km<extra></extra>"
    ))

    # Kinetic Intercept Burst Marker
    cpa_m = float(th.get("intercept_cpa_m", 0.48))
    p_kill = float(th.get("p_kill", 0.97)) * 100.0

    fig.add_trace(go.Scatter(
        x=[x_int],
        y=[z_int],
        mode="markers+text",
        name="Kinetic Intercept Point (HIT)",
        marker=dict(size=18, color="#ffee00", symbol="diamond-wide", line=dict(color="#ff2200", width=2.5)),
        text=[f"💥 KINETIC HIT (CPA: {cpa_m:.2f} m | P_kill: {p_kill:.0f}%)"],
        textposition="top center",
        textfont=dict(color="#ffea00", size=11, family="monospace"),
        hovertemplate=(
            f"<b>💥 KINETIC KILL POINT</b><br>"
            f"Downrange Distance: {x_int:.1f} km<br>"
            f"Intercept Altitude: {z_int:.1f} km MSL<br>"
            f"Miss Distance (CPA): {cpa_m:.2f} meters<br>"
            f"Probability of Kill: {p_kill:.1f}%<extra></extra>"
        )
    ))

    # 5. Defended Target Asset Ground Marker
    fig.add_trace(go.Scatter(
        x=[total_range_km],
        y=[0.0],
        mode="markers+text",
        name=f"Target: {tgt.get('name', 'Defended Asset')}",
        marker=dict(size=14, color="#ffb700", symbol="star-diamond", line=dict(color="#ffffff", width=1.5)),
        text=[f"TARGET: {tgt.get('name', 'Defended HVA')[:24]}"],
        textposition="bottom center",
        textfont=dict(color="#ffb700", size=10.5),
        hovertemplate=f"<b>Defended HVA:</b> {tgt.get('name', 'HVA')}<br><b>Downrange:</b> {total_range_km:.1f} km<extra></extra>"
    ))

    # Layout & Military Styling
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"<b>Missilemap Tactical Altitude Profile: {th.get('threat_name', 'Threat Track')}</b><br>"
                 f"<sup>Engagement Downrange Range: {total_range_km:.0f} km | Peak Apogee: {z_apogee:.1f} km | Intercept Alt: {z_int:.1f} km</sup>",
            font=dict(size=14, color="#ffffff")
        ),
        xaxis=dict(
            title="Downrange Ground Distance (km)",
            gridcolor="#21262d",
            zerolinecolor="#30363d",
            range=[-20, total_range_km + 40],
            color="#c9d1d9"
        ),
        yaxis=dict(
            title="Altitude Above Mean Sea Level (km)",
            gridcolor="#21262d",
            zerolinecolor="#30363d",
            range=[-5, z_max_plot],
            color="#c9d1d9"
        ),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#090d14",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="#161b22",
            bordercolor="#30363d",
            borderwidth=1,
            font=dict(size=10, color="#ffffff")
        ),
        margin=dict(l=55, r=30, t=85, b=45),
        height=height
    )

    return fig


# ==============================================================================
# 7. 3D DIGITAL GLOBE MODE BUILDER (PLOTLY 3D SCATTER & SURFACE)
# ==============================================================================

# Simplified Continental Outlines for 3D Earth Realism
CONTINENTAL_COASTLINES: Dict[str, List[Tuple[float, float]]] = {
    "eurasia_north": [
        (36, -5), (44, -8), (48, -4), (54, 8), (58, 5), (62, 5), (71, 28), (68, 44),
        (70, 75), (75, 100), (77, 104), (73, 140), (66, 170), (60, 163), (53, 142),
        (43, 132), (38, 128), (35, 120), (22, 114), (10, 107), (1, 104), (16, 96),
        (22, 89), (13, 80), (8, 77), (25, 62), (25, 57), (12, 44), (12, 43), (22, 38),
        (31, 35), (36, 36), (41, 29), (42, 28), (44, 15), (41, 12), (43, 7), (36, -5)
    ],
    "africa": [
        (36, -5), (37, 11), (32, 25), (31, 32), (28, 34), (12, 44), (12, 51), (2, 45),
        (-12, 40), (-25, 33), (-34, 18), (-34, 25), (-23, 14), (-16, 12), (-5, 12),
        (4, 7), (6, 3), (4, -7), (10, -14), (15, -17), (21, -17), (28, -13), (36, -5)
    ],
    "north_america": [
        (71, -156), (70, -135), (60, -85), (55, -55), (45, -60), (35, -75), (25, -80),
        (30, -85), (25, -97), (20, -105), (15, -92), (9, -79), (15, -90), (23, -110),
        (32, -117), (38, -123), (48, -125), (58, -136), (60, -145), (60, -165), (71, -156)
    ],
    "south_america": [
        (12, -72), (7, -58), (-2, -44), (-8, -35), (-23, -42), (-35, -53), (-55, -67),
        (-46, -75), (-33, -72), (-18, -70), (-5, -81), (1, -79), (9, -79), (12, -72)
    ],
    "australia": [
        (-12, 131), (-12, 136), (-18, 140), (-25, 153), (-38, 145), (-35, 115), (-22, 114),
        (-15, 124), (-12, 131)
    ]
}


def build_3d_globe_figure(
    theater_key: str = "eastern_europe",
    show_earth_mesh: bool = True,
    show_continents: bool = True,
    show_wez_domes: bool = True,
    show_bursts: bool = True,
    altitude_scale: float = 3.5,
    height: int = 660
) -> go.Figure:
    """
    Construct an interactive 3D Digital Globe using Plotly 3D scatter and surface:
    - Renders spherical Earth with latitude/longitude grid and continental coastlines
    - Deep space background with subtle starfield points
    - Attacker Launch Sites, Defender Batteries, and Defended Target HVAs positioned on Earth sphere
    - 3D Suborbital Parabolic Arcs rising off the surface into space
    - 3D Radar Engagement Domes (wireframe rings / arches) over defender batteries
    - 3D Kinetic Intercept Detonation Bursts and Interceptor climb arcs
    - Dynamic theater-centric camera orientation aligned with selected theater center
    """
    theater = THEATER_PRESETS.get(theater_key, THEATER_PRESETS["eastern_europe"])
    center_lat, center_lon = theater["center"]

    fig = go.Figure()
    R = EARTH_RADIUS_KM

    # 1. Distant Starfield Background (Deep Space Ambience)
    np.random.seed(42)
    n_stars = 140
    theta_stars = np.random.uniform(0, 2.0 * np.pi, n_stars)
    phi_stars = np.random.uniform(0, np.pi, n_stars)
    r_stars = R * 2.8

    fig.add_trace(go.Scatter3d(
        x=r_stars * np.sin(phi_stars) * np.cos(theta_stars),
        y=r_stars * np.sin(phi_stars) * np.sin(theta_stars),
        z=r_stars * np.cos(phi_stars),
        mode="markers",
        marker=dict(size=1.6, color="#ffffff", opacity=0.65),
        hoverinfo="none",
        showlegend=False
    ))

    # 2. Spherical Earth Surface (Military Dark Slate Mesh)
    if show_earth_mesh:
        u_surf = np.linspace(0, 2 * np.pi, 45)
        v_surf = np.linspace(0, np.pi, 25)
        xs = R * np.outer(np.cos(u_surf), np.sin(v_surf))
        ys = R * np.outer(np.sin(u_surf), np.sin(v_surf))
        zs = R * np.outer(np.ones(np.size(u_surf)), np.cos(v_surf))
        surf_color = np.zeros_like(xs)

        fig.add_trace(go.Surface(
            x=xs, y=ys, z=zs,
            surfacecolor=surf_color,
            colorscale=[[0, "#08111a"], [1, "#0f1c29"]],
            showscale=False,
            opacity=0.88,
            hoverinfo="none",
            name="Earth Sphere"
        ))

    # 3. Latitude & Longitude Reference Grid Lines
    for lat_deg in [-60, -30, 0, 30, 60]:
        lons = np.linspace(-180, 180, 72)
        xl, yl, zl = [], [], []
        for lon_deg in lons:
            cx, cy, cz = lat_lon_to_cartesian(lat_deg, lon_deg, alt_km=2.0, radius=R)
            xl.append(cx)
            yl.append(cy)
            zl.append(cz)
        fig.add_trace(go.Scatter3d(
            x=xl, y=yl, z=zl,
            mode="lines",
            line=dict(color="#152b3c", width=1.4, dash="dot"),
            hoverinfo="none",
            showlegend=False
        ))

    for lon_deg in range(-180, 180, 45):
        lats = np.linspace(-85, 85, 40)
        xl, yl, zl = [], [], []
        for lat_deg in lats:
            cx, cy, cz = lat_lon_to_cartesian(lat_deg, lon_deg, alt_km=2.0, radius=R)
            xl.append(cx)
            yl.append(cy)
            zl.append(cz)
        fig.add_trace(go.Scatter3d(
            x=xl, y=yl, z=zl,
            mode="lines",
            line=dict(color="#152b3c", width=1.4, dash="dot"),
            hoverinfo="none",
            showlegend=False
        ))

    # 4. Continental Coastlines in Tactical Teal
    if show_continents:
        for c_name, coords in CONTINENTAL_COASTLINES.items():
            cx_list, cy_list, cz_list = [], [], []
            for lat, lon in coords:
                cx, cy, cz = lat_lon_to_cartesian(lat, lon, alt_km=4.0, radius=R)
                cx_list.append(cx)
                cy_list.append(cy)
                cz_list.append(cz)
            fig.add_trace(go.Scatter3d(
                x=cx_list, y=cy_list, z=cz_list,
                mode="lines",
                line=dict(color="#1d4863", width=2.0),
                hoverinfo="none",
                showlegend=False
            ))

    # 5. Attacker Launch Sites (Red Markers on Earth Surface)
    launch_sites = theater["attacker_launch_sites"]
    lx, ly, lz, lnames = [], [], [], []
    for s in launch_sites:
        cx, cy, cz = lat_lon_to_cartesian(s["lat"], s["lon"], alt_km=15.0, radius=R)
        lx.append(cx)
        ly.append(cy)
        lz.append(cz)
        lnames.append(f"🔴 Launch Site: {s['name']}")

    fig.add_trace(go.Scatter3d(
        x=lx, y=ly, z=lz,
        mode="markers+text",
        name="Aggressor Launch Complexes",
        marker=dict(size=7, color="#ff2244", symbol="square", line=dict(color="#ffffff", width=1.2)),
        text=[s["name"][:18] for s in launch_sites],
        textposition="top center",
        textfont=dict(color="#ff6677", size=9.5),
        hovertext=lnames,
        hoverinfo="text"
    ))

    # 6. Defended Target HVAs (Gold Markers on Earth Surface)
    target_assets = theater["target_assets"]
    tx, ty, tz, tnames = [], [], [], []
    for t in target_assets:
        cx, cy, cz = lat_lon_to_cartesian(t["lat"], t["lon"], alt_km=15.0, radius=R)
        tx.append(cx)
        ty.append(cy)
        tz.append(cz)
        tnames.append(f"⭐ Target HVA: {t['name']} (Value: {t.get('strategic_value', 100):.0f})")

    fig.add_trace(go.Scatter3d(
        x=tx, y=ty, z=tz,
        mode="markers+text",
        name="Defended Strategic HVAs",
        marker=dict(size=8, color="#ffb700", symbol="circle", line=dict(color="#ffffff", width=1.5)),
        text=[t["name"][:18] for t in target_assets],
        textposition="bottom center",
        textfont=dict(color="#ffd700", size=9.5),
        hovertext=tnames,
        hoverinfo="text"
    ))

    # 7. Defender Batteries (Emerald Markers on Earth Surface)
    defender_batteries = theater["defender_batteries"]
    bx, by, bz, bnames = [], [], [], []
    for b in defender_batteries:
        cx, cy, cz = lat_lon_to_cartesian(b["lat"], b["lon"], alt_km=15.0, radius=R)
        bx.append(cx)
        by.append(cy)
        bz.append(cz)
        bnames.append(f"🛡️ Battery: {b['name']} ({b.get('system', 'IAMD')})")

    fig.add_trace(go.Scatter3d(
        x=bx, y=by, z=bz,
        mode="markers+text",
        name="Defender IAMD Batteries",
        marker=dict(size=8, color="#00ff88", symbol="diamond", line=dict(color="#003322", width=1.5)),
        text=[b["name"][:18] for b in defender_batteries],
        textposition="top center",
        textfont=dict(color="#00ff88", size=9.5),
        hovertext=bnames,
        hoverinfo="text"
    ))

    # 8. 3D Radar Engagement Domes over Defender Batteries
    if show_wez_domes:
        for b in defender_batteries:
            b_lat, b_lon = b["lat"], b["lon"]
            wez_km = b.get("wez_radius_km", 70.0) * altitude_scale
            # Construct wireframe concentric dome rings
            for ring_frac in [0.4, 0.7, 1.0]:
                ring_rad_km = wez_km * ring_frac
                ang_deg = (ring_rad_km / EARTH_RADIUS_KM) * (180.0 / math.pi)
                ring_alt = (wez_km * math.sqrt(max(0.0, 1.0 - ring_frac ** 2))) * 0.4
                ring_x, ring_y, ring_z = [], [], []

                for azimuth in np.linspace(0, 2 * np.pi, 24):
                    d_lat = ang_deg * math.cos(azimuth)
                    d_lon = (ang_deg * math.sin(azimuth)) / max(0.2, math.cos(math.radians(b_lat)))
                    rx, ry, rz = lat_lon_to_cartesian(b_lat + d_lat, b_lon + d_lon, alt_km=ring_alt, radius=R)
                    ring_x.append(rx)
                    ring_y.append(ry)
                    ring_z.append(rz)

                fig.add_trace(go.Scatter3d(
                    x=ring_x, y=ring_y, z=ring_z,
                    mode="lines",
                    line=dict(color="#00ff88", width=1.5),
                    opacity=0.35,
                    hoverinfo="none",
                    showlegend=False
                ))

    # 9. 3D Suborbital Parabolic Arcs Rising Off Earth Surface
    launch_dict = {s["id"]: s for s in launch_sites}
    target_dict = {t["id"]: t for t in target_assets}
    battery_dict = {b["id"]: b for b in defender_batteries}
    trajectories = theater.get("threat_trajectories", [])

    color_threat_3d = {
        "ballistic": "#ff3344",
        "quasi-ballistic": "#ff3344",
        "mrbm": "#ff2244",
        "icbm": "#ff0033",
        "hypersonic": "#ff00cc",
        "cruise": "#ff9900",
        "drone": "#ffea00"
    }

    for threat in trajectories:
        t_id = threat["threat_id"]
        t_type = threat.get("threat_type", "ballistic").lower()
        l_site = launch_dict.get(threat["launch_site_id"])
        tgt = target_dict.get(threat["target_id"])
        bat = battery_dict.get(threat["assigned_battery_id"])

        if not l_site or not tgt:
            continue

        waypoints = generate_trajectory_waypoints(
            l_site["lat"], l_site["lon"], tgt["lat"], tgt["lon"],
            threat_type=t_type,
            apogee_km=threat.get("apogee_km", 75.0),
            n_points=50
        )

        arc_x, arc_y, arc_z = [], [], []
        for wp in waypoints:
            scaled_alt = wp["alt_km"] * altitude_scale
            cx, cy, cz = lat_lon_to_cartesian(wp["lat"], wp["lon"], alt_km=scaled_alt, radius=R)
            arc_x.append(cx)
            arc_y.append(cy)
            arc_z.append(cz)

        line_col = color_threat_3d.get(t_type, "#ff4444")
        fig.add_trace(go.Scatter3d(
            x=arc_x, y=arc_y, z=arc_z,
            mode="lines",
            name=f"3D Arc: {threat.get('threat_name', t_id)}",
            line=dict(color=line_col, width=4.0),
            hoverinfo="name"
        ))

        # 10. 3D Intercept Detonation Burst & Interceptor Arc
        if show_bursts and threat.get("status") == "INTERCEPTED":
            int_frac = threat.get("intercept_fraction", 0.75)
            int_lat, int_lon = great_circle_intermediate_point(
                l_site["lat"], l_site["lon"], tgt["lat"], tgt["lon"], int_frac
            )
            int_alt_scaled = threat.get("intercept_alt_km", 30.0) * altitude_scale
            bx_int, by_int, bz_int = lat_lon_to_cartesian(int_lat, int_lon, alt_km=int_alt_scaled, radius=R)

            # 3D Burst Marker
            cpa_m = threat.get("intercept_cpa_m", 0.5)
            fig.add_trace(go.Scatter3d(
                x=[bx_int], y=[by_int], z=[bz_int],
                mode="markers+text",
                name="3D Kinetic Intercept Burst",
                marker=dict(size=11, color="#ffff00", symbol="diamond", line=dict(color="#ff3300", width=2)),
                text=[f"💥 INTERCEPT: {threat.get('threat_name', t_id)[:16]}"],
                textposition="top center",
                textfont=dict(color="#ffff00", size=10, family="monospace"),
                hovertext=f"💥 Kinetic Intercept Point<br>Threat: {threat.get('threat_name', t_id)}<br>CPA Miss: {cpa_m:.2f} m",
                hoverinfo="text"
            ))

            # Interceptor Vector from Battery to Intercept Point
            if bat:
                bat_x, bat_y, bat_z = lat_lon_to_cartesian(bat["lat"], bat["lon"], alt_km=10.0, radius=R)
                fig.add_trace(go.Scatter3d(
                    x=[bat_x, bx_int],
                    y=[bat_y, by_int],
                    z=[bat_z, bz_int],
                    mode="lines",
                    line=dict(color="#00e5ff", width=2.8, dash="dash"),
                    hoverinfo="none",
                    showlegend=False
                ))

    # Calculate Camera Orientation Centered on Theater
    rad_lat = math.radians(center_lat)
    rad_lon = math.radians(center_lon)
    cam_dist = 1.95 if theater_key != "conus_homeland" else 2.3
    eye_x = cam_dist * math.cos(rad_lat) * math.cos(rad_lon)
    eye_y = cam_dist * math.cos(rad_lat) * math.sin(rad_lon)
    eye_z = cam_dist * math.sin(rad_lat)

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"<b>3D Digital Globe Command HUD: {theater['name']}</b><br>"
                 f"<sup>Exo-Atmospheric Suborbital Arcs, Radar WEZ Domes & Kinetic Interceptions (Altitude Scale: {altitude_scale:.1f}x)</sup>",
            font=dict(size=14, color="#ffffff")
        ),
        scene=dict(
            xaxis=dict(visible=False, showgrid=False, zeroline=False),
            yaxis=dict(visible=False, showgrid=False, zeroline=False),
            zaxis=dict(visible=False, showgrid=False, zeroline=False),
            bgcolor="#050811",
            camera=dict(
                eye=dict(x=eye_x, y=eye_y, z=eye_z),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            ),
            aspectmode="cube"
        ),
        paper_bgcolor="#050811",
        plot_bgcolor="#050811",
        legend=dict(
            font=dict(color="#ffffff", size=10),
            bgcolor="#0d1117",
            bordercolor="#30363d",
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=65, b=10),
        height=height
    )

    return fig


# ==============================================================================
# 8. HIGH-LEVEL UNIFIED DASH VIEW CONTAINER & MODE TOGGLE
# ==============================================================================

def build_map_views_container(
    theater_key: str = "eastern_europe",
    default_mode: str = "2d"
) -> html.Div:
    """
    Construct the unified Dashboard component layout integrating:
    - Theater Quick-Jump Selector Dropdown
    - View Mode Switcher: 2D Tactical Map (dash-leaflet) vs. 3D Digital Globe (Plotly 3D)
    - Interactive Layer Filters (Radar WEZ, Interceptors, Detonation Bursts)
    - Container for 2D Map and 3D Globe with dynamic toggle support
    - Altitude Profile Chart container
    - Real-Time Tactical Status HUD Badges
    """
    theater_options = [
        {"label": f"🌍 {data['name']}", "value": key}
        for key, data in THEATER_PRESETS.items()
    ]

    is_2d = default_mode == "2d"

    # Status KPI calculations for initial view
    theater = THEATER_PRESETS.get(theater_key, THEATER_PRESETS["eastern_europe"])
    trajectories = theater.get("threat_trajectories", [])
    n_threats = len(trajectories)
    n_intercepts = sum(1 for t in trajectories if t.get("status") == "INTERCEPTED")
    n_leakers = sum(1 for t in trajectories if t.get("status") == "IMPACT")
    fleet_pkill = np.mean([t.get("p_kill", 0.95) for t in trajectories]) * 100.0 if trajectories else 96.0

    return html.Div([
        # 1. Top Control Toolbar
        html.Div([
            html.Div([
                html.Label("OPERATIONAL THEATER QUICK-JUMP:", style={"fontSize": "11px", "color": "#8b949e", "fontWeight": "bold", "marginBottom": "4px", "display": "block"}),
                dcc.Dropdown(
                    id="theater-selector",
                    options=theater_options,
                    value=theater_key,
                    clearable=False,
                    style={"backgroundColor": "#161b22", "color": "#000000", "minWidth": "280px", "fontSize": "13px"}
                )
            ], style={"marginRight": "20px"}),

            html.Div([
                html.Label("VISUALIZATION MODE TOGGLE:", style={"fontSize": "11px", "color": "#8b949e", "fontWeight": "bold", "marginBottom": "4px", "display": "block"}),
                dcc.RadioItems(
                    id="view-mode-toggle",
                    options=[
                        {"label": " 🛰️ 2D Tactical Map (Leaflet) ", "value": "2d"},
                        {"label": " 🌐 3D Digital Globe (Plotly) ", "value": "3d"}
                    ],
                    value=default_mode,
                    inline=True,
                    style={"color": "#ffffff", "fontSize": "13px", "paddingTop": "6px"}
                )
            ], style={"marginRight": "20px"}),

            html.Div([
                html.Label("TACTICAL OVERLAYS:", style={"fontSize": "11px", "color": "#8b949e", "fontWeight": "bold", "marginBottom": "4px", "display": "block"}),
                dcc.Checklist(
                    id="map-layer-toggles",
                    options=[
                        {"label": " Radar WEZ ", "value": "wez"},
                        {"label": " Interceptors ", "value": "interceptors"},
                        {"label": " Detonations ", "value": "bursts"}
                    ],
                    value=["wez", "interceptors", "bursts"],
                    inline=True,
                    style={"color": "#58a6ff", "fontSize": "12px", "paddingTop": "6px"}
                )
            ])
        ], style={
            "display": "flex",
            "flexWrap": "wrap",
            "alignItems": "center",
            "backgroundColor": "#161b22",
            "padding": "12px 18px",
            "borderRadius": "8px",
            "border": "1px solid #30363d",
            "marginBottom": "12px"
        }),

        # 2. Tactical Status HUD KPI Badges
        html.Div(id="tactical-status-hud", children=[
            html.Div([
                html.Span("ACTIVE THREATS: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{n_threats} Tracking", style={"color": "#ff3344", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #ff3344", "padding": "6px 14px", "borderRadius": "4px", "marginRight": "10px"}),

            html.Div([
                html.Span("KINETIC INTERCEPTS: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{n_intercepts} Confirmed", style={"color": "#00ff88", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #00ff88", "padding": "6px 14px", "borderRadius": "4px", "marginRight": "10px"}),

            html.Div([
                html.Span("LEAKER PENETRATIONS: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{n_leakers} Impacts", style={"color": "#ffea00", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #ffea00", "padding": "6px 14px", "borderRadius": "4px", "marginRight": "10px"}),

            html.Div([
                html.Span("SYSTEM-WIDE P_KILL: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{fleet_pkill:.1f}%", style={"color": "#00e5ff", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #00e5ff", "padding": "6px 14px", "borderRadius": "4px"})
        ], style={"display": "flex", "flexWrap": "wrap", "marginBottom": "12px"}),

        # 3. Viewport Containers for 2D Map vs 3D Globe
        html.Div(
            id="tactical-2d-viewport-container",
            children=[build_tactical_leaflet_map(theater_key=theater_key)],
            style={"display": "block" if is_2d else "none", "marginBottom": "16px"}
        ),

        html.Div(
            id="tactical-3d-viewport-container",
            children=[
                dcc.Graph(
                    id="tactical-3d-globe-graph",
                    figure=build_3d_globe_figure(theater_key=theater_key),
                    config={"displayModeBar": True, "responsive": True}
                )
            ],
            style={"display": "none" if is_2d else "block", "marginBottom": "16px"}
        ),

        # 4. Missilemap 2D Altitude Profile Section
        html.Div([
            html.Div([
                html.H4("🎯 MISSILEMAP 2D DOWNRANGE VS. ALTITUDE PROFILE", style={"color": "#ffffff", "margin": "0 0 6px 0", "fontSize": "15px"}),
                html.P("Simultaneous multi-variable flight profile depicting boost-phase burnout, peak apogee, interceptor climb vector, and kinetic interception geometry.", style={"color": "#8b949e", "fontSize": "12px", "margin": "0 0 10px 0"})
            ]),
            dcc.Graph(
                id="missilemap-altitude-profile-graph",
                figure=build_altitude_profile_figure(theater_key=theater_key, threat_index=0),
                config={"displayModeBar": True, "responsive": True}
            )
        ], style={
            "backgroundColor": "#161b22",
            "padding": "16px",
            "borderRadius": "8px",
            "border": "1px solid #30363d"
        })
    ], id="unified-map-views-container", style={"fontFamily": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif"})


# ==============================================================================
# 9. DASH CALLBACK REGISTRATION
# ==============================================================================

def register_map_callbacks(app) -> None:
    """Register all interactive callbacks for theater jumping, 2D/3D toggling, and overlays."""

    @app.callback(
        Output("tactical-2d-viewport-container", "style"),
        Output("tactical-3d-viewport-container", "style"),
        Input("view-mode-toggle", "value")
    )
    def toggle_view_mode(mode):
        if mode == "3d":
            return {"display": "none", "marginBottom": "16px"}, {"display": "block", "marginBottom": "16px"}
        return {"display": "block", "marginBottom": "16px"}, {"display": "none", "marginBottom": "16px"}

    @app.callback(
        Output("tactical-2d-viewport-container", "children"),
        Output("tactical-3d-globe-graph", "figure"),
        Output("missilemap-altitude-profile-graph", "figure"),
        Output("tactical-status-hud", "children"),
        Input("theater-selector", "value"),
        Input("map-layer-toggles", "value")
    )
    def update_theater_and_layers(selected_theater, active_layers):
        layers = active_layers or []
        show_wez = "wez" in layers
        show_interceptors = "interceptors" in layers
        show_bursts = "bursts" in layers

        # 1. Rebuild 2D Leaflet Map
        new_map = build_tactical_leaflet_map(
            theater_key=selected_theater,
            show_wez=show_wez,
            show_interceptors=show_interceptors,
            show_bursts=show_bursts
        )

        # 2. Rebuild 3D Globe Figure
        new_globe_fig = build_3d_globe_figure(
            theater_key=selected_theater,
            show_wez_domes=show_wez,
            show_bursts=show_bursts
        )

        # 3. Rebuild Altitude Profile Chart
        new_alt_fig = build_altitude_profile_figure(
            theater_key=selected_theater,
            threat_index=0
        )

        # 4. Rebuild Status HUD
        th_data = THEATER_PRESETS.get(selected_theater, THEATER_PRESETS["eastern_europe"])
        trajectories = th_data.get("threat_trajectories", [])
        n_threats = len(trajectories)
        n_intercepts = sum(1 for t in trajectories if t.get("status") == "INTERCEPTED")
        n_leakers = sum(1 for t in trajectories if t.get("status") == "IMPACT")
        fleet_pkill = np.mean([t.get("p_kill", 0.95) for t in trajectories]) * 100.0 if trajectories else 96.0

        new_hud = [
            html.Div([
                html.Span("ACTIVE THREATS: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{n_threats} Tracking", style={"color": "#ff3344", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #ff3344", "padding": "6px 14px", "borderRadius": "4px", "marginRight": "10px"}),

            html.Div([
                html.Span("KINETIC INTERCEPTS: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{n_intercepts} Confirmed", style={"color": "#00ff88", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #00ff88", "padding": "6px 14px", "borderRadius": "4px", "marginRight": "10px"}),

            html.Div([
                html.Span("LEAKER PENETRATIONS: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{n_leakers} Impacts", style={"color": "#ffea00", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #ffea00", "padding": "6px 14px", "borderRadius": "4px", "marginRight": "10px"}),

            html.Div([
                html.Span("SYSTEM-WIDE P_KILL: ", style={"color": "#8b949e", "fontSize": "11px"}),
                html.Span(f"{fleet_pkill:.1f}%", style={"color": "#00e5ff", "fontWeight": "bold", "fontSize": "13px"})
            ], style={"backgroundColor": "#0d1117", "border": "1px solid #00e5ff", "padding": "6px 14px", "borderRadius": "4px"})
        ]

        return [new_map], new_globe_fig, new_alt_fig, new_hud


# ==============================================================================
# 10. DIRECT DEMO EXECUTION
# ==============================================================================

if __name__ == "__main__":
    from dash import Dash

    demo_app = Dash(__name__)
    demo_app.title = "Tactical Map & Air Defense HUD"
    demo_app.layout = html.Div([
        html.Div([
            html.H2("🛰️ INTEGRATED AIR & MISSILE DEFENSE (IAMD) COMMAND HUD", style={"color": "#ffffff", "margin": "0 0 4px 0", "letterSpacing": "1px"}),
            html.P("Multi-Theater Tactical Command Visualizer: 2D Tactical Leaflet Map, 3D Digital Globe, and Missilemap Altitude Profiles", style={"color": "#8b949e", "margin": "0 0 16px 0", "fontSize": "13px"})
        ], style={"padding": "16px 20px 0 20px"}),
        build_map_views_container()
    ], style={"backgroundColor": "#0d1117", "minHeight": "100vh", "padding": "10px"})

    register_map_callbacks(demo_app)
    print("Starting tactical map demo on http://127.0.0.1:8050 ...")
    demo_app.run(debug=True, port=8050)
