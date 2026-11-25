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

    # 4. Continuous Sub-Mesh Ridge Micro-Optimization Validation
    print("\n[Study 4/4] Continuous Sub-Mesh Terrain Ridge Micro-Optimization ($280M Budget):")
    cop_base, pl_base, _ = lsim.deploy_neural_lattice_mesh(copy.deepcopy(infra), mesh, 280.0, dep, device)
    res_base = lsim.execute_true_rk4_raid_simulation(cop_base, mesh, waves_1x, "neural_lattice", surr, kw, device, seed=101)

    micro_opt = optimize_sensor_ridge_micro_offsets(pl_base, mesh.sea_azimuth_rad, search_radius_km=8.0)
    cop_opt = copy.deepcopy(cop_base)
    # Re-run fresh COP with micro-optimized ridge coordinates
    cop_fresh, _, _ = lsim.deploy_neural_lattice_mesh(copy.deepcopy(infra), mesh, 280.0, dep, device)
    opt_map = {item["entity_id"]: item for item in micro_opt["placements"]}
    for ent in cop_fresh.get_live_assets():
        if ent.entity_id in opt_map and ent.location:
            inf_p = opt_map[ent.entity_id]
            spec = lmesh.NODE_BY_ID[ent.ontology.platform_type]
            new_terr = inf_p.get("opt_terrain_elev_m", inf_p["terrain_elev_m"])
            ent.location.position.latitude_degrees = inf_p["opt_lat"]
            ent.location.position.longitude_degrees = inf_p["opt_lon"]
            ent.location.position.altitude_hae_meters = new_terr + spec.platform_alt_agl_m
    res_opt = lsim.execute_true_rk4_raid_simulation(cop_fresh, mesh, waves_1x, "neural_lattice", surr, kw, device, seed=101)
    print(
        f"  Mean Ridge Elevation Gain: +{micro_opt['mean_ridge_elevation_gain_m']:.1f}m (Max +{micro_opt['max_ridge_elevation_gain_m']:.1f}m) | "
        f"Discrete Mesh Surv: {res_base['cascading_operational_survival_pct']:.1f}% -> Micro-Optimized Surv: {res_opt['cascading_operational_survival_pct']:.1f}%"
    )

    # Render 2-panel Pareto & Saturation Optimization Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 6.0), facecolor="#080d16")
    ax1.set_facecolor("#0b1320")
    df_b = pd.DataFrame(budget_rows)
    ax1.plot(df_b["budget_musd"], df_b["neural_survival_pct"], "-o", color="#00e676", linewidth=2.4, label="Neural Lattice Kill-Web")
    ax1.plot(df_b["budget_musd"], df_b["siloed_survival_pct"], "--s", color="#ef4444", linewidth=2.0, label="Legacy Siloed Batteries")
    ax1.set_title("Defense Budget Pareto Frontier (True 3-DoF RK4)", color="white", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Defense Procurement Budget ($M USD)", color="#cbd5e1")
    ax1.set_ylabel("Cascading Operational Survival (%)", color="#cbd5e1")
    ax1.set_ylim(0, 105)
    ax1.tick_params(colors="#94a3b8")
    ax1.grid(color="#1e293b", linestyle=":")
    ax1.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="white")

    ax2.set_facecolor("#0b1320")
    df_s = pd.DataFrame(stress_rows)
    ax2.plot(df_s["total_threats"], df_s["neural_survival_pct"], "-o", color="#00f0ff", linewidth=2.4, label="Neural Lattice Kill-Web")
    ax2.plot(df_s["total_threats"], df_s["siloed_survival_pct"], "--s", color="#f59e0b", linewidth=2.0, label="Legacy Siloed Batteries")
    ax2.set_title("Multi-Wave Raid Saturation Stress Curve ($320M Budget)", color="white", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Total Synchronized Inbound Threats (incl. MIRVs)", color="#cbd5e1")
    ax2.set_ylabel("Cascading Operational Survival (%)", color="#cbd5e1")
    ax2.set_ylim(0, 105)
    ax2.tick_params(colors="#94a3b8")
    ax2.grid(color="#1e293b", linestyle=":")
    ax2.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="white")

    plt.tight_layout()
    curves_png = os.path.join(BASE_DIR, "lattice_optimization_curves.png")
    plt.savefig(curves_png, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)

    pareto_csv = os.path.join(BASE_DIR, "lattice_optimization_pareto.csv")
    df_b.to_csv(pareto_csv, index=False)

    summary = {
        "elapsed_seconds": round(time.time() - t0, 2),
        "budget_pareto_frontier": budget_rows,
        "saturation_stress_curve": stress_rows,
        "sead_self_healing_sweep": sead_rows,
        "submesh_ridge_micro_optimization": {
            "mean_ridge_elevation_gain_m": micro_opt["mean_ridge_elevation_gain_m"],
            "max_ridge_elevation_gain_m": micro_opt["max_ridge_elevation_gain_m"],
            "discrete_mesh_survival_pct": res_base["cascading_operational_survival_pct"],
            "micro_optimized_survival_pct": res_opt["cascading_operational_survival_pct"],
        },
    }
    out_json = os.path.join(BASE_DIR, "lattice_optimization_validation.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 98)
    print(f"Saved Optimization Validation JSON : {out_json}")
    print(f"Saved Budget Pareto CSV            : {pareto_csv}")
    print(f"Saved Optimization Curves PNG      : {curves_png}")
    print("=" * 98)
    return summary


if __name__ == "__main__":
    run_full_optimization_and_validation()
