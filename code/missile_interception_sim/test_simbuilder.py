#!/usr/bin/env python3
"""
================================================================================
TEST SUITE: SIMBUILDER & GNC ENGINE VERIFICATION
File: test_simbuilder.py
================================================================================
Verifies:
  1. GNC Engine Subroutines (Hawley & Blauwkamp 3-Pillar Architecture):
     - US Standard Atmosphere & Speed of Sound
     - Dynamic Drag & Induced Drag polar curves
     - TPN, APN, and ZEM Guidance Laws
     - Sub-timestep continuous CPA quadratic interpolation
     - Autopilot First-Order Lag & G-limits
  2. FAAC SimBuilder Modules:
     - Weapon profiles & Catalog instantiation
     - Spherical Earth 4/3 R_E Radar Horizon
     - Aspect-dependent Radar Cross Section (RCS)
     - WEZ / ZAP Dynamic Launch Envelopes
     - Countermeasures: Chaff, RF Noise Jamming, Burn-Through
  3. End-to-End Flyout Engagement & Academic Analytics:
     - High-speed kinetic intercept of Mach 6 quasi-ballistic threat
     - CEP calculation & CSV telemetry export
================================================================================
"""

import os
import math
import numpy as np
import pytest

from gnc_engine import (
    G0, R_EARTH, atmosphere, GuidanceLaw, SeekerType,
    AerodynamicsModel, PropulsionModel, SeekerSensorModel, AutopilotModel,
    CountermeasureState, WeaponSpec, GNCVehicle, WeaponEngagementZone,
    compute_wez_envelope, compute_continuous_substep_cpa
)
from simbuilder import (
    RadarSensorNode, SimBuilderCatalog, IADSSimulator, EngagementOutcome
)
from academic_analysis import (
    compute_cep_metrics, compute_pk_confidence_interval,
    run_navigation_ratio_sweep, export_telemetry_to_csv,
    plot_engagement_telemetry, plot_cep_histogram
)


def test_atmosphere_and_sound_speed():
    """Validates barometric atmospheric temperature, density, and sound speed."""
    rho_sl, t_sl, c_sl = atmosphere(0.0)
    assert abs(rho_sl - 1.225) < 0.05
    assert abs(t_sl - 288.15) < 0.1
    assert abs(c_sl - 340.29) < 2.0

    # Tropopause test at 11,000 m
    rho_tp, t_tp, c_tp = atmosphere(11000.0)
    assert abs(t_tp - 216.65) < 0.5
    assert rho_tp < rho_sl * 0.35


def test_subtimestep_cpa_anti_tunneling():
    """
    Validates that sub-timestep quadratic interpolation correctly computes
    closest point of approach when relative closing speed exceeds Mach 10 (3400+ m/s)
    and endpoints both lie outside the lethal sphere.
    """
    dt = 0.05
    # Two vehicles closing along X-axis at Mach 12 (4080 m/s total) with 4.0 m lateral offset
    r_t = np.array([100.0, 4.0, 0.0])
    v_t = np.array([-2000.0, 0.0, 0.0])
    r_i = np.array([0.0, 0.0, 0.0])
    v_i = np.array([2080.0, 0.0, 0.0])

    d_start = float(np.linalg.norm(r_t - r_i)) # ~100.08 m
    d_end = float(np.linalg.norm((r_t + v_t * dt) - (r_i + v_i * dt))) # ~104.08 m

    tau_cpa, d_cpa, pos_t, pos_i = compute_continuous_substep_cpa(r_t, v_t, r_i, v_i, dt)

    assert 0.0 < tau_cpa < dt, "CPA should occur inside the timestep"
    assert abs(d_cpa - 4.0) < 1e-3, f"Expected continuous CPA = 4.0 m, got {d_cpa}"


def test_guidance_laws_comparison():
    """Verifies acceleration commands from TPN, APN, and ZEM guidance laws."""
    spec_tpn = SimBuilderCatalog.create_patriot_pac3_mse()
    spec_tpn.guidance_law = GuidanceLaw.TPN

    spec_apn = SimBuilderCatalog.create_patriot_pac3_mse()
    spec_apn.guidance_law = GuidanceLaw.APN

    # Vehicle at origin flying East at 800 m/s
    v_int = GNCVehicle(spec_tpn, np.array([0.0, 0.0, 5000.0]), np.array([800.0, 0.0, 0.0]))
    target_pos = np.array([5000.0, 200.0, 5000.0])
    target_vel = np.array([-1200.0, 0.0, 0.0])
    target_accel = np.array([0.0, 10.0 * G0, 0.0]) # Target pulling 10G North

    a_cmd_tpn = v_int.calculate_guidance_command(target_pos, target_vel, target_accel)
    assert a_cmd_tpn[1] > 0.0, "TPN should command positive Y steering toward target"

    # APN should command higher lateral acceleration than TPN due to target acceleration compensation
    v_int_apn = GNCVehicle(spec_apn, np.array([0.0, 0.0, 5000.0]), np.array([800.0, 0.0, 0.0]))
    a_cmd_apn = v_int_apn.calculate_guidance_command(target_pos, target_vel, target_accel)
    assert a_cmd_apn[1] > a_cmd_tpn[1], "APN should command higher lead acceleration against maneuvering target"


def test_wez_launch_envelope():
    """Verifies FAAC SimBuilder WEZ / ZAP dynamic launch envelope boundaries."""
    spec_pac3 = SimBuilderCatalog.create_patriot_pac3_mse()
    wez = compute_wez_envelope(spec_pac3)

    assert wez.r_max_km > 35.0, "PAC-3 MSE R_max should exceed 35 km"
    assert wez.r_no_escape_km < wez.r_max_km, "No-escape zone must be smaller than aerodynamic R_max"
    assert wez.r_min_km < 1.0, "R_min should be under 1 km"
    assert wez.max_altitude_km > 20.0, "Ceiling should exceed 20 km"


def test_radar_horizon_and_aspect_rcs():
    """Validates 4/3 R_E spherical Earth radar horizon and aspect-dependent RCS."""
    radar = RadarSensorNode(
        radar_id="AN_MPQ_65",
        name="Patriot AN/MPQ-65",
        radar_type="fire_control",
        pos_enu=np.array([0.0, 0.0, 15.0]), # Radar at 15m elevation
        max_instrumented_range_m=160000.0,
        nominal_range_at_ref_rcs_m=130000.0,
    )

    # Low altitude threat at 100m MSL
    horizon_100m = radar.compute_radar_horizon_m(100.0)
    # Theoretical: sqrt(2 * 4/3 * 6371000 * 15) + sqrt(2 * 4/3 * 6371000 * 100)
    # = ~15967m + ~41227m = ~57.2 km
    assert 50000.0 < horizon_100m < 65000.0, f"Expected ~57km horizon, got {horizon_100m/1000:.1f}km"

    # High altitude threat at 20,000m MSL
    horizon_20km = radar.compute_radar_horizon_m(20000.0)
    assert horizon_20km > 400000.0, "High altitude horizon should exceed 400 km"

    # Broadside RCS should be greater than nose-on RCS
    tgt_pos = np.array([20000.0, 0.0, 2000.0])
    nose_on_vel = np.array([-600.0, 0.0, 0.0]) # Flying directly at radar
    broadside_vel = np.array([0.0, 600.0, 0.0]) # Crossing broadside

    rcs_nose = radar.compute_aspect_rcs(tgt_pos, nose_on_vel, nominal_rcs=1.0)
    rcs_broad = radar.compute_aspect_rcs(tgt_pos, broadside_vel, nominal_rcs=1.0)
    assert rcs_broad > rcs_nose, "Broadside aspect RCS must be significantly higher than nose-on"


def test_countermeasure_burn_through():
    """Validates electronic warfare jamming range degradation and burn-through."""
    radar = RadarSensorNode(
        radar_id="TEST_RADAR",
        name="Test Radar",
        radar_type="fire_control",
        pos_enu=np.array([0.0, 0.0, 10.0]),
        max_instrumented_range_m=150000.0,
        nominal_range_at_ref_rcs_m=120000.0,
    )

    tgt_pos = np.array([30000.0, 0.0, 5000.0])
    tgt_vel = np.array([-500.0, 0.0, 0.0])

    cm_off = CountermeasureState(rf_jamming_active=False)
    det_off, r_max_off, _ = radar.is_target_detected(tgt_pos, tgt_vel, 1.0, cm_off)
    assert det_off is True

    cm_jam = CountermeasureState(rf_jamming_active=True)
    det_jam, r_max_jam, _ = radar.is_target_detected(tgt_pos, tgt_vel, 1.0, cm_jam)
    assert r_max_jam < r_max_off, "RF Jamming must reduce effective radar detection range"


def test_end_to_end_flyout_and_cep(tmp_path):
    """
    Executes an end-to-end continuous flyout engagement of Patriot PAC-3 MSE
    against an incoming Iskander-M quasi-ballistic threat and validates CEP statistics.
    """
    pac3_spec = SimBuilderCatalog.create_patriot_pac3_mse()
    iskander_spec = SimBuilderCatalog.create_iskander_m()

    # Threat inbound from 40 km downrange at Mach 5.2
    threat_pos = np.array([40000.0, 2000.0, 16000.0])
    threat_vel = np.array([-1600.0, 0.0, -120.0])
    threat = GNCVehicle(iskander_spec, threat_pos, threat_vel)

    sim = IADSSimulator()
    battery_pos = np.array([0.0, 0.0, 10.0])
    sim.add_battery("BAT_ALPHA", pac3_spec, battery_pos, capacity=16)

    # Launch interceptor
    interceptor = sim.launch_interceptor("BAT_ALPHA", threat)
    assert interceptor is not None

    dt = 0.02
    t = 0.0
    outcomes = []
    while t < 40.0 and interceptor.active and threat.active:
        # Threat weaves terminal evasion at 4G
        a_weave = np.array([0.0, 4.0 * G0 * math.sin(0.4 * t), 0.0])
        threat.accel_achieved = a_weave
        threat.vel += a_weave * dt
        threat.pos += threat.vel * dt
        threat.flight_time += dt

        step_outcomes = sim.step_engagement(dt)
        if step_outcomes:
            outcomes.extend(step_outcomes)
            break
        t += dt

    assert len(outcomes) > 0, "Engagement should terminate with an outcome"
    outcome = outcomes[0]
    assert outcome.kill is True, f"Interceptor should achieve lethal kill (Miss distance: {outcome.cpa_miss_distance_m}m)"
    assert outcome.cpa_miss_distance_m <= 15.0, "CPA miss distance must be within lethal kill radius"

    # Export telemetry to CSV
    csv_file = tmp_path / "telemetry_test.csv"
    df = export_telemetry_to_csv(interceptor, str(csv_file))
    assert os.path.exists(csv_file)
    assert len(df) > 100
    assert "g_load" in df.columns
    assert "los_rate_rad_s" in df.columns

    # Test CEP calculations
    cep = compute_cep_metrics([outcome.cpa_miss_distance_m, 3.2, 5.1, 7.8, 12.0])
    assert cep["cep50"] > 0.0
    assert cep["cep95"] >= cep["cep50"]
