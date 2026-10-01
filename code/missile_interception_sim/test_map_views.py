#!/usr/bin/env python3
"""
================================================================================
UNIT & INTEGRATION TEST SUITE: MAP_VIEWS.PY
Validates 2D Tactical Leaflet Map, Altitude Profile Chart, 3D Digital Globe,
and Unified Dash Component Architecture
================================================================================
"""

import os
import sys
import json
import plotly.graph_objects as go
from dash import Dash
import dash_leaflet as dl

# Import components from map_views
from map_views import (
    THEATER_PRESETS,
    TILE_CARTO_DARK_MATTER,
    TILE_ESRI_DARK_CANVAS,
    EARTH_RADIUS_KM,
    ATTACKER_LAUNCH_ICON_URI,
    DEFENDER_BATTERY_ICON_URI,
    TARGET_ASSET_ICON_URI,
    THREAT_POSITION_ICON_URI,
    DETONATION_BURST_ICON_URI,
    haversine_distance_km,
    great_circle_intermediate_point,
    lat_lon_to_cartesian,
    generate_trajectory_waypoints,
    generate_interceptor_trajectory,
    build_tactical_leaflet_map,
    build_altitude_profile_figure,
    build_3d_globe_figure,
    build_map_views_container,
    register_map_callbacks
)


def run_tests():
    print("=" * 80)
    print("RUNNING MAP_VIEWS TEST SUITE")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # TEST 1: THEATER PRESETS VERIFICATION
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Verifying Operational Theater Presets...")
    expected_theaters = ["eastern_europe", "persian_gulf", "taiwan_strait", "conus_homeland"]
    for th_key in expected_theaters:
        assert th_key in THEATER_PRESETS, f"Missing theater preset: {th_key}"
        th = THEATER_PRESETS[th_key]
        assert "name" in th and len(th["name"]) > 0
        assert "center" in th and len(th["center"]) == 2
        assert "zoom" in th and isinstance(th["zoom"], int)
        assert len(th["attacker_launch_sites"]) > 0, f"No launch sites in {th_key}"
        assert len(th["defender_batteries"]) > 0, f"No defender batteries in {th_key}"
        assert len(th["target_assets"]) > 0, f"No target assets in {th_key}"
        assert len(th["threat_trajectories"]) > 0, f"No threat trajectories in {th_key}"

        # Coordinate bounds check
        lat, lon = th["center"]
        assert -90.0 <= lat <= 90.0, f"Invalid center lat: {lat}"
        assert -180.0 <= lon <= 180.0, f"Invalid center lon: {lon}"

        for site in th["attacker_launch_sites"]:
            assert -90.0 <= site["lat"] <= 90.0
            assert -180.0 <= site["lon"] <= 180.0
            assert len(site["systems"]) > 0

        for bat in th["defender_batteries"]:
            assert -90.0 <= bat["lat"] <= 90.0
            assert -180.0 <= bat["lon"] <= 180.0
            assert bat.get("wez_radius_km", 0) > 0

        for tgt in th["target_assets"]:
            assert -90.0 <= tgt["lat"] <= 90.0
            assert -180.0 <= tgt["lon"] <= 180.0
            assert tgt.get("strategic_value", 0) > 0

        for threat in th["threat_trajectories"]:
            assert "threat_id" in threat
            assert "speed_mach" in threat
            assert "status" in threat

        print(f"  ✓ Theater '{th['name']}' verified ({len(th['attacker_launch_sites'])} launch sites, "
              f"{len(th['defender_batteries'])} batteries, {len(th['target_assets'])} HVAs, "
              f"{len(th['threat_trajectories'])} trajectories)")

    # --------------------------------------------------------------------------
    # TEST 2: GEODESIC & SPATIAL KINEMATIC UTILITIES
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Verifying Geodesic & Spatial Kinematic Utilities...")
    # Distance Kyiv (50.45, 30.52) to Odesa (46.48, 30.72) ~ 440 km
    dist_kyiv_odesa = haversine_distance_km(50.45, 30.52, 46.48, 30.72)
    assert 400.0 < dist_kyiv_odesa < 480.0, f"Unexpected distance: {dist_kyiv_odesa}"
    print(f"  ✓ Haversine distance Kyiv -> Odesa: {dist_kyiv_odesa:.2f} km")

    # Intermediate midpoint
    mid_lat, mid_lon = great_circle_intermediate_point(50.45, 30.52, 46.48, 30.72, 0.5)
    assert 48.0 < mid_lat < 49.0
    print(f"  ✓ Great circle midpoint: ({mid_lat:.4f}°, {mid_lon:.4f}°)")

    # 3D Cartesian coordinates on sphere
    x, y, z = lat_lon_to_cartesian(0.0, 0.0, alt_km=0.0)
    assert abs(x - EARTH_RADIUS_KM) < 1e-4 and abs(y) < 1e-4 and abs(z) < 1e-4
    print(f"  ✓ Cartesian conversion at equator: x={x:.1f}, y={y:.1f}, z={z:.1f} km")

    # Trajectory generation for ballistic, hypersonic, cruise, drone
    for t_type in ["ballistic", "hypersonic", "cruise", "drone"]:
        wps = generate_trajectory_waypoints(50.45, 30.52, 46.48, 30.72, threat_type=t_type, n_points=20)
        assert len(wps) == 20
        assert all("lat" in wp and "lon" in wp and "alt_km" in wp for wp in wps)
    print("  ✓ Trajectory waypoints generated across ballistic, hypersonic, cruise, and drone classes.")

    # Interceptor flyout trajectory
    int_traj = generate_interceptor_trajectory(50.45, 30.52, 48.5, 30.6, intercept_alt_km=32.0, n_points=15)
    assert len(int_traj) == 15
    assert abs(int_traj[-1]["alt_km"] - 32.0) < 1e-3
    print(f"  ✓ Interceptor trajectory generated: climb from 0 to {int_traj[-1]['alt_km']:.1f} km")

    # --------------------------------------------------------------------------
    # TEST 3: 2D TACTICAL MAP USING DASH-LEAFLET
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Verifying 2D Tactical Leaflet Map Construction & Elements...")
    for th_key in expected_theaters:
        map_container = build_tactical_leaflet_map(theater_key=th_key)
        assert isinstance(map_container, dl.MapContainer), "Must return a dl.MapContainer"

        # Verify Dash serialization
        json_dict = map_container.to_plotly_json()
        assert "props" in json_dict
        props = json_dict["props"]
        assert "center" in props
        assert "zoom" in props
        children = props["children"]
        assert len(children) >= 8, f"Insufficient map children in {th_key}: {len(children)}"

        # Verify element types
        has_tile = False
        draggable_launchers = 0
        draggable_batteries = 0
        wez_circles = 0
        draggable_targets = 0
        polylines = 0
        burst_markers = 0

        for child in children:
            c_name = type(child).__name__
            c_id = getattr(child, "id", None)
            is_drag = getattr(child, "draggable", False)

            if c_name == "TileLayer":
                has_tile = True
            elif c_name == "Marker":
                if isinstance(c_id, dict):
                    m_kind = c_id.get("type", "")
                    if m_kind == "attacker-launch-site":
                        if is_drag:
                            draggable_launchers += 1
                    elif m_kind == "defender-battery":
                        if is_drag:
                            draggable_batteries += 1
                    elif m_kind == "target-asset":
                        if is_drag:
                            draggable_targets += 1
                    elif m_kind in ["detonation-burst-marker", "leaker-impact-marker"]:
                        burst_markers += 1
            elif c_name == "Circle":
                wez_circles += 1
            elif c_name == "Polyline":
                polylines += 1

        assert has_tile, f"TileLayer missing in {th_key}"
        assert draggable_launchers > 0, f"No draggable launchers in {th_key}"
        assert draggable_batteries > 0, f"No draggable batteries in {th_key}"
        assert wez_circles > 0, f"No WEZ circles in {th_key}"
        assert draggable_targets > 0, f"No draggable targets in {th_key}"
        assert polylines > 0, f"No polylines in {th_key}"
        assert burst_markers > 0, f"No burst markers in {th_key}"

        print(f"  ✓ 2D Map for '{th_key}': {len(children)} layers (Launchers: {draggable_launchers}, "
              f"Batteries: {draggable_batteries}, WEZ Circles: {wez_circles}, Targets: {draggable_targets}, "
              f"Polylines: {polylines}, Bursts: {burst_markers})")

    # --------------------------------------------------------------------------
    # TEST 4: ALTITUDE PROFILE CHART (MISSILEMAP STYLE)
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Verifying Altitude Profile Chart (Missilemap style)...")
    for th_key in expected_theaters:
        fig_alt = build_altitude_profile_figure(theater_key=th_key, threat_index=0)
        assert isinstance(fig_alt, go.Figure), "Must return a plotly go.Figure"

        # Check serialization
        fig_dict = fig_alt.to_dict()
        assert "data" in fig_dict and len(fig_dict["data"]) >= 5

        # Check required traces: threat curve, apogee, interceptor curve, kinetic hit
        trace_names = [t.get("name", "") for t in fig_dict["data"]]
        has_threat_curve = any("Threat:" in name for name in trace_names)
        has_apogee = any("Apogee" in name for name in trace_names)
        has_interceptor = any("Interceptor" in name for name in trace_names)
        has_hit = any("Kinetic Intercept" in name or "HIT" in name for name in trace_names)

        assert has_threat_curve, f"Threat curve missing in {th_key} altitude profile"
        assert has_apogee, f"Apogee marker missing in {th_key} altitude profile"
        assert has_interceptor, f"Interceptor climb curve missing in {th_key} altitude profile"
        assert has_hit, f"Kinetic hit marker missing in {th_key} altitude profile"

        # Check axes layout
        layout = fig_dict["layout"]
        assert "xaxis" in layout and "Downrange" in layout["xaxis"]["title"]["text"]
        assert "yaxis" in layout and "Altitude" in layout["yaxis"]["title"]["text"]

        print(f"  ✓ Altitude Profile for '{th_key}': {len(fig_dict['data'])} traces verified (Threat, Apogee, Interceptor, Hit point)")

    # --------------------------------------------------------------------------
    # TEST 5: 3D DIGITAL GLOBE MODE
    # --------------------------------------------------------------------------
    print("\n[TEST 5] Verifying 3D Digital Globe Mode...")
    for th_key in expected_theaters:
        fig_3d = build_3d_globe_figure(theater_key=th_key, show_wez_domes=True, show_bursts=True)
        assert isinstance(fig_3d, go.Figure), "Must return a plotly go.Figure"

        fig_dict = fig_3d.to_dict()
        assert "data" in fig_dict and len(fig_dict["data"]) >= 8

        # Check presence of Earth surface or mesh, coastlines, launch sites, batteries, targets, 3D arcs, bursts
        trace_types = [t.get("type", "") for t in fig_dict["data"]]
        trace_names = [t.get("name", "") for t in fig_dict["data"]]

        assert "surface" in trace_types, f"Earth surface mesh missing in {th_key} 3D globe"
        has_launch_sites = any("Launch Complexes" in name for name in trace_names)
        has_batteries = any("Batteries" in name for name in trace_names)
        has_targets = any("Defended Strategic HVAs" in name for name in trace_names)
        has_3d_arc = any("3D Arc:" in name for name in trace_names)
        has_3d_burst = any("Kinetic Intercept Burst" in name for name in trace_names)

        assert has_launch_sites, f"Launch sites trace missing in {th_key} 3D globe"
        assert has_batteries, f"Defender batteries trace missing in {th_key} 3D globe"
        assert has_targets, f"Target HVAs trace missing in {th_key} 3D globe"
        assert has_3d_arc, f"3D suborbital arc missing in {th_key} 3D globe"
        assert has_3d_burst, f"3D burst marker missing in {th_key} 3D globe"

        # Check camera eye
        scene = fig_dict["layout"]["scene"]
        camera_eye = scene["camera"]["eye"]
        assert "x" in camera_eye and "y" in camera_eye and "z" in camera_eye

        print(f"  ✓ 3D Globe for '{th_key}': {len(fig_dict['data'])} traces verified (Camera eye: x={camera_eye['x']:.2f}, y={camera_eye['y']:.2f}, z={camera_eye['z']:.2f})")

    # --------------------------------------------------------------------------
    # TEST 6: UNIFIED DASH VIEW CONTAINER & CALLBACK REGISTRATION
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Verifying Unified Dashboard Component Layout & Callbacks...")
    layout = build_map_views_container(theater_key="eastern_europe", default_mode="2d")
    assert hasattr(layout, "to_plotly_json"), "Layout must be a Dash Component"

    # Instantiate test Dash app and register callbacks
    test_app = Dash(__name__)
    test_app.layout = layout
    register_map_callbacks(test_app)

    # Verify callback count
    assert len(test_app.callback_map) >= 2, f"Expected at least 2 callbacks registered, got {len(test_app.callback_map)}"
    print(f"  ✓ Unified layout created and {len(test_app.callback_map)} callbacks successfully registered.")

    # --------------------------------------------------------------------------
    # TEST 7: EXPORT SAMPLE DEMO ARTIFACTS
    # --------------------------------------------------------------------------
    print("\n[TEST 7] Exporting verification figures to HTML artifacts...")
    os.makedirs("test_output", exist_ok=True)

    alt_demo = build_altitude_profile_figure(theater_key="eastern_europe", threat_index=0)
    alt_demo_path = "test_output/altitude_profile_demo.html"
    alt_demo.write_html(alt_demo_path, include_plotlyjs="cdn")
    assert os.path.exists(alt_demo_path) and os.path.getsize(alt_demo_path) > 1000

    globe_demo = build_3d_globe_figure(theater_key="eastern_europe")
    globe_demo_path = "test_output/globe_3d_demo.html"
    globe_demo.write_html(globe_demo_path, include_plotlyjs="cdn")
    assert os.path.exists(globe_demo_path) and os.path.getsize(globe_demo_path) > 1000

    print(f"  ✓ Exported '{alt_demo_path}' ({os.path.getsize(alt_demo_path):,} bytes)")
    print(f"  ✓ Exported '{globe_demo_path}' ({os.path.getsize(globe_demo_path):,} bytes)")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED CLEANLY! (7/7 TEST SUITES SUCCESSFUL)")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
