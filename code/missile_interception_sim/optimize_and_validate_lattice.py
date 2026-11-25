#!/usr/bin/env python3
"""
================================================================================
LATTICE MESH & KILL-WEB OPTIMIZATION STRESS TESTS & VALIDATION SUITE
File: optimize_and_validate_lattice.py
================================================================================
Executes 4 rigorous post-training optimization & stress-validation studies inside
TRUE 3-DoF RK4 WGS84 physics:

1. Defense Budget Pareto Frontier ($120M -> $460M):
   Measures cascading infrastructure survival, intercept rate, and cost-exchange
   efficiency of Neural Lattice Kill-Web vs. Legacy Siloed Defense across budgets.
2. Multi-Wave Saturation Stress Curve (1.0x -> 3.0x Raid Multipliers):
   Identifies the exact magazine-exhaustion knee under extreme saturation raids.
3. SEAD Node-Attrition Self-Healing Sweep (0 -> 4 Destroyed Forward Nodes):
   Validates Lattice RF/SATCOM mesh self-healing & Engage-on-Remote continuity.
4. Sub-Mesh Ridge Coordinate Micro-Optimization:
   Tests local continuous hill-climbing around `LatticeMeshDeploymentNet`'s discrete
   geodesic mesh vertices to verify near-optimality and squeeze maximum 35m horizon!
================================================================================
"""

from __future__ import annotations

import copy
import json
import math
import os
import time
from typing import Any, Dict, List

os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lattice_mesh as lmesh
import lattice_sim_engine as lsim
import run_lattice_wargame as rlw
import train_lattice_m3_ultra as tlm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def optimize_sensor_ridge_micro_offsets(
    cop_placements: List[Dict[str, Any]],
    sea_azimuth_rad: float,
    search_radius_km: float = 8.0,
) -> Dict[str, Any]:
    """
    Continuous local sub-mesh terrain ridge hill-climb around Neural Mesh placements:
    Searches a 5x5 sub-kilometer micro-grid around each ground sensor/battery to find
    peak local ridgeline elevation and verify 35m sea-skimmer horizon gain.
    """
    gains_m: List[float] = []
    optimized_coords: List[Dict[str, Any]] = []

    for p in cop_placements:
        base_lat, base_lon = p["lat"], p["lon"]
        base_elev = lmesh.procedural_global_terrain_elevation_m(base_lat, base_lon, sea_azimuth_rad)
        if base_elev <= 0.5 or p["node_type_id"] == "altius_600_isr_picket":
            optimized_coords.append({**p, "opt_lat": base_lat, "opt_lon": base_lon, "elev_gain_m": 0.0})
            continue

        cos_c = max(0.15, math.cos(math.radians(base_lat)))
        best_lat, best_lon, best_elev = base_lat, base_lon, base_elev
        for d_n in np.linspace(-search_radius_km, search_radius_km, 7):
            for d_e in np.linspace(-search_radius_km, search_radius_km, 7):
                clat = base_lat + d_n / 111.132
                clon = base_lon + d_e / (111.320 * cos_c)
                celev = lmesh.procedural_global_terrain_elevation_m(clat, clon, sea_azimuth_rad)
                if celev > best_elev:
                    best_lat, best_lon, best_elev = clat, clon, celev

        gain = round(best_elev - base_elev, 1)
        gains_m.append(gain)
        optimized_coords.append({
            **p,
            "opt_lat": round(best_lat, 5),
            "opt_lon": round(best_lon, 5),
            "opt_terrain_elev_m": round(best_elev, 1),
            "elev_gain_m": gain,
        })

    return {
        "nodes_micro_optimized": len(gains_m),
        "mean_ridge_elevation_gain_m": round(float(np.mean(gains_m)) if gains_m else 0.0, 2),
        "max_ridge_elevation_gain_m": round(float(np.max(gains_m)) if gains_m else 0.0, 2),
        "placements": optimized_coords,
    }


def run_full_optimization_and_validation() -> Dict[str, Any]:
    t0 = time.time()
    surr, dep, kw, device = tlm.load_trained_lattice_models()

    reg = copy.deepcopy(lmesh.GLOBAL_TEST_REGIONS["taiwan_silicon_shield"])
    infra = reg["infrastructure"]
    sea_az = reg["sea_azimuth_deg"]
    mesh = lmesh.generate_geodesic_spatial_mesh(infra, sea_azimuth_deg=sea_az)
    waves_1x = rlw.build_multi_wave_tot_strike(infra, sea_az, "combined_tot_saturation", attack_mult=1.0)

    print("=" * 98)
    print("LATTICE KILL-WEB POST-DEPLOYMENT OPTIMIZATION & STRESS VALIDATION SUITE")
    print("=" * 98)

    # 1. Defense Budget Pareto Sweep ($120M -> $440M)
    print("\n[Study 1/4] Defense Budget Pareto Frontier Sweep ($120M -> $440M):")
    budget_rows = []
    for b_musd in (120.0, 200.0, 280.0, 360.0, 440.0):
        cop_n, pl_n, _ = lsim.deploy_neural_lattice_mesh(copy.deepcopy(infra), mesh, b_musd, dep, device)
        res_n = lsim.execute_true_rk4_raid_simulation(cop_n, mesh, waves_1x, "neural_lattice", surr, kw, device, seed=101)

        cop_s, _, _ = lsim.deploy_baseline_defense("siloed_legacy", copy.deepcopy(infra), mesh, b_musd)
        res_s = lsim.execute_true_rk4_raid_simulation(cop_s, mesh, waves_1x, "siloed_greedy", seed=101)

        delta = res_n["cascading_operational_survival_pct"] - res_s["cascading_operational_survival_pct"]
        print(
            f"  Budget ${b_musd:5.0f}M -> Neural Lattice Surv: {res_n['cascading_operational_survival_pct']:5.1f}% "
            f"(Kills {res_n['intercept_rate_pct']:5.1f}%) | Siloed Surv: {res_s['cascading_operational_survival_pct']:5.1f}% "
            f"| Lattice Gain: {delta:+5.1f}%"
        )
        budget_rows.append({
            "study": "budget_pareto",
            "budget_musd": b_musd,
            "neural_survival_pct": res_n["cascading_operational_survival_pct"],
            "siloed_survival_pct": res_s["cascading_operational_survival_pct"],
            "neural_intercept_pct": res_n["intercept_rate_pct"],
            "siloed_intercept_pct": res_s["intercept_rate_pct"],
            "neural_shot_spend_musd": res_n["interceptor_spend_musd"],
            "nodes_deployed": len(pl_n),
        })

    # 2. Saturation Stress Multiplier Curve (1.0x, 1.5x, 2.0x, 3.0x)
    print("\n[Study 2/4] Multi-Wave Saturation Raid Stress Curve ($320M Defense Budget):")
    stress_rows = []
    for mult in (1.0, 1.5, 2.0, 3.0):
        waves_m = rlw.build_multi_wave_tot_strike(infra, sea_az, "combined_tot_saturation", attack_mult=mult)
        cop_n, _, _ = lsim.deploy_neural_lattice_mesh(copy.deepcopy(infra), mesh, 320.0, dep, device)
        res_n = lsim.execute_true_rk4_raid_simulation(cop_n, mesh, waves_m, "neural_lattice", surr, kw, device, seed=101)

        cop_s, _, _ = lsim.deploy_baseline_defense("siloed_legacy", copy.deepcopy(infra), mesh, 320.0)
        res_s = lsim.execute_true_rk4_raid_simulation(cop_s, mesh, waves_m, "siloed_greedy", seed=101)

        print(
            f"  Raid {mult:3.1f}x ({res_n['total_threats_with_mirvs']:3d} threats) -> "
            f"Neural Lattice Surv: {res_n['cascading_operational_survival_pct']:5.1f}% ({res_n['threats_neutralized']}/{res_n['total_threats_with_mirvs']} kills) | "
            f"Siloed Surv: {res_s['cascading_operational_survival_pct']:5.1f}% ({res_s['threats_neutralized']}/{res_s['total_threats_with_mirvs']} kills)"
        )
        stress_rows.append({
            "raid_multiplier": mult,
            "total_threats": res_n["total_threats_with_mirvs"],
            "neural_survival_pct": res_n["cascading_operational_survival_pct"],
            "siloed_survival_pct": res_s["cascading_operational_survival_pct"],
            "neural_kills": res_n["threats_neutralized"],
            "siloed_kills": res_s["threats_neutralized"],
        })

    # 3. SEAD Node-Attrition Mesh Self-Healing Validation
    print("\n[Study 3/4] Pre-Raid SEAD Node-Attrition & Mesh Self-Healing Resilience ($300M Budget):")
    sead_rows = []
    for k_drop in (0, 1, 2, 3):
        cop_n, _, _ = lsim.deploy_neural_lattice_mesh(copy.deepcopy(infra), mesh, 300.0, dep, device)
        live_a = cop_n.get_live_assets()
        for d_i in range(min(k_drop, max(0, len(live_a) - 2))):
            live_a[d_i].is_live = False
        mesh_stat = lmesh.update_self_healing_mesh_links(cop_n.get_live_assets(), cop_n.get_infrastructure_entities())
        res_n = lsim.execute_true_rk4_raid_simulation(cop_n, mesh, waves_1x, "neural_lattice", surr, kw, device, seed=101)
        online_pct = 100.0 * mesh_stat["online_nodes"] / max(1, mesh_stat["total_live_nodes"])
        print(
            f"  Destroyed Nodes: {k_drop} -> Surviving Mesh Online: {online_pct:5.1f}% "
            f"(Mean Hops: {mesh_stat['mean_hops']:.2f}) | Operational Survival: {res_n['cascading_operational_survival_pct']:5.1f}%"
        )
        sead_rows.append({
            "nodes_destroyed": k_drop,
            "mesh_online_pct": round(online_pct, 1),
            "mean_hops": mesh_stat["mean_hops"],
            "operational_survival_pct": res_n["cascading_operational_survival_pct"],
        })
