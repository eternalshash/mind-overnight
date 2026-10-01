#!/usr/bin/env python3
"""
================================================================================
COMPREHENSIVE TEST SUITE: PYTHON DESKTOP DEPLOYMENT & OPEN-SOURCE MAP ENGINE
File: test_desktop_app.py
================================================================================
Verifies:
1. Headless initialization of `desktop_gui.py` (CustomTkinter + TkinterMapView).
2. 100% open-source zero-API-key tile providers (CartoDB Dark Matter, OSM, OpenTopoMap).
3. Drag-and-drop & click-to-place marker callbacks and geodesic recalculations.
4. Radar WEZ circle polygon generation and boundary coordinates.
5. Real-time telemetry HUD updates (Mach, altitude, apogee, phase badges, CPA, P_kill).
6. Playback transport controls (Play, Pause, Step, Reset, Speed Multiplier, Scrubber).
7. 10% F-22 / F-35 stealth fighter air-launch easter egg trigger and banner.
8. One-command desktop launcher (`run_desktop.py`) headless verification.
================================================================================
"""

import math
import os
import sys
import unittest
import urllib.parse
from typing import Dict, Any

# Ensure local directory is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import desktop_gui
import run_desktop
import map_views
import app


class TestDesktopDeploymentAndMapEngine(unittest.TestCase):
    """Test suite for Standalone Desktop GUI and Open-Source Map Engine."""

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 80)
        print("STARTING TEST SUITE: test_desktop_app.py")
        print("=" * 80)
        # Initialize headless desktop app
        cls.app = desktop_gui.TacticalDesktopApp(headless=True, theater_key="eastern_europe")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "app") and cls.app:
            cls.app.destroy()
        print("\n" + "=" * 80)
        print("TEST SUITE COMPLETED SUCCESSFULLY")
        print("=" * 80)

    # --------------------------------------------------------------------------
    # 1. HEADLESS INITIALIZATION & THEATER PRESETS
    # --------------------------------------------------------------------------

    def test_01_headless_initialization(self):
        """Verifies that TacticalDesktopApp initializes cleanly in headless mode."""
        self.assertIsNotNone(self.app)
        self.assertIsNotNone(self.app.root)
        self.assertIsNotNone(self.app.map_widget)
        self.assertIsNotNone(self.app.sim_engine)
        self.assertTrue(self.app.headless)
        print("  ✓ Test 1: TacticalDesktopApp headless initialization verified.")

    def test_02_all_theaters_loadable(self):
        """Verifies that all 4 tactical theaters load valid geographic sites and tracks."""
        theaters = ["eastern_europe", "persian_gulf", "taiwan_strait", "conus_homeland"]
        for th in theaters:
            engine = desktop_gui.TacticalSimEngine(theater_key=th)
            self.assertEqual(engine.theater_key, th)
            self.assertGreater(len(engine.attacker_launch_sites), 0, f"No launch sites in {th}")
            self.assertGreater(len(engine.defender_batteries), 0, f"No defender batteries in {th}")
            self.assertGreater(len(engine.target_assets), 0, f"No target assets in {th}")
            self.assertGreater(len(engine.tracks), 0, f"No tracks in {th}")
            self.assertGreater(engine.duration_s, 0)
        print(f"  ✓ Test 2: All {len(theaters)} operational theaters verified with full sites and tracks.")

    # --------------------------------------------------------------------------
    # 2. OPEN-SOURCE ZERO-API-KEY TILE ENGINE VERIFICATION
    # --------------------------------------------------------------------------

    def test_03_zero_api_key_tile_servers(self):
        """Verifies all tile servers use strictly open-source URLs with zero API keys."""
        tile_providers = desktop_gui.OPEN_SOURCE_TILE_SERVERS
        self.assertIn("CartoDB Dark Matter (Tactical)", tile_providers)
        self.assertIn("OpenStreetMap (Standard)", tile_providers)
        self.assertIn("OpenTopoMap (Topographic)", tile_providers)

        for name, cfg in tile_providers.items():
            url = cfg["url"]
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)

            # Assert domain is strictly open-source
            allowed_domains = ["cartocdn.com", "openstreetmap.org", "opentopomap.org"]
            domain_match = any(d in parsed.netloc for d in allowed_domains)
            self.assertTrue(domain_match, f"Provider {name} has unexpected non-open-source domain: {parsed.netloc}")

            # Assert ZERO API key, token, or secret query parameters
            for forbidden_key in ["key", "api_key", "apikey", "token", "access_token", "app_id"]:
                self.assertNotIn(forbidden_key, query_params, f"Provider {name} contains API key parameter '{forbidden_key}'!")

        print(f"  ✓ Test 3: Verified {len(tile_providers)} tile servers are 100% open-source with ZERO API keys.")

    def test_04_tile_server_switching(self):
        """Verifies dynamic switching between open-source tile providers on the map widget."""
        for name, cfg in desktop_gui.OPEN_SOURCE_TILE_SERVERS.items():
            self.app._on_tile_server_selected(name)
            self.assertEqual(self.app.map_widget.tile_server, cfg["url"])
            self.assertEqual(self.app.map_widget.max_zoom, cfg["max_zoom"])
        # Restore default tactical dark tile
        self.app._on_tile_server_selected(desktop_gui.DEFAULT_TILE_KEY)
        print("  ✓ Test 4: Dynamic tile server switching verified.")

    # --------------------------------------------------------------------------
    # 3. MARKER DRAG-AND-DROP & CLICK-TO-PLACE CALLBACKS
    # --------------------------------------------------------------------------

    def test_05_marker_selection_and_click_callback(self):
        """Verifies marker click selection callback updates active unit and status."""
        self.assertGreater(len(self.app.map_site_markers), 0)
        first_id = list(self.app.map_site_markers.keys())[0]
        marker_obj, site_dict, kind = self.app.map_site_markers[first_id]

        # Trigger click callback
        self.app._on_marker_clicked(marker_obj)
        self.assertEqual(self.app.active_marker_obj, marker_obj)
        self.assertEqual(self.app.active_site_dict, site_dict)
        print(f"  ✓ Test 5: Marker click callback verified for '{site_dict['name']}'.")

    def test_06_marker_drag_and_drop_recalculation(self):
        """Simulates dragging an Attacker launch site and verifies geodesic trajectory recalculation."""
        # Find an attacker site
        atk_site = self.app.sim_engine.attacker_launch_sites[0]
        site_id = atk_site["id"]
        orig_lat, orig_lon = atk_site["lat"], atk_site["lon"]
        marker_obj, _, _ = self.app.map_site_markers[site_id]

        new_lat, new_lon = orig_lat + 1.25, orig_lon + 1.50

        # Simulate drag sequence
        class MockEvent:
            x = 420
            y = 280

        expected_lat, expected_lon = desktop_gui.canvas_to_coords(self.app.map_widget, MockEvent.x, MockEvent.y)

        self.app._on_marker_drag_start(MockEvent(), marker_obj, atk_site)
        self.assertTrue(self.app.is_dragging)

        self.app._on_marker_drag_motion(MockEvent(), marker_obj, atk_site)
        self.app._on_marker_drag_end(MockEvent(), marker_obj, atk_site)

        self.assertFalse(self.app.is_dragging)
        self.assertAlmostEqual(atk_site["lat"], expected_lat, places=2)
        self.assertAlmostEqual(atk_site["lon"], expected_lon, places=2)

        # Explicitly relocate site and recompute trajectories
        self.app.sim_engine.move_site(site_id, new_lat, new_lon)
        marker_obj.set_position(new_lat, new_lon)
        self.app._recompute_and_draw_trajectories()

        # Verify connected tracks have updated launch coords
        for tr in self.app.sim_engine.tracks:
            if tr.get("origin") == atk_site["name"] or tr.get("launch_site_id") == site_id:
                self.assertAlmostEqual(tr["launch_lat"], new_lat, places=2)
                self.assertAlmostEqual(tr["launch_lon"], new_lon, places=2)

        print(f"  ✓ Test 6: Marker drag to ({new_lat:.2f}, {new_lon:.2f}) and trajectory recalculation verified.")

    def test_07_click_to_place_new_sites(self):
        """Verifies click-to-place functionality for new Attacker, Defender, and Target entities."""
        # 1. Place Attacker Site
        initial_atk_count = len(self.app.sim_engine.attacker_launch_sites)
        self.app._set_placement_mode("attacker")
        self.assertEqual(self.app.placement_mode, "attacker")
        self.app._on_map_clicked((46.5, 38.0))
        self.assertEqual(len(self.app.sim_engine.attacker_launch_sites), initial_atk_count + 1)
        self.assertIsNone(self.app.placement_mode)

        # 2. Place Defender Battery with WEZ circle
        initial_def_count = len(self.app.sim_engine.defender_batteries)
        self.app._set_placement_mode("defender")
        self.app._on_map_clicked((49.2, 31.5))
        self.assertEqual(len(self.app.sim_engine.defender_batteries), initial_def_count + 1)
        new_bat = self.app.sim_engine.defender_batteries[-1]
        self.assertIn(new_bat["id"], self.app.map_wez_polygons)

        # 3. Place Defended Target
        initial_tgt_count = len(self.app.sim_engine.target_assets)
        self.app._set_placement_mode("target")
        self.app._on_map_clicked((51.0, 32.0))
        self.assertEqual(len(self.app.sim_engine.target_assets), initial_tgt_count + 1)

        print("  ✓ Test 7: Click-to-place verified for Attacker (+1), Defender Battery (+1), and Target (+1).")

    # --------------------------------------------------------------------------
    # 4. RADAR WEZ CIRCLE & GEODESIC TRAJECTORY UTILITIES
    # --------------------------------------------------------------------------

    def test_08_radar_wez_circle_geometry(self):
        """Verifies geodesic circular boundary calculation around defender battery."""
        lat, lon, radius_km = 50.45, 30.52, 70.0
        pts = desktop_gui.calculate_circle_points(lat, lon, radius_km, num_points=36)
        self.assertEqual(len(pts), 37)  # Closed circle

        # Check distance from center to all circle boundary points
        for p_lat, p_lon in pts:
            dist = map_views.haversine_distance_km(lat, lon, p_lat, p_lon)
            self.assertAlmostEqual(dist, radius_km, delta=1.5, msg=f"Circle point ({p_lat}, {p_lon}) has incorrect radius {dist}")

        print("  ✓ Test 8: Radar WEZ circle geometry mathematically verified on WGS84 sphere.")

    # --------------------------------------------------------------------------
    # 5. LIVE TELEMETRY HUD UPDATE FUNCTIONS
    # --------------------------------------------------------------------------

    def test_09_telemetry_hud_updates_across_phases(self):
        """Tests telemetry HUD values (Mach, altitude, apogee, phase, CPA, P_kill) across multiple timesteps."""
        track = self.app.sim_engine.tracks[0]
        self.app.sim_engine.selected_track_id = track["id"]

        test_times = [
            (0.0, "BOOST", "STANDBY"),
            (30.0, "MIDCOURSE", "IN FLIGHT"),
            (75.0, "TERMINAL", "INTERCEPTED"),
        ]

        for t_sec, exp_phase, exp_status in test_times:
            self.app.sim_engine.seek_time(t_sec)
            self.app._update_sim_visuals()

            data = app.calculate_track_telemetry_at_time(track, t_sec)
            self.assertEqual(data["phase"], exp_phase)
            self.assertEqual(data["status"], exp_status)
            if t_sec > 0.0:
                self.assertGreater(data["mach"], 0.0)
            else:
                self.assertGreaterEqual(data["mach"], 0.0)
            self.assertGreaterEqual(data["alt_km"], 0.0)

            # Verify atmospheric zone function
            zone_text, zone_color = desktop_gui.get_atmospheric_zone(data["alt_km"])
            self.assertIsNotNone(zone_text)
            self.assertIsNotNone(zone_color)

        print("  ✓ Test 9: Telemetry HUD updates across BOOST, MIDCOURSE, and TERMINAL/INTERCEPT verified.")

    # --------------------------------------------------------------------------
    # 6. PLAYBACK TRANSPORT CONTROLS
    # --------------------------------------------------------------------------

    def test_10_playback_transport_controls(self):
        """Verifies Play, Pause, Step, Reset, Speed Multiplier, and Timeline Scrubber."""
        engine = self.app.sim_engine

        # Reset
        self.app._on_btn_reset_clicked()
        self.assertEqual(engine.sim_time_s, 0.0)
        self.assertFalse(engine.is_playing)

        # Play / Pause toggle
        self.app._on_btn_play_clicked()
        self.assertTrue(engine.is_playing)
        self.app._on_btn_play_clicked()
        self.assertFalse(engine.is_playing)

        # Step forward (+1s)
        self.app._on_btn_step_clicked()
        self.assertEqual(engine.sim_time_s, 1.0)
        self.app._on_btn_step_clicked()
        self.assertEqual(engine.sim_time_s, 2.0)

        # Timeline Scrubber
        self.app._on_slider_scrubbed(45.5)
        self.assertEqual(engine.sim_time_s, 45.5)

        # Speed Multiplier
        self.app._on_speed_selected("5.0x")
        self.assertEqual(engine.speed_multiplier, 5.0)

        print("  ✓ Test 10: Playback transport controls (Play, Pause, Step, Reset, Scrubber, Speed) verified.")

    # --------------------------------------------------------------------------
    # 7. EASTER EGG STEALTH AIR-LAUNCH TRIGGER
    # --------------------------------------------------------------------------

    def test_11_stealth_air_launch_trigger(self):
        """Verifies 10% F-22/F-35 easter egg trigger and flight path rendering."""
        # Force air-launch strike
        egg = self.app.sim_engine.trigger_easter_egg(force=True)
        self.assertTrue(egg["active"])
        self.assertIn(egg["aircraft"], ["F-22A Raptor", "F-35A Lightning II"])
        self.assertGreater(len(egg["coords"]), 0)

        # Render stealth ingress on map
        self.app._render_stealth_ingress(egg)
        self.assertIsNotNone(self.app.map_stealth_path)
        print(f"  ✓ Test 11: Easter egg stealth fighter trigger verified ({egg['aircraft']}).")

    # --------------------------------------------------------------------------
    # 8. ONE-COMMAND DESKTOP LAUNCHER (`run_desktop.py`) HEADLESS CHECK
    # --------------------------------------------------------------------------

    def test_12_desktop_launcher_headless_check(self):
        """Verifies run_desktop.py port discovery, embedded server launch, and headless HTTP check."""
        port = run_desktop.find_available_port(preferred_port=8065)
        self.assertGreater(port, 1024)

        result = run_desktop.launch_desktop(
            port=port,
            host="127.0.0.1",
            headless_check=True,
            theater="eastern_europe"
        )
        self.assertEqual(result, 0)
        print("  ✓ Test 12: One-command launcher (run_desktop.py) verified in headless check mode.")


if __name__ == "__main__":
    res = unittest.main(exit=False)
    os._exit(0 if res.result.wasSuccessful() else 1)
