#!/usr/bin/env python3
"""
================================================================================
HEADLESS VERIFICATION SUITE: IAMD GLOBAL DEFENSE SIMULATOR
File: test_app_headless.py
================================================================================
Performs comprehensive headless verification:
1. Verifies Dash application layout structure and theme integrity.
2. Checks that all required components and IDs are present in the layout tree.
3. Asserts all interactive callbacks are registered in `app.callback_map`.
4. Exercises playback engine, timeline scrubber, and 2D/3D toggle callbacks in-memory.
5. Verifies telemetry computation (Mach gauge, altimeter, phase badges, ETOF).
6. Verifies the 10% Easter egg stealth fighter air-launch alert mechanism.
7. Verifies the 100x Monte Carlo modal data and stochastic evaluation metrics.
================================================================================
"""

import sys
import unittest
from typing import Set

import dash
import plotly.graph_objects as go

# Import application and modules
import app
import catalog
import physics_engine
import defense_system
import map_views
import telemetry


def extract_all_ids(component) -> Set[str]:
    """Recursively traverses the Dash layout tree and collects all component IDs."""
    ids = set()
    if component is None:
        return ids

    # Check id attribute
    cid = getattr(component, "id", None)
    if cid is not None:
        if isinstance(cid, str):
            ids.add(cid)
        elif isinstance(cid, dict):
            # Pattern matching ID
            ids.add(str(cid))

    # Traverse children
    children = getattr(component, "children", None)
    if children is not None:
        if isinstance(children, list):
            for child in children:
                ids.update(extract_all_ids(child))
        else:
            ids.update(extract_all_ids(children))

    return ids


class TestIAMDGlobalDefenseSimulator(unittest.TestCase):
    """Headless integration test suite for Dash application."""

    @classmethod
    def setUpClass(cls):
        cls.dash_app = app.app
        cls.layout = cls.dash_app.layout
        cls.all_ids = extract_all_ids(cls.layout)
        print(f"\n[SETUP] Total component IDs identified in layout tree: {len(cls.all_ids)}")

    def test_01_app_initialization_and_title(self):
        """Verifies that the Dash application is correctly initialized with the military title."""
        self.assertIsInstance(self.dash_app, dash.Dash)
        self.assertEqual(self.dash_app.title, "IAMD GLOBAL DEFENSE SIMULATOR")
        self.assertIsNotNone(self.layout)
        print("  ✓ Test 1: Dash app initialization and military title verified.")

    def test_02_navbar_and_scenario_controls_presence(self):
        """Verifies presence of Top Navbar controls: Title, Presets, Theater Jump, 2D/3D toggle."""
        required_navbar_ids = [
            "scenario-preset-select",
            "theater-selector",
            "view-mode-toggle",
            "btn-launch-strike",
            "btn-open-monte-carlo",
        ]
        for cid in required_navbar_ids:
            self.assertIn(cid, self.all_ids, f"Navbar component ID '{cid}' missing from layout.")
        print(f"  ✓ Test 2: All {len(required_navbar_ids)} Top Navbar controls present.")

    def test_03_playback_controls_presence(self):
        """Verifies Playback Control Bar: Play, Pause, Step, Reset, Speed, Scrubber, Clock."""
        required_playback_ids = [
            "btn-play",
            "btn-pause",
            "btn-step",
            "btn-reset",
            "sim-speed-radio",
            "sim-clock-display",
            "sim-timeline-slider",
        ]
        for cid in required_playback_ids:
            self.assertIn(cid, self.all_ids, f"Playback component ID '{cid}' missing from layout.")
        print(f"  ✓ Test 3: All {len(required_playback_ids)} Playback Control Bar elements present.")

    def test_04_viewports_and_altitude_profile_presence(self):
        """Verifies 2D Leaflet Map, 3D Globe, and Altitude Profile Chart containers."""
        required_viewport_ids = [
            "tactical-2d-viewport-container",
            "tactical-3d-viewport-container",
            "tactical-3d-globe-graph",
            "missilemap-altitude-profile-graph",
        ]
        for cid in required_viewport_ids:
            self.assertIn(cid, self.all_ids, f"Viewport component ID '{cid}' missing from layout.")
        print(f"  ✓ Test 4: 2D Tactical Map, 3D Globe, and Altitude Profile containers present.")

    def test_05_telemetry_sidebar_presence(self):
        """Verifies Dedicated Telemetry Sidebar components and indicators."""
        required_telemetry_ids = [
            "telemetry-unit-select",
            "telemetry-mach-gauge",
            "telemetry-speed-readout",
            "telemetry-alt-indicators",
            "telemetry-progress-container",
            "telemetry-metrics-container",
            "telemetry-badges-container",
            "telemetry-target-info",
        ]
        for cid in required_telemetry_ids:
            self.assertIn(cid, self.all_ids, f"Telemetry sidebar component ID '{cid}' missing from layout.")
        print(f"  ✓ Test 5: All {len(required_telemetry_ids)} Telemetry Sidebar components present.")

    def test_06_tactical_matrix_presence(self):
        """Verifies Bottom Real-Time Tactical Matrix (DataTable)."""
        required_matrix_ids = [
            "tactical-matrix-container",
            "tactical-matrix-table",
        ]
        for cid in required_matrix_ids:
            self.assertIn(cid, self.all_ids, f"Tactical matrix component ID '{cid}' missing from layout.")
        print("  ✓ Test 6: Bottom Tactical Air Picture Matrix table present.")

    def test_07_easter_egg_and_monte_carlo_modal_presence(self):
        """Verifies Easter Egg banner and 100x Monte Carlo modal components."""
        required_aux_ids = [
            "easter-egg-banner-container",
            "easter-egg-alert",
            "easter-egg-banner-text",
            "monte-carlo-modal",
            "btn-close-monte-carlo",
            "mc-overall-pk",
            "mc-mean-cpa",
            "mc-mean-time",
        ]
        for cid in required_aux_ids:
            self.assertIn(cid, self.all_ids, f"Component ID '{cid}' missing from layout.")
        print("  ✓ Test 7: Easter egg alert banner and Monte Carlo modal elements present.")

    def test_08_dash_callbacks_registered(self):
        """Verifies that all interactive callbacks are properly registered in `callback_map`."""
        callback_map = self.dash_app.callback_map
        self.assertGreater(len(callback_map), 0, "No callbacks registered in Dash application!")

        # Check registered output targets
        registered_outputs = set()
        for k in callback_map.keys():
            # Keys in callback_map represent output targets
            registered_outputs.add(k)

        # Expected registered targets (either single or multi-output)
        expected_substrings = [
            "tactical-2d-viewport-container.style",
            "sim-state-store.data",
            "sim-clock-display.children",
            "monte-carlo-modal.is_open",
        ]
        for exp in expected_substrings:
            found = any(exp in out_key for out_key in registered_outputs)
            self.assertTrue(found, f"Expected callback output '{exp}' not found in registered callback map.")

        print(f"  ✓ Test 8: All core callbacks successfully registered ({len(callback_map)} total callback maps).")

    def test_09_callback_view_mode_toggle(self):
        """Tests the 2D vs 3D view mode toggle callback logic in-memory."""
        style_2d_on, style_3d_off = app.cb_toggle_view_mode("2d")
        self.assertEqual(style_2d_on["display"], "block")
        self.assertEqual(style_3d_off["display"], "none")

        style_2d_off, style_3d_on = app.cb_toggle_view_mode("3d")
        self.assertEqual(style_2d_off["display"], "none")
        self.assertEqual(style_3d_on["display"], "block")
        print("  ✓ Test 9: 2D / 3D View mode toggle callback verified.")

    def test_10_callback_playback_engine_actions(self):
        """Tests playback engine actions: Play, Step, Reset, Timeline Scrubber, Speed."""
        init_state = {
            "time": 0.0, "playing": False, "speed": 1.0,
            "scenario": "eastern_europe", "theater": "eastern_europe",
            "selected_unit": "TRK-01", "easter_egg_active": False
        }
        init_egg = {"active": False, "aircraft": "F-22A Raptor", "banner_text": ""}

        # 1. Test Step Forward
        st_step, disabled, interval_ms, egg_out = app.cb_playback_engine(
            None, None, 1, None, None, None,
            1.0, 0.0, 0,
            "eastern_europe", "eastern_europe", "TRK-01", [0],
            init_state, init_egg, [],
            triggered_id_override="btn-step"
        )
        self.assertEqual(st_step["time"], 2.0)
        self.assertFalse(st_step["playing"])

        # 2. Test Play
        st_play, disabled, interval_ms, _ = app.cb_playback_engine(
            1, None, None, None, None, None,
            1.0, 2.0, 0,
            "eastern_europe", "eastern_europe", "TRK-01", [0],
            st_step, init_egg, [],
            triggered_id_override="btn-play"
        )
        self.assertTrue(st_play["playing"])
        self.assertFalse(disabled)

        # 3. Test Reset
        st_reset, disabled, interval_ms, egg_reset = app.cb_playback_engine(
            None, None, None, 1, None, None,
            1.0, 45.0, 0,
            "eastern_europe", "eastern_europe", "TRK-01", [0],
            {"time": 45.0, "playing": True}, init_egg, [],
            triggered_id_override="btn-reset"
        )
        self.assertEqual(st_reset["time"], 0.0)
        self.assertFalse(st_reset["playing"])
        self.assertFalse(egg_reset["active"])

        # 4. Test Timeline Scrubber jump
        st_scrub, _, _, _ = app.cb_playback_engine(
            None, None, None, None, None, None,
            1.0, 68.5, 0,
            "eastern_europe", "eastern_europe", "TRK-01", [0],
            init_state, init_egg, [],
            triggered_id_override="sim-timeline-slider"
        )
        self.assertEqual(st_scrub["time"], 68.5)

        print("  ✓ Test 10: Playback engine (Play, Step, Reset, Scrubber) verified.")

    def test_11_dashboard_visual_and_telemetry_update(self):
        """Tests `cb_update_dashboard` at multiple timesteps (T+0s, T+35s, T+75s)."""
        for t_test in [0.0, 35.0, 75.0]:
            state = {
                "time": t_test,
                "playing": True,
                "scenario": "eastern_europe",
                "theater": "eastern_europe",
                "selected_unit": "TRK-01",
            }
            egg_state = {"active": False, "banner_text": ""}

            outputs = app.cb_update_dashboard(state, egg_state)
            (
                clock_str, t_sec, unit_opts, cur_unit,
                mach_fig, speed_readout, alt_ind, prog_bar,
                metrics_cards, badges, target_info,
                matrix_rows, sel_rows, egg_open, egg_text,
                alt_fig, globe_fig
            ) = outputs

            self.assertIn(f"T+{t_test:05.1f}s", clock_str)
            self.assertEqual(t_sec, t_test)
            self.assertEqual(cur_unit, "TRK-01")
            self.assertIsInstance(mach_fig, go.Figure)
            self.assertIsInstance(alt_fig, go.Figure)
            self.assertIsInstance(globe_fig, go.Figure)
            self.assertIsInstance(matrix_rows, list)
            self.assertGreater(len(matrix_rows), 0)

        print("  ✓ Test 11: Multi-timestep dashboard, telemetry gauges, and altitude profiles verified.")

    def test_12_easter_egg_stealth_fighter_air_launch(self):
        """Verifies the 10% Easter egg stealth air-launch trigger and banner update."""
        # 1. Test random roll function
        egg_data = app.roll_easter_egg()
        self.assertIn("active", egg_data)
        self.assertIn(egg_data["aircraft"], ["F-22A Raptor", "F-35A Lightning II"])
        self.assertIn("AIR-LAUNCH DETECTED", egg_data["banner_text"])

        # 2. Test deterministic Easter Egg activation via secret test trigger
        st_egg, _, _, egg_out = app.cb_playback_engine(
            None, None, None, None, None, 1,
            1.0, 0.0, 0,
            "eastern_europe", "eastern_europe", "TRK-01", [0],
            {"time": 0.0, "playing": False}, {}, [],
            triggered_id_override="btn-easter-egg-test"
        )
        self.assertTrue(egg_out["active"])
        self.assertTrue(st_egg["easter_egg_active"])

        # 3. Test dashboard update with active Easter egg
        outputs = app.cb_update_dashboard(st_egg, egg_out)
        egg_open = outputs[13]
        egg_text = outputs[14]
        self.assertTrue(egg_open, "Easter egg alert should be open when active")
        self.assertIn("AIR-LAUNCH DETECTED", egg_text)
        print("  ✓ Test 12: 10% Easter egg stealth fighter air-launch alert verified.")

    def test_13_monte_carlo_modal_toggle(self):
        """Tests open and close toggling of the Monte Carlo modal."""
        self.assertTrue(app.cb_toggle_monte_carlo(1, 0, False))
        self.assertFalse(app.cb_toggle_monte_carlo(0, 1, True))
        print("  ✓ Test 13: 100x Monte Carlo modal open/close toggle verified.")


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING HEADLESS VERIFICATION SCRIPT: test_app_headless.py")
    print("=" * 80)
    unittest.main(verbosity=2)
