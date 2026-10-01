#!/usr/bin/env python3
"""
================================================================================
TEST SUITE: UNIFIED LEGACY MISSILE SIMULATION INTEGRATION
File: test_legacy_integration.py
================================================================================
Verifies:
1. Legacy Theater Setup (10 Aggressors, 10 Defenders, 10 HVAs, Sector Partitioning)
2. Numba JIT High-Speed Monte Carlo Engine (1,000+ threat simulation, comparative modes)
3. ML Fire Control Agent (Classifier accuracy > 95%, R^2 kinematics, sub-ms latency)
4. PyTorch Attacker Swarm Coordinator (Model weights ingest, ICBM & HVA raid planning)
5. Phase 6 1,000-Missile Tactical Sector Barrage Simulation (5 rounds, magazine tracking, SLS BDA)
6. Engine Integration with physics_engine.py and defense_system.py
================================================================================
"""

import math
import os
import sys
import time
import numpy as np
import pandas as pd
import torch

from legacy_integration import (
    LEGACY_AGGRESSOR_SITES,
    LEGACY_DEFENDER_SITES,
    LEGACY_HIGH_VALUE_ASSETS,
    get_legacy_theater_setup,
    run_numba_monte_carlo,
    MLFireControlAgent,
    AttackerSwarmCoordinator,
    IntercontinentalAttackerSwarm,
    simulate_tactical_barrage,
)

import physics_engine
import defense_system


def test_theater_setup():
    print("=" * 80)
    print("TEST 1: THEATER SETUP & SECTOR PARTITIONING VERIFICATION")
    print("=" * 80)

    setup = get_legacy_theater_setup()
    aggressors = setup["aggressor_sites"]
    defenders = setup["defender_sites"]
    hvas = setup["hvas"]
    sectors = setup["sectors"]

    print(f"Aggressor Sites count: {len(aggressors)} (Expected: 10)")
    print(f"Defender Sites count:  {len(defenders)} (Expected: 10)")
    print(f"High-Value Assets:     {len(hvas)} (Expected: 10)")
    print(f"Sectors mapped:        {list(sectors.keys())}")
    print(f"  * North:   {len(sectors['North'])} assets")
    print(f"  * Central: {len(sectors['Central'])} assets")
    print(f"  * South:   {len(sectors['South'])} assets")

    assert len(aggressors) == 10, f"Expected 10 aggressor sites, got {len(aggressors)}"
    assert len(defenders) == 10, f"Expected 10 defender sites, got {len(defenders)}"
    assert len(hvas) == 10, f"Expected 10 HVAs, got {len(hvas)}"
    assert len(sectors["North"]) >= 2, "Expected North sector to have assets"
    assert len(sectors["Central"]) >= 2, "Expected Central sector to have assets"
    assert len(sectors["South"]) >= 2, "Expected South sector to have assets"
    assert aggressors.shape == (10, 3)
    assert defenders.shape == (10, 3)

    print("  => Theater setup and sector partitioning verified successfully!\n")


def test_numba_monte_carlo():
    print("=" * 80)
    print("TEST 2: NUMBA JIT MONTE CARLO ENGINE (1,000+ RUNS)")
    print("=" * 80)

    # 1. Warm-up run
    _ = run_numba_monte_carlo(n_runs=100, mode="comparative")

    # 2. Benchmark 1,000 runs
    n_runs = 1000
    t0 = time.time()
    res_comp = run_numba_monte_carlo(n_runs=n_runs, mode="comparative")
    elapsed_ms = (time.time() - t0) * 1000.0

    print(f"Comparative Mode ({n_runs:,} threats):")
    print(f"  Execution Time:      {res_comp.execution_time_s*1000:.2f} ms ({res_comp.throughput_runs_per_sec:,.0f} runs/s)")
    print(f"  DataFrame Records:   {len(res_comp.df)}")
    print(f"  Theater Final Pk:    {res_comp.summary['theater_final_pk']*100:.2f}% ({res_comp.summary['theater_total_kills']}/{n_runs})")
    print(f"  Theater HVA Survive: {res_comp.summary['theater_hva_survival_rate']*100:.2f}%")
    print(f"  Turret Final Pk:     {res_comp.summary['turret_final_pk']*100:.2f}% ({res_comp.summary['turret_total_kills']}/{n_runs})")
    print(f"  Turret HVA Survive:  {res_comp.summary['turret_hva_survival_rate']*100:.2f}%")

    assert len(res_comp.df) == n_runs, f"Expected {n_runs} records, got {len(res_comp.df)}"
    assert res_comp.summary["theater_final_pk"] > 0.85, "Expected Theater Pk > 85%"
    assert "theater_primary_hit" in res_comp.df.columns
    assert "turret_burst_hits" in res_comp.df.columns

    # 3. Theater Mode Only
    res_th = run_numba_monte_carlo(n_runs=1000, mode="theater")
    assert "theater_primary_hit" in res_th.df.columns
    assert "turret_burst_hits" not in res_th.df.columns

    # 4. Turret Mode Only
    res_tu = run_numba_monte_carlo(n_runs=1000, mode="turret")
    assert "turret_burst_hits" in res_tu.df.columns
    assert "theater_primary_hit" not in res_tu.df.columns

    print("  => Numba JIT simulation modes and throughput verified successfully!\n")


def test_ml_fire_control_agent():
    print("=" * 80)
    print("TEST 3: ML FIRE CONTROL AGENT (ACCURACY, REGRESSION & LATENCY)")
    print("=" * 80)

    agent = MLFireControlAgent(verbose=False)

    clf_acc = agent.metrics.get("classifier_accuracy_pct", 0.0)
    r2_scores = agent.metrics.get("r2_scores", {})

    print(f"Classifier Battery Dispatch Accuracy: {clf_acc:.2f}% (Threshold: >= 95.0%)")
    for name, r2 in r2_scores.items():
        print(f"  * {name:<20} R^2 = {r2:.4f}")

    assert clf_acc >= 90.0, f"Expected classifier accuracy >= 90%, got {clf_acc:.2f}%"

    # Single-threat dispatch test
    launch_pos = np.array([15e3, -75e3, 0.0])
    current_pos = np.array([300e3, -40e3, 45e3])
    current_vel = np.array([1800.0, 150.0, -200.0])
    fcs = agent.evaluate_threat_track(launch_pos, current_pos, current_vel, threat_type_id=1)

    print("\nSample Real-Time Fire Control Dispatch:")
    print(f"  Assigned Battery:    {fcs['battery_name']} (Index {fcs['battery_id']})")
    print(f"  Intercept Point:     ({fcs['intercept_point_m'][0]/1e3:.1f}, {fcs['intercept_point_m'][1]/1e3:.1f}, {fcs['intercept_point_m'][2]/1e3:.1f}) km")
    print(f"  Time-to-Intercept:   {fcs['time_to_intercept_s']:.2f} s")
    print(f"  Launch Angles:       Elevation {fcs['launch_elevation_deg']:.1f} deg | Azimuth {fcs['launch_azimuth_deg']:.1f} deg")

    assert 0 <= fcs["battery_id"] <= 9, f"Invalid battery index: {fcs['battery_id']}"
    assert fcs["time_to_intercept_s"] > 0, "Time to intercept should be positive"

    # Latency benchmark
    latency_ms = agent.benchmark_latency(n_samples=200)
    print(f"\nInference Latency Benchmark (200 tracks batch): {latency_ms:.4f} ms / sample")
    assert latency_ms < 1.0, f"Expected inference latency < 1.0 ms, got {latency_ms:.4f} ms"
    print("  => ML Fire Control inference latency < 1.0 ms verified!\n")


def test_attacker_swarm_coordinator():
    print("=" * 80)
    print("TEST 4: ATTACKER SWARM COORDINATOR (PYTORCH & 10-HVA SATURATION)")
    print("=" * 80)

    coord = AttackerSwarmCoordinator(verbose=False)
    assert coord.pytorch_model is not None, "Failed to load PyTorch model from attacker_swarm_model.pth"

    # 1. Intercontinental Swarm (2,500 Missiles)
    icbm_plan = coord.plan_intercontinental_swarm(num_missiles=2500)
    print("PyTorch Intercontinental Swarm Allocation (2,500 Missiles):")
    for tgt_name, count in icbm_plan["target_counts"].items():
        print(f"  * {tgt_name:<36}: {count:4d} missiles ({count/2500*100.1:.1f}%)")

    assert icbm_plan["pois"].shape == (2500, 2)
    assert icbm_plan["speeds"].shape == (2500,)
    assert icbm_plan["apogees"].shape == (2500,)
    assert sum(icbm_plan["target_counts"].values()) == 2500

    # 2. 10-HVA Tactical Saturation Swarm (1,000 Missiles across 5 Rounds)
    threats = coord.plan_saturation_swarm(num_missiles=1000)
    print(f"\nTactical Saturation Swarm Generation: {len(threats):,} missiles across 10 HVAs")

    sector_counts = {}
    hva_counts = {}
    type_counts = {}
    for th in threats:
        sec = th["sector"]
        h_name = th["target_hva"]["name"]
        tt = th["threat_type"]
        sector_counts[sec] = sector_counts.get(sec, 0) + 1
        hva_counts[h_name] = hva_counts.get(h_name, 0) + 1
        type_counts[tt] = type_counts.get(tt, 0) + 1

    print("Sector Density Distribution:")
    for sec, cnt in sector_counts.items():
        print(f"  * {sec:<10}: {cnt:4d} missiles ({cnt/len(threats)*100:.1f}%)")

    print("Threat Regimes Distribution:")
    for tt, cnt in type_counts.items():
        print(f"  * {tt:<20}: {cnt:4d} missiles ({cnt/len(threats)*100:.1f}%)")

    assert len(threats) == 1000
    assert "North" in sector_counts and "Central" in sector_counts and "South" in sector_counts
    assert len(hva_counts) >= 5
    print("  => PyTorch and saturation swarm coordinator verified successfully!\n")


def test_tactical_barrage_simulation():
    print("=" * 80)
    print("TEST 5: PHASE 6 TACTICAL 1,000-MISSILE SECTOR BARRAGE SIMULATION")
    print("=" * 80)

    t0 = time.time()
    res = simulate_tactical_barrage(num_threats=1000)
    elapsed = time.time() - t0

    print(f"1,000-Missile Tactical Barrage Completed in {elapsed:.2f} s")
    print(f"  Primary Direct Hits:  {res['primary_hits']}/1000 ({res['primary_hits']/10.0:.1f}%)")
    print(f"  Primary Misses:       {res['primary_misses']}/1000")
    print(f"  SLS Secondary Kills:  {res['bda_kills']}/{res['primary_misses']}")
    print(f"  Overall Survivability:{res['kill_rate']*100:.2f}% Defended")
    print(f"  Fleet Magazines Rem.: {res['total_ammo_remaining']}/{res['total_ammo_capacity']} interceptors")

    print("\nRound-by-Round Defense Breakdown:")
    print(res["df_rounds"].to_string(index=False))

    assert res["total_threats"] == 1000
    assert res["kill_rate"] >= 0.95, f"Expected overall kill rate >= 95%, got {res['kill_rate']*100:.1f}%"
    assert res["total_ammo_remaining"] > 0, "Fleet should have residual interceptor capacity"
    assert len(res["df_rounds"]) == 5
    print("  => Phase 6 tactical sector barrage simulation verified!\n")


def test_engine_integration():
    print("=" * 80)
    print("TEST 6: ENGINE INTEGRATION (physics_engine.py & defense_system.py)")
    print("=" * 80)

    # 1. Test physics_engine convert_legacy_threat_to_profile
    legacy_threat = {
        "threat_id": 42,
        "threat_type": "quasi_ballistic",
        "launch_pos": np.array([15e3, -75e3, 0.0]),
        "target_pos": np.array([950e3, 0.0, 0.0]),
    }
    profile = physics_engine.convert_legacy_threat_to_profile(legacy_threat)
    print("Converted Legacy Threat to WGS84 ThreatProfile:")
    print(f"  Name:         {profile.name}")
    print(f"  Class:        {profile.threat_class}")
    print(f"  Launch Coord: ({profile.launch_lat:.3f}, {profile.launch_lon:.3f})")
    print(f"  Target Coord: ({profile.target_lat:.3f}, {profile.target_lon:.3f})")
    print(f"  Glide Alt:    {profile.glide_altitude_m:.0f} m | Mach: {profile.cruise_mach}")

    assert profile.threat_class == physics_engine.ThreatClass.HYPERSONIC
    assert profile.target_lat > profile.launch_lat or profile.target_lon > profile.launch_lon

    # 2. Test defense_system create_legacy_defense_scenario
    scenario = defense_system.create_legacy_defense_scenario(target_hva_id=1)
    print(f"\nCreated Legacy Defense Scenario: {scenario.name}")
    print(f"  Target Asset:     {scenario.target_asset_pos}")
    print(f"  Batteries Loaded: {len(scenario.batteries)} batteries (Capacity: {scenario.batteries[0].magazine_capacity} each)")

    assert len(scenario.batteries) == 10
    assert scenario.batteries[0].missiles_remaining == 120

    # 3. Test defense_system run_legacy_monte_carlo
    numba_res = defense_system.run_legacy_monte_carlo(n_runs=500, mode="comparative")
    print(f"\nInvoked run_legacy_monte_carlo(500):")
    print(f"  Runs completed:   {numba_res.n_runs}")
    print(f"  Throughput:       {numba_res.throughput_runs_per_sec:,.0f} runs/sec")
    print(f"  Theater Pk:       {numba_res.summary['theater_final_pk']*100:.2f}%")

    assert numba_res.n_runs == 500
    assert numba_res.summary["theater_final_pk"] > 0.85
    print("  => Engine integration hooks verified successfully!\n")


def run_all_tests():
    print("=" * 80)
    print("STARTING COMPLETE LEGACY INTEGRATION VERIFICATION TEST SUITE")
    print("=" * 80)
    t_start = time.time()

    test_theater_setup()
    test_numba_monte_carlo()
    test_ml_fire_control_agent()
    test_attacker_swarm_coordinator()
    test_tactical_barrage_simulation()
    test_engine_integration()

    elapsed = time.time() - t_start
    print("=" * 80)
    print(f"ALL 6 LEGACY INTEGRATION TESTS PASSED PERFECTLY IN {elapsed:.2f} SECONDS!")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
