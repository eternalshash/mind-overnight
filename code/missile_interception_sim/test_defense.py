#!/usr/bin/env python3
"""
================================================================================
TEST SUITE: INTEGRATED AIR AND MISSILE DEFENSE (IAMD)
File: test_defense.py

Verifies:
1. 3D True Proportional Navigation (TPN) Guidance & Dynamic G-limits
2. Continuous Sub-timestep Closest Point of Approach (CPA) anti-tunneling math
3. Lethal Kill Radius logic (15 m kinetic HTK, 30 m blast frag, 5 m CIWS burst)
4. Multi-Tier Layered IAMD Fire Control & Threat Allocation:
   - Tier 1: SM-3 Block IIA / THAAD (> 40 km)
   - Tier 2: Patriot PAC-3 MSE (5-38 km, ballistic & hypersonic)
   - Tier 3: Anduril Roadrunner-M / Tamir (0.1-10 km, drones & cruise)
   - Tier 4: Phalanx 20mm LPWS Point Defense (< 3.5 km)
5. Operational Firing Doctrines:
   - Shoot-Look-Shoot (SLS) with BDA handoff
   - Salvo of 2 (staggered dual-launch)
   - Automatic (Weapons Free) vs. Manual (Operator Auth) modes
6. Mixed Raid Tactical Engagement:
   - 1x 9K720 Iskander-M (Quasi-Ballistic)
   - 1x Kh-47M2 Kinzhal (Hypersonic Aero-Ballistic)
   - 2x Shahed-136 (Low-altitude UAVs)
   - 1x Cruise Missile (Terminal CIWS leaker test)
7. Monte Carlo Batch Runner (100 runs):
   - Randomized launch headings, atmospheric winds, seeker angular noise
   - Aggregate Pk, miss distance distributions, and timing statistics
================================================================================
"""

import sys
import time
import numpy as np
import pandas as pd

from defense_system import (
    G0,
    DefenseTier,
    FiringDoctrine,
    FireAuthorizationMode,
    InterceptorType,
    ThreatType,
    EngagementStatus,
    DEFAULT_INTERCEPTOR_CONFIGS,
    DefenderBattery,
    Threat,
    create_threat,
    compute_substep_cpa,
    calculate_tpn_acceleration,
    check_lethal_detonation,
    DefenseScenario,
    run_single_simulation,
    run_monte_carlo,
)


def run_unit_tests():
    """Validates mathematical and physical subroutines."""
    print("=" * 80)
    print("TEST 1: MATHEMATICAL & GUIDANCE SUBROUTINE VERIFICATION")
    print("=" * 80)

    # 1. Sub-timestep CPA Tunneling Verification
    # Closing speed: Mach 12 (4,080 m/s), dt = 0.05 s
    # Threat at (100.0, 3.0, 0.0), vel = (-2000, 0, 0)
    # Interceptor at (0.0, 0.0, 0.0), vel = (2080, 0, 0)
    # At t=0: dist = 100.04 m. At t=dt: dist = 104.04 m.
    # Without sub-step CPA: both endpoints > 100 m => false miss!
    r_t = np.array([100.0, 3.0, 0.0])
    v_t = np.array([-2000.0, 0.0, 0.0])
    r_i = np.array([0.0, 0.0, 0.0])
    v_i = np.array([2080.0, 0.0, 0.0])
    dt = 0.05

    d_start = float(np.linalg.norm(r_t - r_i))
    d_end = float(np.linalg.norm((r_t + v_t * dt) - (r_i + v_i * dt)))

    tau, d_cpa, p_t_cpa, p_i_cpa = compute_substep_cpa(r_t, v_t, r_i, v_i, dt)
    kill_htk = check_lethal_detonation(d_cpa, 15.0)

    print("Sub-timestep CPA Tunneling Test (Mach 12 Closing Velocity):")
    print(f"  Step Start Distance: {d_start:.2f} m | Step End Distance: {d_end:.2f} m")
    print(f"  CPA Offset tau:      {tau*1000:.2f} ms (clamped to [0, {dt*1000:.0f}] ms)")
    print(f"  Continuous CPA Dist: {d_cpa:.2f} m | Lethal Radius: 15.0 m")
    print(f"  Lethal Kill Result:  {'SUCCESS (HIT)' if kill_htk else 'FAIL'}")

    assert abs(d_cpa - 3.0) < 1e-3, f"Expected CPA ~3.0m, got {d_cpa}"
    assert kill_htk is True, "Expected lethal hit within 15m kill radius"
    print("  => Anti-tunneling sub-timestep CPA passed successfully!\n")

    # 2. 3D TPN Guidance Law & G-limit Verification
    # Interceptor at origin, target off-axis at (2000, 200, 0)
    r_rel = np.array([2000.0, 200.0, 0.0])
    v_t = np.array([-1500.0, 0.0, 0.0])
    v_i = np.array([1800.0, 0.0, 0.0])

    # Test PAC-3 MSE (30G limit)
    a_cmd_pac3, a_mag_pac3 = calculate_tpn_acceleration(
        r_target=r_rel,
        v_target=v_t,
        r_int=np.zeros(3),
        v_int=v_i,
        n_nav=4.0,
        g_limit=30.0,
    )
    a_limit_pac3 = 30.0 * G0

    # Test Roadrunner-M (15G limit)
    a_cmd_rr, a_mag_rr = calculate_tpn_acceleration(
        r_target=r_rel,
        v_target=v_t,
        r_int=np.zeros(3),
        v_int=v_i,
        n_nav=3.8,
        g_limit=15.0,
    )
    a_limit_rr = 15.0 * G0

    print("3D True Proportional Navigation (TPN) & G-limit Test:")
    print(f"  PAC-3 MSE Commanded: ||a_cmd|| = {a_mag_pac3:.1f} m/s^2 | Clamped to: {np.linalg.norm(a_cmd_pac3):.1f} m/s^2 (Limit: {a_limit_pac3:.1f} m/s^2)")
    print(f"  Roadrunner Commanded: ||a_cmd|| = {a_mag_rr:.1f} m/s^2 | Clamped to: {np.linalg.norm(a_cmd_rr):.1f} m/s^2 (Limit: {a_limit_rr:.1f} m/s^2)")
    print(f"  Commanded Direction: a_cmd[y] = {a_cmd_pac3[1]:.2f} (positive steers toward target)")

    assert np.linalg.norm(a_cmd_pac3) <= a_limit_pac3 + 1e-4, "PAC-3 G-limit exceeded"
    assert np.linalg.norm(a_cmd_rr) <= a_limit_rr + 1e-4, "Roadrunner G-limit exceeded"
    assert a_cmd_pac3[1] > 0.0, "TPN should command positive lateral steering toward target"
    print("  => 3D TPN and dynamic structural G-limits verified successfully!\n")


def build_standard_defense_grid(hva_pos: np.ndarray) -> list:
    """Builds a 4-tier layered IAMD battery defense grid guarding the HVA."""
    return [
        # Tier 1: SM-3 Block IIA / THAAD (forward exo-atmospheric shield)
        DefenderBattery(
            battery_id="BAT_T1_SM3",
            name="THAAD / SM-3 Site Alpha",
            tier=DefenseTier.TIER_1_EXO,
            config=DEFAULT_INTERCEPTOR_CONFIGS[InterceptorType.SM3_BLOCK_IIA],
            pos=np.array([40000.0, 0.0, 0.0]),
            magazine_capacity=12,
            missiles_remaining=12,
        ),
        # Tier 2: Patriot PAC-3 MSE (mid-altitude / hypersonic shield)
        DefenderBattery(
            battery_id="BAT_T2_PAC3",
            name="Patriot PAC-3 MSE Battery Bravo",
            tier=DefenseTier.TIER_2_ENDO,
            config=DEFAULT_INTERCEPTOR_CONFIGS[InterceptorType.PAC3_MSE],
            pos=np.array([75000.0, -8000.0, 0.0]),
            magazine_capacity=16,
            missiles_remaining=16,
        ),
        # Tier 3: Anduril Roadrunner-M (drone & cruise SHORAD)
        DefenderBattery(
            battery_id="BAT_T3_ROADRUNNER",
            name="Anduril Roadrunner-M Nest Charlie",
            tier=DefenseTier.TIER_3_SHORAD,
            config=DEFAULT_INTERCEPTOR_CONFIGS[InterceptorType.ROADRUNNER_M],
            pos=np.array([82000.0, 8000.0, 0.0]),
            magazine_capacity=16,
            missiles_remaining=16,
        ),
        # Tier 4: Phalanx CIWS LPWS (close-in point defense at HVA)
        DefenderBattery(
            battery_id="BAT_T4_CIWS",
            name="Phalanx 20mm LPWS Mount Delta",
            tier=DefenseTier.TIER_4_CIWS,
            config=DEFAULT_INTERCEPTOR_CONFIGS[InterceptorType.PHALANX_CIWS],
            pos=hva_pos.copy(),
            magazine_capacity=24,
            missiles_remaining=24,
        ),
    ]


def test_mixed_raid_shoot_look_shoot():
    """
    Tests layered multi-tier defense against a mixed aggressor raid:
    - 1x 9K720 Iskander-M (Quasi-Ballistic, 12G terminal weave)
    - 1x Kh-47M2 Kinzhal (Hypersonic Aero-Ballistic, Mach 10)
    - 2x Shahed-136 Drones (Low-altitude loitering UAVs)
    - 1x Cruise Missile (Low-altitude leaker)
    Firing Doctrine: Shoot-Look-Shoot (SLS) with Automatic Fire Authorization.
    """
    print("=" * 80)
    print("TEST 2: MIXED RAID ENGAGEMENT (SHOOT-LOOK-SHOOT & AUTOMATIC ENGAGEMENT)")
    print("=" * 80)

    hva_pos = np.array([90000.0, 0.0, 0.0]) # High Value Asset at 90 km downrange
    batteries = build_standard_defense_grid(hva_pos)

    threats = [
        # Threat 1 (Tier 1 Target): Ballistic IRBM (Apogee 75 km, Exo-atmospheric SM-3 engagement)
        create_threat(
            threat_type=ThreatType.BALLISTIC_HIGH,
            threat_id=101,
            launch_x=0.0,
            launch_y=0.0,
            launch_z=75000.0,
            target_pos=hva_pos,
            launch_time=0.0,
        ),
        # Threat 2 (Tier 2 Target): Iskander-M (Quasi-ballistic, Mach 6.2, 12G terminal weave)
        create_threat(
            threat_type=ThreatType.ISKANDER_QUASI_BALLISTIC,
            threat_id=102,
            launch_x=0.0,
            launch_y=12000.0,
            launch_z=0.0,
            target_pos=hva_pos,
            launch_time=0.0,
        ),
        # Threat 3 (Tier 2 Target): Kinzhal Hypersonic (Mach 10, steep dive)
        create_threat(
            threat_type=ThreatType.KINZHAL_HYPERSONIC,
            threat_id=103,
            launch_x=10000.0,
            launch_y=-10000.0,
            launch_z=30000.0,
            target_pos=hva_pos,
            launch_time=2.0,
        ),
        # Threat 4 (Tier 3 Target): Shahed-136 Drone North Flank (Low & slow, 150m alt)
        create_threat(
            threat_type=ThreatType.SHAHED_DRONE,
            threat_id=104,
            launch_x=70000.0,
            launch_y=15000.0,
            launch_z=150.0,
            target_pos=hva_pos,
            launch_time=0.0,
        ),
        # Threat 5 (Tier 3 Target): Shahed-136 Drone South Flank (Low & slow, 180m alt)
        create_threat(
            threat_type=ThreatType.SHAHED_DRONE,
            threat_id=105,
            launch_x=68000.0,
            launch_y=-14000.0,
            launch_z=180.0,
            target_pos=hva_pos,
            launch_time=1.0,
        ),
        # Threat 6 (Tier 4 Target): Cruise Missile Leaker breaching perimeter inside 3.5 km
        create_threat(
            threat_type=ThreatType.CRUISE_MISSILE,
            threat_id=106,
            launch_x=88000.0,
            launch_y=500.0,
            launch_z=80.0,
            target_pos=hva_pos,
            launch_time=6.0,
        ),
    ]

    scenario = DefenseScenario(
        name="Mixed_Raid_SLS",
        target_asset_pos=hva_pos,
        batteries=batteries,
        threats=threats,
        firing_doctrine=FiringDoctrine.SHOOT_LOOK_SHOOT,
        auth_mode=FireAuthorizationMode.AUTOMATIC,
        dt=0.02,
        max_time=100.0,
    )

    result = run_single_simulation(scenario, verbose=True)

    print("\n--- ENGAGEMENT LOG ---")
    df_eng = pd.DataFrame(result.engagement_records)
    print(df_eng[["threat_name", "battery_id", "tier", "kill", "miss_distance", "intercept_time", "intercept_altitude"]].to_string(index=False))

    print(f"\nRaid Results: Neutralized {result.threats_killed}/{result.total_threats} threats | Pk: {result.pk:.1%}")
    assert result.pk >= 0.80, f"Expected Pk >= 80%, got {result.pk:.1%}"
    print("  => Mixed raid Shoot-Look-Shoot engagement successfully verified!\n")


def test_salvo_and_manual_authorization():
    """
    Verifies:
    1. Firing Doctrine: "Salvo of 2" (staggered dual-launch).
    2. Operational Mode: Manual Authorization (Weapons Tight -> Operator Auth).
    """
    print("=" * 80)
    print("TEST 3: SALVO OF 2 & MANUAL FIRE AUTHORIZATION DOCTRINE")
    print("=" * 80)

    hva_pos = np.array([90000.0, 0.0, 0.0])
    batteries = build_standard_defense_grid(hva_pos)

    # Difficult Kinzhal hypersonic threat
    threat_kinzhal = create_threat(
        threat_type=ThreatType.KINZHAL_HYPERSONIC,
        threat_id=201,
        launch_x=15000.0,
        launch_y=5000.0,
        launch_z=30000.0,
        target_pos=hva_pos,
        launch_time=0.0,
    )

    # 1. Test Manual Authorization Mode (hold fire until authorized)
    from defense_system import IAMDFireControlSystem

    fcs_manual = IAMDFireControlSystem(
        batteries=batteries,
        firing_doctrine=FiringDoctrine.SALVO_OF_2,
        auth_mode=FireAuthorizationMode.MANUAL,
    )
    fcs_manual.register_threat(threat_kinzhal)

    # Step at t=0.5s: should be awaiting authorization
    fcs_manual.step(0.5, 0.02)
    assert 201 in fcs_manual.pending_authorizations, "Threat should be pending authorization"
    assert len(fcs_manual.active_interceptors) == 0, "No interceptors should launch without auth"
    print("  Step 1: Threat detected -> queued in pending authorizations (Weapons Tight confirmed).")

    # Authorize fire
    fcs_manual.authorize_fire(201)
    fcs_manual.step(0.6, 0.02)
    print(f"  Step 2: Operator authorized fire -> Interceptors dispatched: {len(fcs_manual.active_interceptors)} (Salvo mode)")
    assert len(fcs_manual.active_interceptors) >= 1, "Interceptors should launch after operator authorization"

    # 2. Run full simulation under Salvo of 2 doctrine
    salvo_batteries = build_standard_defense_grid(hva_pos)
    salvo_threat = create_threat(
        threat_type=ThreatType.KINZHAL_HYPERSONIC,
        threat_id=202,
        launch_x=15000.0,
        launch_y=5000.0,
        launch_z=30000.0,
        target_pos=hva_pos,
        launch_time=0.0,
    )
    scenario_salvo = DefenseScenario(
        name="Kinzhal_Salvo_Test",
        target_asset_pos=hva_pos,
        batteries=salvo_batteries,
        threats=[salvo_threat],
        firing_doctrine=FiringDoctrine.SALVO_OF_2,
        auth_mode=FireAuthorizationMode.AUTOMATIC,
        dt=0.02,
        max_time=60.0,
    )

    salvo_result = run_single_simulation(scenario_salvo, verbose=False)
    print(f"  Salvo Results: Interceptors Fired = {salvo_result.total_interceptors_fired} | Pk = {salvo_result.pk:.1%}")
    assert salvo_result.total_interceptors_fired >= 2, "Salvo of 2 should fire at least 2 interceptors"
    assert salvo_result.threats_killed == 1, "Target should be killed by salvo"
    print("  => Salvo of 2 doctrine and Manual Authorization verified successfully!\n")


def test_monte_carlo_batch():
    """
    Executes a 100-run Monte Carlo batch evaluation:
    - Mixed raid (Iskander + Kinzhal + 2 Shahed-136)
    - Randomized launch headings (+/- 8 deg)
    - Randomized atmospheric winds
    - Randomized seeker angular measurement errors
    """
    print("=" * 80)
    print("TEST 4: MONTE CARLO 100-RUN BATCH EVALUATION")
    print("=" * 80)

    hva_pos = np.array([90000.0, 0.0, 0.0])
    base_batteries = build_standard_defense_grid(hva_pos)

    base_threats = [
        create_threat(ThreatType.ISKANDER_QUASI_BALLISTIC, 1, 0.0, 10000.0, 0.0, hva_pos, launch_time=0.0),
        create_threat(ThreatType.KINZHAL_HYPERSONIC, 2, 10000.0, -8000.0, 30000.0, hva_pos, launch_time=1.0),
        create_threat(ThreatType.SHAHED_DRONE, 3, 72000.0, 12000.0, 150.0, hva_pos, launch_time=0.0),
        create_threat(ThreatType.SHAHED_DRONE, 4, 70000.0, -12000.0, 180.0, hva_pos, launch_time=1.0),
    ]

    base_scenario = DefenseScenario(
        name="MonteCarlo_Base_Scenario",
        target_asset_pos=hva_pos,
        batteries=base_batteries,
        threats=base_threats,
        firing_doctrine=FiringDoctrine.SHOOT_LOOK_SHOOT,
        auth_mode=FireAuthorizationMode.AUTOMATIC,
        dt=0.02,
        max_time=80.0,
    )

    t0 = time.time()
    mc_summary = run_monte_carlo(base_scenario, num_runs=100, seed=42, verbose=True)
    elapsed = time.time() - t0

    print("\n" + "=" * 80)
    print(f"MONTE CARLO RESULTS: 100 RUNS ({mc_summary.total_threats_simulated} TOTAL THREAT ENGAGEMENTS)")
    print(f"Batch Execution Wall Time: {elapsed:.2f} seconds ({elapsed/100:.3f} s/run)")
    print("=" * 80)
    print(f"Overall Probability of Kill (Pk):  {mc_summary.overall_pk:.2%}")
    print(f"Mean Miss Distance:                 {mc_summary.mean_miss_distance:.2f} m")
    print(f"Median Miss Distance:               {mc_summary.median_miss_distance:.2f} m")
    print(f"Std Dev Miss Distance:              {mc_summary.std_miss_distance:.2f} m")
    print(f"Mean Interception Time:             {mc_summary.mean_intercept_time:.2f} s")
    print(f"Mean Interceptor Expenditure:       {mc_summary.mean_ammo_expended:.1f} missiles / raid")

    print("\n--- Pk Breakdown By Threat Type ---")
    for t_type, pk_val in mc_summary.pk_by_threat_type.items():
        print(f"  * {t_type:<45}: Pk = {pk_val:.1%}")

    print("\n--- Pk Breakdown By Defense Tier ---")
    tier_names = {1: "Tier 1 (SM-3 / THAAD)", 2: "Tier 2 (PAC-3 MSE)", 3: "Tier 3 (Roadrunner-M)", 4: "Tier 4 (Phalanx CIWS)"}
    for tier_id, pk_val in mc_summary.pk_by_tier.items():
        t_label = tier_names.get(tier_id, f"Tier {tier_id}")
        print(f"  * {t_label:<30}: Pk = {pk_val:.1%}")

    assert mc_summary.overall_pk >= 0.85, f"Monte Carlo overall Pk below threshold: {mc_summary.overall_pk:.1%}"
    print("\n  => Monte Carlo batch validation passed with flying colors!")


if __name__ == "__main__":
    start_total = time.time()
    print("\n================================================================================")
    print("STARTING COMPLETE IAMD DEFENSE SYSTEM VERIFICATION SUITE")
    print("================================================================================\n")

    run_unit_tests()
    test_mixed_raid_shoot_look_shoot()
    test_salvo_and_manual_authorization()
    test_monte_carlo_batch()

    total_time = time.time() - start_total
    print("\n================================================================================")
    print(f"ALL TESTS PASSED SUCCESSFULLY! Total Test Runtime: {total_time:.2f} s")
    print("================================================================================\n")
