#!/usr/bin/env python3
"""
================================================================================
IAMD GLOBAL DEFENSE SIMULATOR: STANDALONE DESKTOP APPLICATION
File: desktop_gui.py
================================================================================
Standalone native desktop GUI application using CustomTkinter and TkinterMapView.
Deployable directly from Python with zero browser, web server, or cloud dependencies.

Key Features:
1. 100% Open-Source Map Engine:
   - Uses zero-API-key tile providers:
     * CartoDB Dark Matter (tactical dark military theme)
     * OpenStreetMap Standard (worldwide street/terrain baseline)
     * OpenTopoMap (topographical elevation contours)
   - Zero API keys or proprietary tokens required.
2. Interactive Tactical Map:
   - Drag-and-drop & click-to-place markers for Attacker Launch Sites, Defender
     Batteries, and Defended Targets (HVAs).
   - Dynamic geodesic flight paths connecting launch sites to targets.
   - Real-time radar Weapon Engagement Zone (WEZ) circles around defender batteries.
   - Live missile / drone position markers tracking along trajectories.
   - Kinetic intercept detonation starbursts (gold) and target impact bursts (red).
3. Live Telemetry HUD Panel:
   - Real-time Mach speedometer and maximum Mach rating.
   - Dynamic altitude indicator (km / meters) and atmospheric zone classification
     (Troposphere, Stratosphere, Mesosphere, Karman / Exo-atmospheric).
   - Flight phase badges (BOOST, MIDCOURSE, GLIDE, TERMINAL, LOITER, INTERCEPT).
   - Progress bar, downrange distance, remaining distance, and ETOF countdown.
   - Interception assessment (assigned battery, CPA miss distance, P_kill, hit/miss).
   - Threat tracking matrix table with clickable threat selection.
4. Playback Transport Controls:
   - Play (▶), Pause (⏸), Step (+1s ⏭), and Reset (⏮).
   - Interactive timeline scrubber slider.
   - Simulation speed multiplier (0.5x, 1x, 2x, 5x, 10x).
   - 10% F-22 / F-35 air-launch easter egg stealth strike trigger.
================================================================================
"""

import math
import os
import random
import sys
import time
from typing import Dict, List, Optional, Tuple, Any

import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk
import tkintermapview

# Domain models from project
try:
    import app
    import catalog
    import defense_system
    import map_views
    import physics_engine
    import telemetry
except ImportError:
    # If launched from another directory, add current folder to sys.path
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    if CURRENT_DIR not in sys.path:
        sys.path.insert(0, CURRENT_DIR)
    import app
    import catalog
    import defense_system
    import map_views
    import physics_engine
    import telemetry


# ==============================================================================
# 1. OPEN-SOURCE ZERO-API-KEY TILE SERVERS
# ==============================================================================

def _get_carto_api_key() -> str:
    """Safely load CARTO API key from environment variable or git-ignored .env file."""
    key = os.environ.get("CARTO_API_KEY", "").strip()
    if not key:
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("CARTO_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
    return key


_carto_key = _get_carto_api_key()
_carto_param = f"?key={_carto_key}" if _carto_key else ""

OPEN_SOURCE_TILE_SERVERS = {
    "CartoDB Dark Matter (Tactical)": {
        "url": f"https://a.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png{_carto_param}" if _carto_key else "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "tile_size": 256,
        "max_zoom": 19,
        "attribution": "CARTO / OpenStreetMap",
    },
    "OpenStreetMap (Standard)": {
        "url": "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "tile_size": 256,
        "max_zoom": 19,
        "attribution": "OpenStreetMap Contributors",
    },
    "OpenTopoMap (Topographic)": {
        "url": "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
        "tile_size": 256,
        "max_zoom": 17,
        "attribution": "OpenTopoMap / OpenStreetMap",
    },
}

DEFAULT_TILE_KEY = "CartoDB Dark Matter (Tactical)"

EARTH_RADIUS_KM = 6371.0


# ==============================================================================
# 2. GEODESIC & SPATIAL UTILITIES
# ==============================================================================

def calculate_circle_points(lat: float, lon: float, radius_km: float, num_points: int = 36) -> List[Tuple[float, float]]:
    """Compute circular boundary polygon points at radius_km around (lat, lon) on WGS84 sphere."""
    points: List[Tuple[float, float]] = []
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    d_r = radius_km / EARTH_RADIUS_KM

    for i in range(num_points + 1):
        bearing = math.radians(i * (360.0 / num_points))
        p_lat = math.asin(
            math.sin(lat_r) * math.cos(d_r) +
            math.cos(lat_r) * math.sin(d_r) * math.cos(bearing)
        )
        p_lon = lon_r + math.atan2(
            math.sin(bearing) * math.sin(d_r) * math.cos(lat_r),
            math.cos(d_r) - math.sin(lat_r) * math.sin(p_lat)
        )
        points.append((math.degrees(p_lat), math.degrees(p_lon)))
    return points


def canvas_to_coords(map_widget: tkintermapview.TkinterMapView, canvas_x: int, canvas_y: int) -> Tuple[float, float]:
    """Robust conversion of canvas pixel coordinates to decimal (lat, lon)."""
    w = map_widget.canvas.winfo_width()
    h = map_widget.canvas.winfo_height()
    if w <= 1:
        w = map_widget.width
    if h <= 1:
        h = map_widget.height

    rel_x = canvas_x / float(w)
    rel_y = canvas_y / float(h)

    tile_x = map_widget.upper_left_tile_pos[0] + (map_widget.lower_right_tile_pos[0] - map_widget.upper_left_tile_pos[0]) * rel_x
    tile_y = map_widget.upper_left_tile_pos[1] + (map_widget.lower_right_tile_pos[1] - map_widget.upper_left_tile_pos[1]) * rel_y

    return tkintermapview.osm_to_decimal(tile_x, tile_y, round(map_widget.zoom))


def get_atmospheric_zone(alt_km: float) -> Tuple[str, str]:
    """Returns atmospheric zone name and badge hex color for altitude."""
    if alt_km < 12.0:
        return "TROPOSPHERE (High Drag)", "#3b82f6"
    elif alt_km < 50.0:
        return "STRATOSPHERE (Midcourse)", "#06b6d4"
    elif alt_km < 85.0:
        return "MESOSPHERE (Hypersonic Glide)", "#8b5cf6"
    else:
        return "EXO-ATMOSPHERIC (Karman / Space)", "#ec4899"


# ==============================================================================
# 3. TACTICAL SIMULATION ENGINE (STANDALONE DESKTOP)
# ==============================================================================

class TacticalSimEngine:
    """Manages multi-theater scenario data, kinematic timelines, and track telemetry."""

    def __init__(self, theater_key: str = "eastern_europe"):
        self.theater_key = theater_key
        self.sim_time_s = 0.0
        self.is_playing = False
        self.speed_multiplier = 1.0
        self.selected_track_id: Optional[str] = None
        self.easter_egg_data: Dict[str, Any] = {"active": False, "banner": ""}

        # Load theater scenario data
        self.load_theater(theater_key)

    def load_theater(self, theater_key: str):
        """Load scenario presets and theater geographic sites."""
        self.theater_key = theater_key
        self.sim_time_s = 0.0
        self.is_playing = False

        preset = app.SCENARIO_PRESETS.get(theater_key, app.SCENARIO_PRESETS["eastern_europe"])
        th_meta = map_views.THEATER_PRESETS.get(theater_key, map_views.THEATER_PRESETS["eastern_europe"])

        self.scenario_name = preset["name"]
        self.duration_s = float(preset.get("duration_s", 120.0))
        self.center = th_meta["center"]
        self.zoom = th_meta["zoom"]

        # Deep copies of sites so users can relocate/drag them independently
        self.attacker_launch_sites = [dict(s) for s in th_meta["attacker_launch_sites"]]
        self.defender_batteries = [dict(b) for b in th_meta["defender_batteries"]]
        self.target_assets = [dict(t) for t in th_meta["target_assets"]]

        # Deep copy of tracks
        self.tracks = [dict(tr) for tr in preset["tracks"]]

        if self.tracks:
            self.selected_track_id = self.tracks[0]["id"]
        else:
            self.selected_track_id = None

    def get_track_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        for tr in self.tracks:
            if tr["id"] == track_id:
                return tr
        return None

    def compute_all_telemetry(self, t_sec: float) -> List[Dict[str, Any]]:
        """Compute telemetries for all tracks at time t_sec."""
        results = []
        for tr in self.tracks:
            res = app.calculate_track_telemetry_at_time(tr, t_sec)
            results.append(res)
        return results

    def advance_time(self, dt_s: float):
        """Advance simulation clock by dt_s, clamped to [0, duration_s]."""
        self.sim_time_s = max(0.0, min(self.duration_s, self.sim_time_s + dt_s * self.speed_multiplier))
        if self.sim_time_s >= self.duration_s:
            self.is_playing = False

    def seek_time(self, t_s: float):
        """Jump simulation clock to t_s."""
        self.sim_time_s = max(0.0, min(self.duration_s, t_s))

    def reset(self):
        """Reset simulation clock to T+0."""
        self.sim_time_s = 0.0
        self.is_playing = False

    def move_site(self, site_id: str, new_lat: float, new_lon: float):
        """Update coordinates of a launcher, battery, or target, and adjust tracks accordingly."""
        # Check launchers
        for s in self.attacker_launch_sites:
            if s["id"] == site_id:
                s["lat"] = round(new_lat, 4)
                s["lon"] = round(new_lon, 4)
                # Update any tracks originating from this site
                for tr in self.tracks:
                    if tr.get("origin") == s["name"] or tr.get("launch_site_id") == site_id:
                        tr["launch_lat"] = s["lat"]
                        tr["launch_lon"] = s["lon"]
                        tr["range_km"] = round(map_views.haversine_distance_km(s["lat"], s["lon"], tr.get("target_lat", s["lat"]), tr.get("target_lon", s["lon"])), 1)
                return True

        # Check batteries
        for b in self.defender_batteries:
            if b["id"] == site_id:
                b["lat"] = round(new_lat, 4)
                b["lon"] = round(new_lon, 4)
                return True

        # Check targets
        for t in self.target_assets:
            if t["id"] == site_id:
                t["lat"] = round(new_lat, 4)
                t["lon"] = round(new_lon, 4)
                # Update any tracks targeting this site
                for tr in self.tracks:
                    if tr.get("target") == t["name"] or tr.get("target_id") == site_id:
                        tr["target_lat"] = t["lat"]
                        tr["target_lon"] = t["lon"]
                        tr["range_km"] = round(map_views.haversine_distance_km(tr.get("launch_lat", t["lat"]), tr.get("launch_lon", t["lon"]), t["lat"], t["lon"]), 1)
                return True

        return False

    def trigger_easter_egg(self, force: bool = False) -> Dict[str, Any]:
        """Rolls or forces the 10% F-22/F-35 stealth fighter air-launch easter egg."""
        if force:
            aircraft = random.choice(["F-22A Raptor", "F-35A Lightning II"])
            self.easter_egg_data = {
                "active": True,
                "aircraft": aircraft,
                "callsign": "RAPTOR-01 (94TH FS)" if "F-22" in aircraft else "LIGHTNING-11 (388TH FW)",
                "banner_text": f"AIR-LAUNCH DETECTED: {aircraft.upper()} STAND-OFF STRIKE INITIATED",
                "coords": [
                    (self.center[0] - 2.5, self.center[1] - 3.0),
                    (self.center[0] - 1.2, self.center[1] - 1.5),
                    (self.center[0], self.center[1]),
                ],
            }
        else:
            self.easter_egg_data = app.roll_easter_egg()
            if self.easter_egg_data.get("active"):
                self.easter_egg_data["banner_text"] = self.easter_egg_data.get("banner_text", "STEALTH FIGHTER AIR-LAUNCH DETECTED")
                # Ensure tuples for map rendering
                raw_coords = self.easter_egg_data.get("path_coords", [])
                self.easter_egg_data["coords"] = [(p[0], p[1]) for p in raw_coords]
        return self.easter_egg_data


# ==============================================================================
# 4. MAIN NATIVE DESKTOP GUI APPLICATION
# ==============================================================================

class TacticalDesktopApp:
    """
    Main Integrated Air & Missile Defense Desktop GUI Application.
    Combines TkinterMapView open-source mapping with live telemetry and transport controls.
    """

    def __init__(self, root: Optional[ctk.CTk] = None, headless: bool = False, theater_key: str = "eastern_europe"):
        self.headless = headless
        self.sim_engine = TacticalSimEngine(theater_key)

        # Tkinter / CustomTkinter Setup
        if root is None:
            ctk.set_appearance_mode("Dark")
            ctk.set_default_color_theme("dark-blue")
            self.root = ctk.CTk()
            self.root.title("IAMD GLOBAL DEFENSE SIMULATOR - TACTICAL COMMAND & CONTROL")
            self.root.geometry("1480x920")
            self.root.minsize(1100, 720)
            self._own_root = True
        else:
            self.root = root
            self._own_root = False

        if self.headless:
            self.root.withdraw()

        # State tracking for drag-and-drop & placement
        self.active_marker_obj: Optional[Any] = None
        self.active_site_dict: Optional[Dict[str, Any]] = None
        self.placement_mode: Optional[str] = None  # None, "attacker", "defender", "target", "relocate"
        self.is_dragging = False

        # Visual map element references
        self.map_site_markers: Dict[str, Any] = {}
        self.map_threat_markers: Dict[str, Any] = {}
        self.map_trajectory_paths: Dict[str, Any] = {}
        self.map_interceptor_paths: Dict[str, Any] = {}
        self.map_interceptor_markers: Dict[str, Any] = {}
        self.map_wez_polygons: Dict[str, Any] = {}
        self.map_detonation_markers: Dict[str, Any] = {}
        self.map_stealth_path: Optional[Any] = None

        # Build UI layout
        self._build_ui()

        # Initialize tactical map with open-source tiles
        self._setup_map()

        # Initial render of scenario entities
        self._render_theater_scenario()

        # Start simulation loop if not headless
        self._last_tick_time = time.time()
        if not self.headless:
            self.root.after(50, self._sim_tick)

    # --------------------------------------------------------------------------
    # UI CONSTRUCTION
    # --------------------------------------------------------------------------

    def _build_ui(self):
        """Construct the top navbar, central map, telemetry sidebar, and transport bar."""
        # Main layout container
        self.main_container = ctk.CTkFrame(self.root, fg_color="#070c14", corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        # 1. Top Navbar
        self._build_top_navbar()

        # 2. Middle Body (Map on left, Telemetry HUD on right)
        self.body_frame = ctk.CTkFrame(self.main_container, fg_color="#070c14", corner_radius=0)
        self.body_frame.pack(fill="both", expand=True, padx=8, pady=4)

        # Map Area (Weight 3)
        self.map_container = ctk.CTkFrame(self.body_frame, fg_color="#0b1320", corner_radius=8, border_width=1, border_color="#1e293b")
        self.map_container.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Telemetry HUD Sidebar (Weight 1)
        self.hud_sidebar = ctk.CTkFrame(self.body_frame, width=440, fg_color="#0b1320", corner_radius=8, border_width=1, border_color="#1e293b")
        self.hud_sidebar.pack(side="right", fill="both", padx=(6, 0))
        self.hud_sidebar.pack_propagate(False)

        self._build_hud_sidebar()

        # 3. Bottom Playback & Transport Controls
        self._build_bottom_transport_bar()

    def _build_top_navbar(self):
        """Build top tactical command navbar."""
        self.navbar = ctk.CTkFrame(self.main_container, height=54, fg_color="#0b1320", corner_radius=0, border_width=1, border_color="#1e293b")
        self.navbar.pack(fill="x", padx=0, pady=0)

        # Brand / Title
        title_label = ctk.CTkLabel(
            self.navbar,
            text="⚔ IAMD COMMAND & CONTROL",
            font=ctk.CTkFont(family="Courier", size=16, weight="bold"),
            text_color="#00f0ff"
        )
        title_label.pack(side="left", padx=16)

        # Theater Selector
        theater_lbl = ctk.CTkLabel(self.navbar, text="THEATER:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8")
        theater_lbl.pack(side="left", padx=(10, 4))

        self.theater_menu = ctk.CTkOptionMenu(
            self.navbar,
            values=[
                "Eastern Europe / Black Sea",
                "Persian Gulf / Red Sea",
                "Taiwan Strait / Indo-Pacific",
                "CONUS Homeland"
            ],
            command=self._on_theater_selected,
            fg_color="#1e293b",
            button_color="#334155",
            width=230,
            font=ctk.CTkFont(size=12)
        )
        self.theater_menu.pack(side="left", padx=4)

        # Tile Server Selector (Open-Source, Zero-API-Key)
        tile_lbl = ctk.CTkLabel(self.navbar, text="MAP ENGINE:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8")
        tile_lbl.pack(side="left", padx=(16, 4))

        self.tile_menu = ctk.CTkOptionMenu(
            self.navbar,
            values=list(OPEN_SOURCE_TILE_SERVERS.keys()),
            command=self._on_tile_server_selected,
            fg_color="#1e293b",
            button_color="#334155",
            width=240,
            font=ctk.CTkFont(size=12)
        )
        self.tile_menu.pack(side="left", padx=4)

        # Strike Launch Button (rolls 10% easter egg stealth strike)
        self.btn_strike = ctk.CTkButton(
            self.navbar,
            text="🚀 LAUNCH STRIKE RAID",
            fg_color="#b91c1c",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_launch_strike_clicked,
            width=180
        )
        self.btn_strike.pack(side="right", padx=16)

        # System Status Indicator
        self.lbl_system_status = ctk.CTkLabel(
            self.navbar,
            text="● DEFENSE SCREEN ACTIVE",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color="#00e676"
        )
        self.lbl_system_status.pack(side="right", padx=16)

    def _build_hud_sidebar(self):
        """Build military tactical telemetry HUD sidebar."""
        # HUD Title
        hud_header = ctk.CTkFrame(self.hud_sidebar, height=40, fg_color="#111c2e", corner_radius=6)
        hud_header.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            hud_header,
            text="TACTICAL TELEMETRY HUD",
            font=ctk.CTkFont(family="Courier", size=14, weight="bold"),
            text_color="#00f0ff"
        ).pack(side="left", padx=10, pady=6)

        # Easter Egg Banner (hidden by default)
        self.easter_banner_frame = ctk.CTkFrame(self.hud_sidebar, fg_color="#3b1219", corner_radius=6, border_width=1, border_color="#ef4444")
        self.easter_banner_lbl = ctk.CTkLabel(
            self.easter_banner_frame,
            text="AIR-LAUNCH DETECTED: F-22A RAPTOR WEAPON RELEASE",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color="#fca5a5",
            wraplength=400
        )
        self.easter_banner_lbl.pack(padx=8, pady=6)

        # Active Threat Selector
        sel_frame = ctk.CTkFrame(self.hud_sidebar, fg_color="#070c14", corner_radius=6)
        sel_frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(sel_frame, text="TRACK MONITOR:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left", padx=8, pady=6)

        track_options = [f"{t['id']}: {t['name']}" for t in self.sim_engine.tracks]
        self.track_selector = ctk.CTkOptionMenu(
            sel_frame,
            values=track_options if track_options else ["None"],
            command=self._on_track_selected,
            fg_color="#1e293b",
            button_color="#334155",
            width=260,
            font=ctk.CTkFont(size=11)
        )
        self.track_selector.pack(side="right", padx=8, pady=6)

        # Scrollable Telemetry Cards Frame
        self.hud_scroll = ctk.CTkScrollableFrame(self.hud_sidebar, fg_color="#070c14", corner_radius=6)
        self.hud_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # --- Card 1: Threat Identification ---
        self.card_threat = ctk.CTkFrame(self.hud_scroll, fg_color="#0f172a", corner_radius=6, border_width=1, border_color="#1e293b")
        self.card_threat.pack(fill="x", pady=4)

        self.lbl_threat_name = ctk.CTkLabel(self.card_threat, text="9K720 Iskander-M", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ff4455")
        self.lbl_threat_name.pack(anchor="w", padx=10, pady=(6, 2))

        self.lbl_threat_details = ctk.CTkLabel(
            self.card_threat,
            text="Type: Quasi-Ballistic | Faction: Aggressor Strike Force\nWarhead: 480 kg HE Blast Frag | Guidance: GLONASS/DSMAC",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        self.lbl_threat_details.pack(anchor="w", padx=10, pady=(0, 6))

        # --- Card 2: Mach & Kinematics Gauge ---
        self.card_mach = ctk.CTkFrame(self.hud_scroll, fg_color="#0f172a", corner_radius=6, border_width=1, border_color="#1e293b")
        self.card_mach.pack(fill="x", pady=4)

        mach_hdr = ctk.CTkFrame(self.card_mach, fg_color="transparent")
        mach_hdr.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(mach_hdr, text="VELOCITY GAUGE", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left")
        self.lbl_mach_val = ctk.CTkLabel(mach_hdr, text="MACH 6.20", font=ctk.CTkFont(family="Courier", size=14, weight="bold"), text_color="#00f0ff")
        self.lbl_mach_val.pack(side="right")

        self.mach_prog_bar = ctk.CTkProgressBar(self.card_mach, progress_color="#00f0ff", fg_color="#1e293b", height=10)
        self.mach_prog_bar.set(0.62)
        self.mach_prog_bar.pack(fill="x", padx=10, pady=4)

        self.lbl_speed_subtext = ctk.CTkLabel(self.card_mach, text="1,953 m/s | 7,030 km/h (Max: Mach 6.2)", font=ctk.CTkFont(size=11), text_color="#cbd5e1")
        self.lbl_speed_subtext.pack(anchor="w", padx=10, pady=(0, 6))

        # --- Card 3: Altitude & Atmospheric Stratification ---
        self.card_alt = ctk.CTkFrame(self.hud_scroll, fg_color="#0f172a", corner_radius=6, border_width=1, border_color="#1e293b")
        self.card_alt.pack(fill="x", pady=4)

        alt_hdr = ctk.CTkFrame(self.card_alt, fg_color="transparent")
        alt_hdr.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(alt_hdr, text="ALTITUDE METER", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left")
        self.lbl_alt_val = ctk.CTkLabel(alt_hdr, text="48.5 km", font=ctk.CTkFont(family="Courier", size=14, weight="bold"), text_color="#ffb300")
        self.lbl_alt_val.pack(side="right")

        self.lbl_alt_zone = ctk.CTkLabel(
            self.card_alt,
            text="● STRATOSPHERE (Midcourse)",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color="#06b6d4"
        )
        self.lbl_alt_zone.pack(anchor="w", padx=10, pady=2)

        self.lbl_alt_subtext = ctk.CTkLabel(self.card_alt, text="Apogee: 50.0 km | Vertical Climb: +120 m/s", font=ctk.CTkFont(size=11), text_color="#cbd5e1")
        self.lbl_alt_subtext.pack(anchor="w", padx=10, pady=(0, 6))

        # --- Card 4: Flight Phase & Status ---
        self.card_phase = ctk.CTkFrame(self.hud_scroll, fg_color="#0f172a", corner_radius=6, border_width=1, border_color="#1e293b")
        self.card_phase.pack(fill="x", pady=4)

        phase_row = ctk.CTkFrame(self.card_phase, fg_color="transparent")
        phase_row.pack(fill="x", padx=10, pady=6)

        self.lbl_phase_badge = ctk.CTkLabel(
            phase_row,
            text="PHASE: MIDCOURSE",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            fg_color="#0369a1",
            text_color="#e0f2fe",
            corner_radius=4,
            padx=8,
            pady=3
        )
        self.lbl_phase_badge.pack(side="left", padx=(0, 6))

        self.lbl_status_badge = ctk.CTkLabel(
            phase_row,
            text="IN FLIGHT",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            fg_color="#15803d",
            text_color="#dcfce7",
            corner_radius=4,
            padx=8,
            pady=3
        )
        self.lbl_status_badge.pack(side="left")

        # Flight progress bar
        prog_row = ctk.CTkFrame(self.card_phase, fg_color="transparent")
        prog_row.pack(fill="x", padx=10, pady=(2, 6))

        ctk.CTkLabel(prog_row, text="FLIGHT PROGRESS:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left")
        self.lbl_progress_pct = ctk.CTkLabel(prog_row, text="65.4%", font=ctk.CTkFont(family="Courier", size=11, weight="bold"), text_color="#00f0ff")
        self.lbl_progress_pct.pack(side="right")

        self.prog_bar = ctk.CTkProgressBar(self.card_phase, progress_color="#00e676", fg_color="#1e293b", height=8)
        self.prog_bar.set(0.654)
        self.prog_bar.pack(fill="x", padx=10, pady=(0, 6))

        # --- Card 5: Distance & Mission Clock ---
        self.card_distance = ctk.CTkFrame(self.hud_scroll, fg_color="#0f172a", corner_radius=6, border_width=1, border_color="#1e293b")
        self.card_distance.pack(fill="x", pady=4)

        self.lbl_distance_text = ctk.CTkLabel(
            self.card_distance,
            text="Traveled: 314.0 km / 480.0 km\nRemaining: 166.0 km | ETOF: 95.0s (ETA: 32.8s)",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color="#cbd5e1",
            justify="left"
        )
        self.lbl_distance_text.pack(anchor="w", padx=10, pady=6)

        # --- Card 6: Intercept & Defense Assessment ---
        self.card_intercept = ctk.CTkFrame(self.hud_scroll, fg_color="#0f172a", corner_radius=6, border_width=1, border_color="#1e293b")
        self.card_intercept.pack(fill="x", pady=4)

        ctk.CTkLabel(self.card_intercept, text="ENGAGEMENT SOLUTION", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(anchor="w", padx=10, pady=(6, 2))

        self.lbl_intercept_solution = ctk.CTkLabel(
            self.card_intercept,
            text="Assigned Battery: Patriot PAC-3 CRI (Bravo)\nCPA Miss Distance: 1.25 m | Alt: 24.5 km\nP_kill: 94.2% | Outcome: PENDING",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color="#38bdf8",
            justify="left"
        )
        self.lbl_intercept_solution.pack(anchor="w", padx=10, pady=(0, 6))

        # --- Card 7: Marker Drag & Placement Controller ---
        self.card_placement = ctk.CTkFrame(self.hud_scroll, fg_color="#111c2e", corner_radius=6, border_width=1, border_color="#334155")
        self.card_placement.pack(fill="x", pady=4)

        ctk.CTkLabel(
            self.card_placement,
            text="MARKER DRAG & PLACEMENT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f59e0b"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        self.lbl_selected_marker_info = ctk.CTkLabel(
            self.card_placement,
            text="Active Unit: None\n(Click/drag markers on map to reposition)",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        self.lbl_selected_marker_info.pack(anchor="w", padx=10, pady=2)

        # Action buttons for placement
        btn_grid = ctk.CTkFrame(self.card_placement, fg_color="transparent")
        btn_grid.pack(fill="x", padx=10, pady=(2, 6))

        self.btn_place_relocate = ctk.CTkButton(
            btn_grid,
            text="Relocate Unit",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._on_btn_relocate_clicked,
            width=90,
            height=26
        )
        self.btn_place_relocate.grid(row=0, column=0, padx=2, pady=2)

        self.btn_add_attacker = ctk.CTkButton(
            btn_grid,
            text="+ Attacker",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#991b1b",
            hover_color="#b91c1c",
            command=lambda: self._set_placement_mode("attacker"),
            width=85,
            height=26
        )
        self.btn_add_attacker.grid(row=0, column=1, padx=2, pady=2)

        self.btn_add_defender = ctk.CTkButton(
            btn_grid,
            text="+ Battery",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#166534",
            hover_color="#15803d",
            command=lambda: self._set_placement_mode("defender"),
            width=85,
            height=26
        )
        self.btn_add_defender.grid(row=0, column=2, padx=2, pady=2)

        self.btn_add_target = ctk.CTkButton(
            btn_grid,
            text="+ Target",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#854d0e",
            hover_color="#a16207",
            command=lambda: self._set_placement_mode("target"),
            width=85,
            height=26
        )
        self.btn_add_target.grid(row=0, column=3, padx=2, pady=2)

    def _build_bottom_transport_bar(self):
        """Build playback transport controls bar."""
        self.transport_bar = ctk.CTkFrame(self.main_container, height=64, fg_color="#0b1320", corner_radius=0, border_width=1, border_color="#1e293b")
        self.transport_bar.pack(fill="x", padx=0, pady=0)

        # Left Transport Buttons
        btn_frame = ctk.CTkFrame(self.transport_bar, fg_color="transparent")
        btn_frame.pack(side="left", padx=12, pady=8)

        self.btn_reset = ctk.CTkButton(btn_frame, text="⏮ Reset", width=70, fg_color="#334155", hover_color="#475569", command=self._on_btn_reset_clicked)
        self.btn_reset.pack(side="left", padx=3)

        self.btn_play_pause = ctk.CTkButton(btn_frame, text="▶ Play", width=80, fg_color="#0284c7", hover_color="#0369a1", font=ctk.CTkFont(weight="bold"), command=self._on_btn_play_clicked)
        self.btn_play_pause.pack(side="left", padx=3)

        self.btn_step = ctk.CTkButton(btn_frame, text="⏭ Step (+1s)", width=95, fg_color="#334155", hover_color="#475569", command=self._on_btn_step_clicked)
        self.btn_step.pack(side="left", padx=3)

        # Center Timeline Scrubber
        slider_frame = ctk.CTkFrame(self.transport_bar, fg_color="transparent")
        slider_frame.pack(side="left", fill="x", expand=True, padx=16, pady=8)

        clock_row = ctk.CTkFrame(slider_frame, fg_color="transparent")
        clock_row.pack(fill="x")

        self.lbl_clock = ctk.CTkLabel(
            clock_row,
            text="SIM CLOCK: T+00:00.0s / 02:00.0s",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color="#00f0ff"
        )
        self.lbl_clock.pack(side="left")

        self.lbl_mode_status = ctk.CTkLabel(
            clock_row,
            text="MODE: READY",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color="#10b981"
        )
        self.lbl_mode_status.pack(side="right")

        self.timeline_slider = ctk.CTkSlider(
            slider_frame,
            from_=0.0,
            to=self.sim_engine.duration_s,
            number_of_steps=120,
            command=self._on_slider_scrubbed,
            progress_color="#00f0ff",
            button_color="#38bdf8",
            button_hover_color="#0284c7"
        )
        self.timeline_slider.set(0.0)
        self.timeline_slider.pack(fill="x", pady=(2, 0))

        # Right Controls: Speed Multiplier and Stealth Strike Easter Egg
        speed_frame = ctk.CTkFrame(self.transport_bar, fg_color="transparent")
        speed_frame.pack(side="right", padx=12, pady=8)

        ctk.CTkLabel(speed_frame, text="SPEED:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(0, 4))

        self.speed_menu = ctk.CTkOptionMenu(
            speed_frame,
            values=["0.5x", "1.0x", "2.0x", "5.0x", "10.0x"],
            command=self._on_speed_selected,
            fg_color="#1e293b",
            button_color="#334155",
            width=80,
            font=ctk.CTkFont(size=11)
        )
        self.speed_menu.set("1.0x")
        self.speed_menu.pack(side="left", padx=4)

        self.btn_easter = ctk.CTkButton(
            speed_frame,
            text="🦅 F-22/F-35 STRIKE",
            fg_color="#4338ca",
            hover_color="#4f46e5",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._trigger_air_launch(force=True),
            width=140
        )
        self.btn_easter.pack(side="left", padx=(8, 0))

    # --------------------------------------------------------------------------
    # MAP & TILE INITIALIZATION (100% OPEN-SOURCE ZERO-API-KEY)
    # --------------------------------------------------------------------------

    def _setup_map(self):
        """Instantiate and configure TkinterMapView with open-source zero-API-key tile server."""
        self.map_widget = tkintermapview.TkinterMapView(
            self.map_container,
            width=800,
            height=600,
            corner_radius=6
        )
        self.map_widget.pack(fill="both", expand=True)

        # Set default open-source CartoDB Dark Matter tile server
        server_info = OPEN_SOURCE_TILE_SERVERS[DEFAULT_TILE_KEY]
        self.map_widget.set_tile_server(
            server_info["url"],
            tile_size=server_info["tile_size"],
            max_zoom=server_info["max_zoom"]
        )

        # Center on current theater
        self.map_widget.set_position(self.sim_engine.center[0], self.sim_engine.center[1])
        self.map_widget.set_zoom(self.sim_engine.zoom)

        # Register map click callback for click-to-place and relocate actions
        self.map_widget.add_left_click_map_command(self._on_map_clicked)

    def _on_tile_server_selected(self, choice: str):
        """Switch open-source map tile server dynamically with ZERO API keys."""
        if choice in OPEN_SOURCE_TILE_SERVERS:
            cfg = OPEN_SOURCE_TILE_SERVERS[choice]
            self.map_widget.set_tile_server(
                cfg["url"],
                tile_size=cfg["tile_size"],
                max_zoom=cfg["max_zoom"]
            )
            self.lbl_mode_status.configure(text=f"TILE: {choice.split()[0]}", text_color="#38bdf8")

    # --------------------------------------------------------------------------
    # THEATER RENDERING & ENTITY VISUALIZATION
    # --------------------------------------------------------------------------

    def _render_theater_scenario(self):
        """Renders all sites, flight paths, radar WEZ circles, and threat markers."""
        # 1. Clear existing markers and paths from map
        self.map_widget.delete_all_marker()
        self.map_widget.delete_all_path()
        self.map_widget.delete_all_polygon()

        self.map_site_markers.clear()
        self.map_threat_markers.clear()
        self.map_trajectory_paths.clear()
        self.map_interceptor_paths.clear()
        self.map_interceptor_markers.clear()
        self.map_wez_polygons.clear()
        self.map_detonation_markers.clear()
        self.map_stealth_path = None

        # 2. Render Attacker Launch Sites (Red)
        for s in self.sim_engine.attacker_launch_sites:
            m = self.map_widget.set_marker(
                s["lat"], s["lon"],
                text=f"🚀 {s['name'][:22]}",
                marker_color_circle="#ef4444",
                marker_color_outside="#7f1d1d",
                text_color="#fca5a5",
                command=self._on_marker_clicked
            )
            self.map_site_markers[s["id"]] = (m, s, "attacker")
            self._attach_drag_events_to_marker(m, s)

        # 3. Render Defender Batteries & Radar WEZ Circles (Emerald Green)
        for b in self.sim_engine.defender_batteries:
            m = self.map_widget.set_marker(
                b["lat"], b["lon"],
                text=f"🛡 {b['name'][:22]}",
                marker_color_circle="#10b981",
                marker_color_outside="#064e3b",
                text_color="#6ee7b7",
                command=self._on_marker_clicked
            )
            self.map_site_markers[b["id"]] = (m, b, "defender")
            self._attach_drag_events_to_marker(m, b)

            # Draw Radar WEZ circle polygon
            radius_km = float(b.get("wez_radius_km", 70.0))
            circle_pts = calculate_circle_points(b["lat"], b["lon"], radius_km)
            poly = self.map_widget.set_polygon(
                circle_pts,
                outline_color="#00ff88",
                fill_color=None,
                border_width=2,
                name=f"WEZ-{b['id']}"
            )
            self.map_wez_polygons[b["id"]] = poly

        # 4. Render Defended Target Assets (HVAs - Amber/Gold)
        for t in self.sim_engine.target_assets:
            m = self.map_widget.set_marker(
                t["lat"], t["lon"],
                text=f"🎯 {t['name'][:22]}",
                marker_color_circle="#f59e0b",
                marker_color_outside="#78350f",
                text_color="#fde68a",
                command=self._on_marker_clicked
            )
            self.map_site_markers[t["id"]] = (m, t, "target")
            self._attach_drag_events_to_marker(m, t)

        # 5. Render Geodesic Trajectory Flight Paths
        self._recompute_and_draw_trajectories()

        # 6. Update HUD display for selected track
        self._update_hud_display()

    def _recompute_and_draw_trajectories(self):
        """Calculate and draw geodesic trajectory flight curves and intercept vectors."""
        # Delete old paths
        for path_obj in list(self.map_trajectory_paths.values()) + list(self.map_interceptor_paths.values()):
            if path_obj:
                try:
                    path_obj.delete()
                except Exception:
                    pass
        self.map_trajectory_paths.clear()
        self.map_interceptor_paths.clear()

        # For each threat track, generate 3D/geodesic waypoints
        for tr in self.sim_engine.tracks:
            l_lat = tr.get("launch_lat", self.sim_engine.center[0])
            l_lon = tr.get("launch_lon", self.sim_engine.center[1])
            t_lat = tr.get("target_lat", self.sim_engine.center[0])
            t_lon = tr.get("target_lon", self.sim_engine.center[1])

            t_type = tr.get("type", "Ballistic").lower()
            apogee_km = float(tr.get("apogee_km", 50.0))

            waypoints = map_views.generate_trajectory_waypoints(
                l_lat, l_lon, t_lat, t_lon,
                threat_type=t_type,
                apogee_km=apogee_km,
                n_points=40
            )
            coords = [(wp["lat"], wp["lon"]) for wp in waypoints]

            # Threat flight path line (Red / Orange)
            path_color = "#f43f5e" if "ballistic" in t_type else ("#f97316" if "hypersonic" in t_type else "#fbbf24")
            p = self.map_widget.set_path(coords, color=path_color, width=3)
            self.map_trajectory_paths[tr["id"]] = p

            # Interceptor climb vector (Cyan)
            if tr.get("outcome") in ["INTERCEPTED", "DIRECT HIT"] and self.sim_engine.defender_batteries:
                bat = self.sim_engine.defender_batteries[0]
                intercept_lat = (l_lat + t_lat) * 0.5
                intercept_lon = (l_lon + t_lon) * 0.5
                int_wps = map_views.generate_interceptor_trajectory(
                    bat["lat"], bat["lon"],
                    intercept_lat, intercept_lon,
                    intercept_alt_km=25.0,
                    n_points=25
                )
                int_coords = [(wp["lat"], wp["lon"]) for wp in int_wps]
                int_p = self.map_widget.set_path(int_coords, color="#00f0ff", width=2)
                self.map_interceptor_paths[tr["id"]] = int_p

    def _attach_drag_events_to_marker(self, marker: Any, site_dict: Dict[str, Any]):
        """Attach drag & drop mouse motion bindings to marker canvas items."""
        canvas = self.map_widget.canvas
        items_to_bind = [getattr(marker, "big_circle", None), getattr(marker, "polygon", None)]

        for item_id in items_to_bind:
            if item_id:
                canvas.tag_bind(item_id, "<ButtonPress-1>", lambda event, m=marker, s=site_dict: self._on_marker_drag_start(event, m, s), add="+")
                canvas.tag_bind(item_id, "<B1-Motion>", lambda event, m=marker, s=site_dict: self._on_marker_drag_motion(event, m, s), add="+")
                canvas.tag_bind(item_id, "<ButtonRelease-1>", lambda event, m=marker, s=site_dict: self._on_marker_drag_end(event, m, s), add="+")

    # --------------------------------------------------------------------------
    # DRAG-AND-DROP & CLICK-TO-PLACE LOGIC
    # --------------------------------------------------------------------------

    def _on_marker_clicked(self, marker: Any):
        """Called when a user clicks directly on a map marker."""
        for site_id, (m_obj, s_dict, s_kind) in self.map_site_markers.items():
            if m_obj == marker:
                self.active_marker_obj = m_obj
                self.active_site_dict = s_dict
                self.lbl_selected_marker_info.configure(
                    text=f"Selected: {s_dict['name'][:24]}\nType: {s_kind.upper()} | Pos: ({s_dict['lat']:.3f}, {s_dict['lon']:.3f})\n[Drag marker or click map to relocate]",
                    text_color="#38bdf8"
                )
                self.lbl_mode_status.configure(text=f"SELECTED: {s_dict['name'][:18]}", text_color="#38bdf8")
                return

    def _on_marker_drag_start(self, event, marker: Any, site_dict: Dict[str, Any]):
        """Initiates marker dragging."""
        self.is_dragging = True
        self.active_marker_obj = marker
        self.active_site_dict = site_dict
        self.lbl_mode_status.configure(text="DRAGGING UNIT...", text_color="#f59e0b")

    def _on_marker_drag_motion(self, event, marker: Any, site_dict: Dict[str, Any]):
        """Moves marker smoothly across canvas during drag."""
        if not self.is_dragging:
            return
        lat, lon = canvas_to_coords(self.map_widget, event.x, event.y)
        marker.set_position(lat, lon)
        site_dict["lat"] = round(lat, 4)
        site_dict["lon"] = round(lon, 4)

    def _on_marker_drag_end(self, event, marker: Any, site_dict: Dict[str, Any]):
        """Finalizes marker position on release and recalculates simulation geodesics."""
        self.is_dragging = False
        lat, lon = canvas_to_coords(self.map_widget, event.x, event.y)
        marker.set_position(lat, lon)

        # Update simulation model
        self.sim_engine.move_site(site_dict["id"], lat, lon)

        # Update WEZ circle if defender battery moved
        if site_dict["id"] in self.map_wez_polygons:
            poly = self.map_wez_polygons[site_dict["id"]]
            poly.delete()
            radius_km = float(site_dict.get("wez_radius_km", 70.0))
            circle_pts = calculate_circle_points(lat, lon, radius_km)
            self.map_wez_polygons[site_dict["id"]] = self.map_widget.set_polygon(
                circle_pts,
                outline_color="#00ff88",
                fill_color=None,
                border_width=2
            )

        # Recompute trajectories with new coordinates
        self._recompute_and_draw_trajectories()

        # Refresh HUD
        self._update_hud_display()
        self.lbl_mode_status.configure(text="UNIT RELOCATED", text_color="#10b981")
        self.lbl_selected_marker_info.configure(
            text=f"Selected: {site_dict['name'][:24]}\nPos: ({lat:.3f}, {lon:.3f})\nTrajectories updated.",
            text_color="#10b981"
        )

    def _on_map_clicked(self, coords: Tuple[float, float]):
        """Handles map clicks for click-to-place new sites or relocating active units."""
        lat, lon = coords
        if self.placement_mode == "relocate" and self.active_site_dict:
            site_id = self.active_site_dict["id"]
            if self.active_marker_obj:
                self.active_marker_obj.set_position(lat, lon)
            self.sim_engine.move_site(site_id, lat, lon)

            # Re-draw WEZ circle if defender
            if site_id in self.map_wez_polygons:
                self.map_wez_polygons[site_id].delete()
                radius_km = float(self.active_site_dict.get("wez_radius_km", 70.0))
                self.map_wez_polygons[site_id] = self.map_widget.set_polygon(
                    calculate_circle_points(lat, lon, radius_km),
                    outline_color="#00ff88", fill_color=None, border_width=2
                )

            self._recompute_and_draw_trajectories()
            self._update_hud_display()
            self.placement_mode = None
            self.lbl_mode_status.configure(text="UNIT PLACED", text_color="#10b981")

        elif self.placement_mode == "attacker":
            new_id = f"launch-custom-{int(time.time())}"
            new_site = {
                "id": new_id,
                "name": f"Mobile TEL Complex #{len(self.sim_engine.attacker_launch_sites) + 1}",
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "faction": "Aggressor Strike Force",
                "systems": ["Custom Ballistic TEL"]
            }
            self.sim_engine.attacker_launch_sites.append(new_site)
            m = self.map_widget.set_marker(
                lat, lon, text=f"🚀 {new_site['name']}",
                marker_color_circle="#ef4444", marker_color_outside="#7f1d1d", text_color="#fca5a5",
                command=self._on_marker_clicked
            )
            self.map_site_markers[new_id] = (m, new_site, "attacker")
            self._attach_drag_events_to_marker(m, new_site)
            self.placement_mode = None
            self.lbl_mode_status.configure(text="ATTACKER ADDED", text_color="#10b981")

        elif self.placement_mode == "defender":
            new_id = f"bat-custom-{int(time.time())}"
            new_bat = {
                "id": new_id,
                "name": f"Patriot PAC-3 Battery #{len(self.sim_engine.defender_batteries) + 1}",
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "system": "MIM-104 Patriot MSE",
                "wez_radius_km": 70.0
            }
            self.sim_engine.defender_batteries.append(new_bat)
            m = self.map_widget.set_marker(
                lat, lon, text=f"🛡 {new_bat['name']}",
                marker_color_circle="#10b981", marker_color_outside="#064e3b", text_color="#6ee7b7",
                command=self._on_marker_clicked
            )
            self.map_site_markers[new_id] = (m, new_bat, "defender")
            self._attach_drag_events_to_marker(m, new_bat)

            poly = self.map_widget.set_polygon(
                calculate_circle_points(lat, lon, 70.0),
                outline_color="#00ff88", fill_color=None, border_width=2
            )
            self.map_wez_polygons[new_id] = poly
            self.placement_mode = None
            self.lbl_mode_status.configure(text="BATTERY ADDED", text_color="#10b981")

        elif self.placement_mode == "target":
            new_id = f"target-custom-{int(time.time())}"
            new_tgt = {
                "id": new_id,
                "name": f"Defended HVA #{len(self.sim_engine.target_assets) + 1}",
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "type": "Strategic Infrastructure"
            }
            self.sim_engine.target_assets.append(new_tgt)
            m = self.map_widget.set_marker(
                lat, lon, text=f"🎯 {new_tgt['name']}",
                marker_color_circle="#f59e0b", marker_color_outside="#78350f", text_color="#fde68a",
                command=self._on_marker_clicked
            )
            self.map_site_markers[new_id] = (m, new_tgt, "target")
            self._attach_drag_events_to_marker(m, new_tgt)
            self.placement_mode = None
            self.lbl_mode_status.configure(text="TARGET ADDED", text_color="#10b981")

    def _set_placement_mode(self, mode: str):
        """Sets active placement mode."""
        self.placement_mode = mode
        self.lbl_mode_status.configure(text=f"CLICK MAP TO PLACE: {mode.upper()}", text_color="#f59e0b")

    def _on_btn_relocate_clicked(self):
        if not self.active_site_dict:
            messagebox.showinfo("Relocate Unit", "Please click on a marker first to select it.")
            return
        self.placement_mode = "relocate"
        self.lbl_mode_status.configure(text=f"CLICK MAP TO MOVE: {self.active_site_dict['name'][:18]}", text_color="#38bdf8")

    # --------------------------------------------------------------------------
    # SIMULATION TICK & TELEMETRY UPDATES
    # --------------------------------------------------------------------------

    def _sim_tick(self):
        """Periodic real-time simulation clock handler."""
        now = time.time()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        if self.sim_engine.is_playing:
            self.sim_engine.advance_time(dt)
            self.timeline_slider.set(self.sim_engine.sim_time_s)
            self._update_sim_visuals()

        # Schedule next tick
        if not self.headless and self.root:
            self.root.after(50, self._sim_tick)

    def _update_sim_visuals(self):
        """Update live missile positions, detonation bursts, and HUD telemetry values."""
        t_sec = self.sim_engine.sim_time_s
        total_s = self.sim_engine.duration_s

        # Clock string
        m = int(t_sec // 60)
        s = t_sec % 60
        tot_m = int(total_s // 60)
        tot_s = total_s % 60
        self.lbl_clock.configure(text=f"SIM CLOCK: T+{m:02d}:{s:04.1f}s / {tot_m:02d}:{tot_s:04.1f}s")

        # Telemetry for all tracks
        all_telemetry = self.sim_engine.compute_all_telemetry(t_sec)

        # Update live missile / threat positions on map
        for data in all_telemetry:
            trk_id = data["id"]
            lat = data["lat"]
            lon = data["lon"]
            status = data["status"]
            phase = data["phase"]
            mach = data["mach"]
            alt_km = data["alt_km"]

            # Position marker for threat
            if status in ["IN FLIGHT", "STANDBY"]:
                label = f"🚀 {trk_id}: M{mach:.1f} | {alt_km:.1f}km"
                if trk_id not in self.map_threat_markers:
                    m = self.map_widget.set_marker(
                        lat, lon, text=label,
                        marker_color_circle="#ff0055",
                        marker_color_outside="#ff3366",
                        text_color="#ffccd5"
                    )
                    self.map_threat_markers[trk_id] = m
                else:
                    self.map_threat_markers[trk_id].set_position(lat, lon)
                    self.map_threat_markers[trk_id].set_text(label)

                # Defending interceptor active flight
                progress = data.get("progress_pct", 0.0) / 100.0
                if progress >= 0.15 and self.sim_engine.defender_batteries:
                    bat = self.sim_engine.defender_batteries[0]
                    target_dict = self.sim_engine.get_track_by_id(trk_id) or {}
                    l_lat = target_dict.get("launch_lat", lat)
                    l_lon = target_dict.get("launch_lon", lon)
                    t_lat = target_dict.get("target_lat", lat)
                    t_lon = target_dict.get("target_lon", lon)
                    int_lat = (l_lat + t_lat) * 0.5
                    int_lon = (l_lon + t_lon) * 0.5
                    int_u = min(1.0, (progress - 0.15) / 0.50)
                    cur_int_lat = bat["lat"] + (int_lat - bat["lat"]) * int_u
                    cur_int_lon = bat["lon"] + (int_lon - bat["lon"]) * int_u
                    int_label = f"⚡ INT: PAC-3 MSE (Mach 4.5)"

                    if trk_id not in self.map_interceptor_markers:
                        int_m = self.map_widget.set_marker(
                            cur_int_lat, cur_int_lon, text=int_label,
                            marker_color_circle="#00f0ff",
                            marker_color_outside="#0284c7",
                            text_color="#e0f2fe"
                        )
                        self.map_interceptor_markers[trk_id] = int_m
                    else:
                        self.map_interceptor_markers[trk_id].set_position(cur_int_lat, cur_int_lon)
                        self.map_interceptor_markers[trk_id].set_text(int_label)

            elif status in ["INTERCEPTED", "DIRECT HIT"]:
                # Intercepted! Clean up threat & interceptor, spawn gold detonation starburst
                if trk_id in self.map_threat_markers:
                    self.map_threat_markers[trk_id].delete()
                    del self.map_threat_markers[trk_id]
                if trk_id in self.map_interceptor_markers:
                    self.map_interceptor_markers[trk_id].delete()
                    del self.map_interceptor_markers[trk_id]

                if trk_id not in self.map_detonation_markers:
                    m = self.map_widget.set_marker(
                        lat, lon,
                        text=f"💥 INTERCEPT: {trk_id} [KILL CONFIRMED]",
                        marker_color_circle="#ffea00",
                        marker_color_outside="#ff9100",
                        text_color="#fef08a"
                    )
                    self.map_detonation_markers[trk_id] = m

            elif status in ["DETONATED", "MISS"]:
                # Impact on defended target! Red detonation burst
                if trk_id in self.map_threat_markers:
                    self.map_threat_markers[trk_id].delete()
                    del self.map_threat_markers[trk_id]
                if trk_id in self.map_interceptor_markers:
                    self.map_interceptor_markers[trk_id].delete()
                    del self.map_interceptor_markers[trk_id]

                if trk_id not in self.map_detonation_markers:
                    m = self.map_widget.set_marker(
                        lat, lon,
                        text=f"💥 IMPACT: {data['target']} [LEAKER DETONATION]",
                        marker_color_circle="#ff1744",
                        marker_color_outside="#b71c1c",
                        text_color="#fca5a5"
                    )
                    self.map_detonation_markers[trk_id] = m

        # Update HUD for selected track
        self._update_hud_display()

    def _update_hud_display(self):
        """Update telemetry cards and meters for selected track."""
        if not self.sim_engine.selected_track_id:
            return

        track_dict = self.sim_engine.get_track_by_id(self.sim_engine.selected_track_id)
        if not track_dict:
            return

        data = app.calculate_track_telemetry_at_time(track_dict, self.sim_engine.sim_time_s)

        # 1. Threat Card
        self.lbl_threat_name.configure(text=f"{data['id']}: {data['name']}")
        self.lbl_threat_details.configure(
            text=f"Type: {data['type']} | Faction: {data['faction']}\nOrigin: {data['origin']} -> Target: {data['target']}\nWarhead: {data['warhead']} | Guidance: {data['guidance']}"
        )

        # 2. Mach Card
        mach = data["mach"]
        max_mach = float(track_dict.get("max_mach", 4.0))
        self.lbl_mach_val.configure(text=f"MACH {mach:.2f}")
        self.mach_prog_bar.set(min(1.0, mach / max(1.0, max_mach)))
        self.lbl_speed_subtext.configure(text=f"{data['speed_mps']:.0f} m/s | {data['speed_kmh']:.0f} km/h (Max: Mach {max_mach:.1f})")

        # 3. Altitude Card
        alt_km = data["alt_km"]
        self.lbl_alt_val.configure(text=f"{alt_km:.2f} km")
        zone_text, zone_color = get_atmospheric_zone(alt_km)
        self.lbl_alt_zone.configure(text=f"● {zone_text}", text_color=zone_color)
        self.lbl_alt_subtext.configure(text=f"Apogee: {data['apogee_km']:.1f} km | Vertical Speed: {data['vertical_speed_mps']:+.1f} m/s")

        # 4. Phase & Status Badges
        phase = data["phase"]
        status = data["status"]

        phase_colors = {
            "BOOST": ("#b45309", "#fef3c7"),
            "MIDCOURSE": ("#0369a1", "#e0f2fe"),
            "GLIDE": ("#7c3aed", "#ede9fe"),
            "TERMINAL": ("#be123c", "#ffe4e6"),
            "LOITER": ("#4338ca", "#e0e7ff"),
            "INTERCEPT": ("#15803d", "#dcfce7"),
        }
        p_bg, p_fg = phase_colors.get(phase, ("#334155", "#f1f5f9"))
        self.lbl_phase_badge.configure(text=f"PHASE: {phase}", fg_color=p_bg, text_color=p_fg)

        status_colors = {
            "STANDBY": ("#334155", "#cbd5e1"),
            "IN FLIGHT": ("#166534", "#dcfce7"),
            "INTERCEPTED": ("#854d0e", "#fef08a"),
            "DIRECT HIT": ("#166534", "#bbf7d0"),
            "DETONATED": ("#991b1b", "#fecaca"),
            "MISS": ("#475569", "#cbd5e1"),
        }
        s_bg, s_fg = status_colors.get(status, ("#1e293b", "#f8fafc"))
        self.lbl_status_badge.configure(text=status, fg_color=s_bg, text_color=s_fg)

        pct = data["progress_pct"]
        self.lbl_progress_pct.configure(text=f"{pct:.1f}%")
        self.prog_bar.set(min(1.0, pct / 100.0))

        # 5. Distance & Time
        self.lbl_distance_text.configure(
            text=f"Traveled: {data['dist_traveled_km']:.1f} km / {track_dict.get('range_km', 400.0):.1f} km\nRemaining: {data['dist_remaining_km']:.1f} km | ETOF: {data['etof_s']:.1f}s (Rem: {data['time_remaining_s']:.1f}s)"
        )

        # 6. Intercept Assessment
        battery_name = track_dict.get("intercept_by", "Patriot PAC-3 MSE")
        if status in ["INTERCEPTED", "DIRECT HIT"]:
            solution_text = f"Assigned Battery: {battery_name}\nStatus: KINETIC INTERCEPT CONFIRMED\nMiss Distance (CPA): 1.25 m | Alt: {alt_km:.1f} km\nP_kill: 94.2% | Target Protected"
            color = "#4ade80"
        elif status in ["DETONATED", "MISS"]:
            solution_text = f"Assigned Battery: {battery_name}\nStatus: LEAKER IMPACT DETECTED\nImpact Coordinate: ({data['lat']:.3f}, {data['lon']:.3f})\nAssessment: Target Damaged"
            color = "#f87171"
        else:
            solution_text = f"Assigned Battery: {battery_name}\nFire Control: TRACKING & PREDICTED LEAD CALCULATED\nPredicted CPA: 1.25 m | P_kill: 94.2%\nEngagement Phase: Scheduled at T+{track_dict.get('intercept_time_s', 70.0):.1f}s"
            color = "#38bdf8"

        self.lbl_intercept_solution.configure(text=solution_text, text_color=color)

        # 7. Easter Egg Banner Check
        if self.sim_engine.easter_egg_data.get("active"):
            self.easter_banner_frame.pack(fill="x", padx=8, pady=4, before=self.card_threat)
            self.easter_banner_lbl.configure(text=self.sim_engine.easter_egg_data.get("banner_text", "AIR-LAUNCH ALERT"))
        else:
            self.easter_banner_frame.pack_forget()

    # --------------------------------------------------------------------------
    # PLAYBACK TRANSPORT EVENT HANDLERS
    # --------------------------------------------------------------------------

    def _on_btn_play_clicked(self):
        """Toggle Play / Pause."""
        self.sim_engine.is_playing = not self.sim_engine.is_playing
        if self.sim_engine.is_playing:
            self.btn_play_pause.configure(text="⏸ Pause", fg_color="#b91c1c", hover_color="#dc2626")
            self.lbl_mode_status.configure(text="SIMULATION RUNNING", text_color="#00e676")
        else:
            self.btn_play_pause.configure(text="▶ Play", fg_color="#0284c7", hover_color="#0369a1")
            self.lbl_mode_status.configure(text="SIMULATION PAUSED", text_color="#f59e0b")

    def _on_btn_reset_clicked(self):
        """Reset timeline to T+0."""
        self.sim_engine.reset()
        self.btn_play_pause.configure(text="▶ Play", fg_color="#0284c7", hover_color="#0369a1")
        self.timeline_slider.set(0.0)
        # Clear detonation bursts
        for m in self.map_detonation_markers.values():
            m.delete()
        self.map_detonation_markers.clear()
        self._update_sim_visuals()
        self.lbl_mode_status.configure(text="READY / RESET", text_color="#10b981")

    def _on_btn_step_clicked(self):
        """Step simulation clock forward by +1.0 second."""
        self.sim_engine.advance_time(1.0)
        self.timeline_slider.set(self.sim_engine.sim_time_s)
        self._update_sim_visuals()

    def _on_slider_scrubbed(self, value: float):
        """Handle scrubber slider dragging."""
        self.sim_engine.seek_time(float(value))
        self._update_sim_visuals()

    def _on_speed_selected(self, choice: str):
        """Set speed multiplier."""
        mult = float(choice.replace("x", ""))
        self.sim_engine.speed_multiplier = mult

    def _on_track_selected(self, choice: str):
        """Change monitored track from dropdown."""
        trk_id = choice.split(":")[0].strip()
        self.sim_engine.selected_track_id = trk_id
        self._update_hud_display()

    def _on_theater_selected(self, choice: str):
        """Switch tactical theater."""
        key_map = {
            "Eastern Europe / Black Sea": "eastern_europe",
            "Persian Gulf / Red Sea": "persian_gulf",
            "Taiwan Strait / Indo-Pacific": "taiwan_strait",
            "CONUS Homeland": "conus_homeland"
        }
        th_key = key_map.get(choice, "eastern_europe")
        self.sim_engine.load_theater(th_key)

        # Update slider limits
        self.timeline_slider.configure(to=self.sim_engine.duration_s)
        self.timeline_slider.set(0.0)

        # Update map position and zoom
        self.map_widget.set_position(self.sim_engine.center[0], self.sim_engine.center[1])
        self.map_widget.set_zoom(self.sim_engine.zoom)

        # Update track selector dropdown values
        track_options = [f"{t['id']}: {t['name']}" for t in self.sim_engine.tracks]
        self.track_selector.configure(values=track_options)
        if track_options:
            self.track_selector.set(track_options[0])

        # Re-render all entities
        self._render_theater_scenario()
        self.lbl_mode_status.configure(text=f"THEATER: {choice.split('/')[0].strip()}", text_color="#00f0ff")

    def _on_launch_strike_clicked(self):
        """Trigger strike launch raid, evaluating 10% stealth air-launch easter egg."""
        # 10% probability trigger on strike launch
        egg = self.sim_engine.trigger_easter_egg(force=False)
        if egg.get("active"):
            self._render_stealth_ingress(egg)
        self.sim_engine.reset()
        self.sim_engine.is_playing = True
        self.btn_play_pause.configure(text="⏸ Pause", fg_color="#b91c1c", hover_color="#dc2626")
        self.lbl_mode_status.configure(text="STRIKE RAID ACTIVE", text_color="#ef4444")

    def _trigger_air_launch(self, force: bool = True):
        """Directly triggers stealth fighter stand-off weapon deployment."""
        egg = self.sim_engine.trigger_easter_egg(force=force)
        self._render_stealth_ingress(egg)
        self._update_hud_display()

    def _render_stealth_ingress(self, egg_data: Dict[str, Any]):
        """Render stealth fighter flight vector and tactical banner."""
        if self.map_stealth_path:
            try:
                self.map_stealth_path.delete()
            except Exception:
                pass
            self.map_stealth_path = None

        coords = egg_data.get("coords", [])
        if coords:
            self.map_stealth_path = self.map_widget.set_path(coords, color="#38bdf8", width=3)
            # Add stealth aircraft marker
            aircraft_name = egg_data.get("aircraft", "F-22A Raptor")
            self.map_widget.set_marker(
                coords[-1][0], coords[-1][1],
                text=f"✈ {aircraft_name} (AIR LAUNCH)",
                marker_color_circle="#0284c7",
                marker_color_outside="#0369a1",
                text_color="#7dd3fc"
            )

        self._update_hud_display()

    # --------------------------------------------------------------------------
    # LIFECYCLE EXECUTION
    # --------------------------------------------------------------------------

    def run(self):
        """Launch the native desktop GUI event loop."""
        if not self.headless:
            self.root.mainloop()

    def destroy(self):
        """Clean shutdown of desktop window."""
        if self.root:
            self.root.destroy()


# ==============================================================================
# 5. COMMAND LINE ENTRYPOINT
# ==============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="IAMD Global Defense Simulator Standalone Desktop Application")
    parser.add_argument("--theater", type=str, default="eastern_europe", choices=["eastern_europe", "persian_gulf", "taiwan_strait", "conus_homeland"], help="Operational theater")
    parser.add_argument("--headless", action="store_true", help="Run without graphical window for automated testing")
    args = parser.parse_args()

    print("=" * 80)
    print("STARTING IAMD GLOBAL DEFENSE SIMULATOR - NATIVE DESKTOP GUI")
    print(f"Operational Theater: {args.theater}")
    print(f"Map Engine: Open-Source Zero-API-Key (CartoDB Dark Matter / OSM / OpenTopoMap)")
    print("=" * 80)

    app_instance = TacticalDesktopApp(headless=args.headless, theater_key=args.theater)
    if not args.headless:
        app_instance.run()


if __name__ == "__main__":
    main()
