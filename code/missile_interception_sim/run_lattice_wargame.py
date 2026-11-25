#!/usr/bin/env python3
"""
================================================================================
POST-TRAINING LATTICE GAUNTLET & CUSTOM RED-TEAM STRIKE WARGAME CLI
File: run_lattice_wargame.py
================================================================================
Provides zero-GUI, rigorous scientific testing of the trained Neural Lattice
Commander inside TRUE 3-DoF RK4 WGS84 physics:

1. `--mode gauntlet` (Default):
   Runs the 4-Part Post-Training Verification Suite across unseen global
   infrastructure clusters (`taiwan_silicon_shield`, `hormuz_energy_corridor`,
   `pacific_nw_strategic_corridor`, `baltic_nordic_shield`):
     - Test 1: Zero-Shot Unseen Global Geography Generalization
     - Test 2: Same-$B Budget Ablation (Lattice Neural Kill-Web vs. Legacy
               Siloed Batteries vs. Heuristic Ring Defense)
     - Test 3: SEAD Radar-Destruction & Heavy Jamming Mesh Self-Healing Test
     - Test 4: Asymmetric 40-Drone Bait + Synchronized ToT Hypersonic/MIRV Trap
   Exports `lattice_gauntlet_results.json`, `lattice_gauntlet_summary.csv`,
   `lattice_cop_snapshot.json`, `lattice_tasks_stream.json`, and high-res static
   Spatial Mesh & Coverage diagnostic figures (`lattice_mesh_diagnostic.png`).

2. `--plan <path.json>` or `--interactive`:
   Lets the user pit any custom Global Attack Plan (custom world HVAs, launch
   coordinates/submarines/bombers, weapon mix, Time-on-Target synchronization,
   budget $B, and attack multiplier) directly against the learned Neural Brain!
================================================================================
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import lattice_mesh as lmesh
import lattice_sim_engine as lsim
import train_lattice_m3_ultra as tlm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==============================================================================
# 1. STANDARDIZED MULTI-WAVE RED-TEAM STRIKE GENERATORS
# ==============================================================================

def build_multi_wave_tot_strike(
    infra_nodes: List[lmesh.CrucialInfraNode],
    sea_azimuth_deg: float,
    preset_style: str = "combined_tot_saturation",
    attack_mult: float = 1.0,
) -> List[lsim.StrikeWaveSpec]:
    """
    Constructs realistic synchronized Time-on-Target (ToT) multi-wave strikes
    originating from offshore submarines, air-launch corridors, and inland TELs.
    """
    c_lat = sum(n.lat for n in infra_nodes) / len(infra_nodes)
    c_lon = sum(n.lon for n in infra_nodes) / len(infra_nodes)
    cos_c = max(0.15, math.cos(math.radians(c_lat)))
    az_r = math.radians(sea_azimuth_deg)

    def offset_coord(dist_km: float, bearing_offset_deg: float) -> Tuple[float, float]:
        b = az_r + math.radians(bearing_offset_deg)
        dlat = (dist_km * math.cos(b)) / 111.132
        dlon = (dist_km * math.sin(b)) / (111.320 * cos_c)
        return round(c_lat + dlat, 4), round(c_lon + dlon, 4)

    scale = max(1, int(round(attack_mult)))
    ids = [n.node_id for n in infra_nodes]

    # Launch coordinates along maritime, flank, and deep ballistic corridors
    l_drone_1 = offset_coord(210.0, -28.0)
    l_drone_2 = offset_coord(195.0, +32.0)
    l_sub_cruise = offset_coord(340.0, -10.0)
    l_bomber_stealth = offset_coord(420.0, +42.0)
    l_tbm_tel = offset_coord(520.0, +5.0)
    l_hgv_brigade = offset_coord(920.0, -15.0)
    l_icbm_field = offset_coord(2400.0, +18.0)

    if preset_style == "sead_and_jamming_surge":
        return [
            # Wave 1 (ToT = 260s): Anti-radar SEAD hunters + Drone bait with heavy EW jamming!
            lsim.StrikeWaveSpec("lancet_3", 4 * scale, l_drone_1[0], l_drone_1[1], "SEAD_RADAR", tot_arrival_window_s=240.0, ew_jamming_boost=0.35),
            lsim.StrikeWaveSpec("kh_47m2_kinzhal", 2 * scale, l_bomber_stealth[0], l_bomber_stealth[1], "SEAD_RADAR", tot_arrival_window_s=245.0, ew_jamming_boost=0.40),
            lsim.StrikeWaveSpec("shahed_136", 10 * scale, l_drone_2[0], l_drone_2[1], ids[0], tot_arrival_window_s=255.0, ew_jamming_boost=0.25),
            # Wave 2 (ToT = 315s): Post-SEAD sea-skimming cruise + Iskander + DF-17 HGV follow-up!
            lsim.StrikeWaveSpec("storm_shadow", 4 * scale, l_bomber_stealth[0], l_bomber_stealth[1], ids[1 % len(ids)], tot_arrival_window_s=310.0, ew_jamming_boost=0.35),
            lsim.StrikeWaveSpec("kalibr_3m54", 4 * scale, l_sub_cruise[0], l_sub_cruise[1], ids[2 % len(ids)], tot_arrival_window_s=315.0, ew_jamming_boost=0.30),
            lsim.StrikeWaveSpec("iskander_m", 3 * scale, l_tbm_tel[0], l_tbm_tel[1], ids[0], tot_arrival_window_s=320.0, ew_jamming_boost=0.35),
            lsim.StrikeWaveSpec("df_17", 2 * scale, l_hgv_brigade[0], l_hgv_brigade[1], ids[3 % len(ids)], tot_arrival_window_s=322.0, ew_jamming_boost=0.30),
        ]

    if preset_style == "drone_bait_cost_trap":
        return [
            # Wave 1 (ToT = 280s): 28 cheap drones ($0.035M-$0.08M) designed to empty $4M-$24M SAM tubes!
            lsim.StrikeWaveSpec("shahed_136", 16 * scale, l_drone_1[0], l_drone_1[1], ids[0], tot_arrival_window_s=275.0),
            lsim.StrikeWaveSpec("anduril_bolt_m", 8 * scale, l_drone_2[0], l_drone_2[1], ids[1 % len(ids)], tot_arrival_window_s=280.0),
            lsim.StrikeWaveSpec("switchblade_600", 4 * scale, l_drone_1[0], l_drone_1[1], ids[2 % len(ids)], tot_arrival_window_s=282.0),
            # Wave 2 (ToT = 345s): High-end hypersonic, supersonic ramjet & MIRV decapitation strike 60s later!
            lsim.StrikeWaveSpec("brahmos", 4 * scale, l_sub_cruise[0], l_sub_cruise[1], ids[2 % len(ids)], tot_arrival_window_s=340.0),
            lsim.StrikeWaveSpec("3m22_zircon", 3 * scale, l_sub_cruise[0], l_sub_cruise[1], ids[0], tot_arrival_window_s=345.0),
            lsim.StrikeWaveSpec("df_17", 3 * scale, l_hgv_brigade[0], l_hgv_brigade[1], ids[1 % len(ids)], tot_arrival_window_s=348.0),
            lsim.StrikeWaveSpec("minuteman_iii", 1 * scale, l_icbm_field[0], l_icbm_field[1], ids[3 % len(ids)], tot_arrival_window_s=352.0),
        ]

    # Default `combined_tot_saturation`: Full-spectrum synchronized Time-on-Target strike!
    return [
        lsim.StrikeWaveSpec("shahed_136", 10 * scale, l_drone_1[0], l_drone_1[1], ids[0], tot_arrival_window_s=290.0),
        lsim.StrikeWaveSpec("anduril_barracuda_500", 4 * scale, l_drone_2[0], l_drone_2[1], ids[1 % len(ids)], tot_arrival_window_s=295.0),
        lsim.StrikeWaveSpec("bgm_109_tomahawk", 4 * scale, l_sub_cruise[0], l_sub_cruise[1], ids[2 % len(ids)], tot_arrival_window_s=300.0),
        lsim.StrikeWaveSpec("brahmos", 3 * scale, l_sub_cruise[0], l_sub_cruise[1], ids[3 % len(ids)], tot_arrival_window_s=305.0),
        lsim.StrikeWaveSpec("iskander_m", 3 * scale, l_tbm_tel[0], l_tbm_tel[1], ids[0], tot_arrival_window_s=310.0),
        lsim.StrikeWaveSpec("df_17", 2 * scale, l_hgv_brigade[0], l_hgv_brigade[1], ids[2 % len(ids)], tot_arrival_window_s=312.0),
        lsim.StrikeWaveSpec("minuteman_iii", 1 * scale, l_icbm_field[0], l_icbm_field[1], ids[1 % len(ids)], tot_arrival_window_s=318.0),
    ]


# ==============================================================================
# 2. STATIC SPATIAL MESH & DIAGNOSTIC VISUALIZATION EXPORTER
# ==============================================================================

def render_spatial_mesh_diagnostic_plot(
    region_title: str,
    infra_nodes: List[lmesh.CrucialInfraNode],
    mesh: lmesh.GeodesicSpatialMesh,
    placements: List[Dict[str, Any]],
    raid_result: Dict[str, Any],
    gauntlet_df: pd.DataFrame,
    out_path: str,
) -> None:
    """
    Renders a clean 2-panel high-resolution diagnostic figure:
      Left:  3D Terrain-Masked Geodesic Spatial Mesh, Crucial Infrastructure
             Debris Keep-Out Perimeters, and Neural Lattice Node Placements.
      Right: Same-Budget ($B) Post-Training Ablation Scorecard across all 4 tests.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.2), facecolor="#080d16")

    # Panel 1: Geodesic Spatial Mesh & Learned Lattice Deployment
    ax1.set_facecolor("#0b1320")
    low_hor_km = mesh.features[:, 2] * 140.0
    sc = ax1.scatter(
        mesh.lons, mesh.lats, c=low_hor_km, cmap="viridis", s=34, alpha=0.68,
        edgecolors="#1e293b", linewidths=0.5, label="Geodesic Mesh (Color = 35m Horizon km)", zorder=2,
    )
    cbar = plt.colorbar(sc, ax=ax1, fraction=0.042, pad=0.02)
    cbar.set_label("3D Terrain-Masked 35m Radar Horizon (km)", color="#cbd5e1", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="#cbd5e1")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="#cbd5e1", fontsize=8)

    # Plot Crucial Infrastructure & Debris Keep-Out Rings
    cos_c = max(0.15, math.cos(math.radians(mesh.center_lat)))
    for inf in infra_nodes:
        ax1.scatter(inf.lon, inf.lat, marker="*", s=240, c="#fbbf24", edgecolors="white", linewidths=1.0, zorder=6)
        ang = np.linspace(0, 2 * np.pi, 48)
        ko_lat = inf.lat + (inf.debris_keep_out_km / 111.132) * np.cos(ang)
        ko_lon = inf.lon + (inf.debris_keep_out_km / (111.320 * cos_c)) * np.sin(ang)
        ax1.plot(ko_lon, ko_lat, linestyle="--", linewidth=1.0, color="#f59e0b", alpha=0.65, zorder=4)
        ax1.annotate(
            inf.name[:22], (inf.lon, inf.lat), xytext=(4, 5), textcoords="offset points",
            color="#fde68a", fontsize=7.5, fontweight="bold", zorder=7,
        )

    # Plot Learned Lattice Placements by Role
    role_styles = {
        "sensor": ("^", "#00f0ff", "Forward Sensor / ALTIUS ISR"),
        "ew": ("D", "#c084fc", "Soft-Kill EW Jammer Dome"),
        "shooter": ("s", "#10b981", "Multi-Tier Kinetic Shooter"),
    }
    seen_roles = set()
    for p in placements:
        mk, col, lbl = role_styles.get(p["role"], ("o", "#ffffff", "Node"))
        use_lbl = lbl if p["role"] not in seen_roles else None
        seen_roles.add(p["role"])
        ax1.scatter(p["lon"], p["lat"], marker=mk, s=95, c=col, edgecolors="white", linewidths=0.9, label=use_lbl, zorder=8)

    # Plot Intercept Detonation Points
    int_ev = [e for e in raid_result.get("intercept_events", []) if "int_lat" in e]
    if int_ev:
        ax1.scatter(
            [e["int_lon"] for e in int_ev], [e["int_lat"] for e in int_ev],
            marker="x", s=55, c="#fde047", linewidths=1.5, label="3-DoF RK4 Intercepts", zorder=9,
        )

    ax1.set_title(f"Learned Lattice Spatial Mesh Deployment\n{region_title}", color="white", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Longitude (deg)", color="#cbd5e1", fontsize=9.5)
    ax1.set_ylabel("Latitude (deg)", color="#cbd5e1", fontsize=9.5)
    ax1.tick_params(colors="#94a3b8", labelsize=8.5)
    ax1.grid(color="#1e293b", linestyle=":", linewidth=0.7)
    ax1.legend(loc="lower left", facecolor="#0f172a", edgecolor="#334155", labelcolor="white", fontsize=7.8)

    # Panel 2: Quantitative Post-Training Gauntlet Comparison
    ax2.set_facecolor("#0b1320")
    if not gauntlet_df.empty:
        piv = gauntlet_df.pivot(index="scenario", columns="architecture", values="cascading_operational_survival_pct")
        cols_order = [c for c in ["Neural Lattice Kill-Web", "Heuristic Ring Mesh", "Legacy Siloed Batteries"] if c in piv.columns]
        piv = piv[cols_order]
        x = np.arange(len(piv.index))
        width = 0.25
        palette = ["#00e676", "#38bdf8", "#ef4444"]
        for i, col_name in enumerate(cols_order):
            vals = piv[col_name].values
            bars = ax2.bar(x + (i - 1) * width, vals, width=width, color=palette[i], label=col_name, edgecolor="#0f172a")
            for b in bars:
                h = b.get_height()
                ax2.text(b.get_x() + b.get_width() / 2.0, h + 1.2, f"{h:.0f}%", ha="center", va="bottom", color="#e2e8f0", fontsize=7.5)

        ax2.set_xticks(x)
        ax2.set_xticklabels([s.replace("_", "\n") for s in piv.index], color="#cbd5e1", fontsize=8.5)
        ax2.set_ylim(0, 112)
        ax2.set_ylabel("Cascading Infrastructure Operational Survival (%)", color="#cbd5e1", fontsize=9.5)
        ax2.set_title("True 3-DoF RK4 Post-Training Gauntlet (Same $B Budget)", color="white", fontsize=11, fontweight="bold")
        ax2.tick_params(colors="#94a3b8", labelsize=8.5)
        ax2.grid(axis="y", color="#1e293b", linestyle=":", linewidth=0.7)
        ax2.legend(loc="upper right", facecolor="#0f172a", edgecolor="#334155", labelcolor="white", fontsize=8.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


# ==============================================================================
# 3. 4-PART POST-TRAINING VERIFICATION GAUNTLET
# ==============================================================================

def run_post_training_gauntlet(seed: int = 101) -> Dict[str, Any]:
    """
    Executes all 4 post-training verification tests inside TRUE 3-DoF RK4 physics
    on held-out world regions never seen during training.
    """
    surrogate_net, deploy_net, killweb_net, device = tlm.load_trained_lattice_models()

    scenarios = [
        ("ZeroShot_Taiwan_ToT", "taiwan_silicon_shield", "combined_tot_saturation"),
        ("ZeroShot_Hormuz_ToT", "hormuz_energy_corridor", "combined_tot_saturation"),
        ("SEAD_SelfHealing_Test", "baltic_nordic_shield", "sead_and_jamming_surge"),
        ("DroneBait_CostTrap_Test", "pacific_nw_strategic_corridor", "drone_bait_cost_trap"),
    ]

    rows: List[Dict[str, Any]] = []
    featured_diag_data = None

    print("=" * 104)
    print("POST-TRAINING TRUE 3-DOF RK4 VERIFICATION GAUNTLET (UNSEEN GLOBAL REGIONS | STRICT FOG OF WAR)")
    print("=" * 104)

    for scen_label, reg_key, strike_style in scenarios:
        reg = lmesh.GLOBAL_TEST_REGIONS[reg_key]
        infra_base = copy.deepcopy(reg["infrastructure"])
        budget_musd = float(reg["default_budget_musd"])
        mesh = lmesh.generate_geodesic_spatial_mesh(infra_base, sea_azimuth_deg=reg["sea_azimuth_deg"])
        waves = build_multi_wave_tot_strike(infra_base, reg["sea_azimuth_deg"], preset_style=strike_style, attack_mult=1.0)

        print(f"\n>>> SCENARIO: {scen_label} | {reg['title']} | Budget: ${budget_musd:.0f}M")
        print("-" * 104)
        print(
            f"{'Architecture':<26} | {'OpSurv%':<8} | {'Kills':<9} | {'EoR Kills':<9} | "
            f"{'EW Kills':<8} | {'DebrisHit':<9} | {'ShotSpend':<10} | {'SEAD Lost'}"
        )
        print("-" * 104)

        # 1. Pure Learned Neural Lattice Kill-Web
        cop_n, pl_n, _ = lsim.deploy_neural_lattice_mesh(
            copy.deepcopy(infra_base), mesh, budget_musd, deploy_net, device
        )
        res_n = lsim.execute_true_rk4_raid_simulation(
            cop_n, mesh, waves, "neural_lattice", surrogate_net, killweb_net, device, seed=seed
        )

        # 2. Heuristic Ring Mesh Baseline (Same $B Budget)
        cop_h, _, _ = lsim.deploy_baseline_defense("heuristic_ring", copy.deepcopy(infra_base), mesh, budget_musd)
        res_h = lsim.execute_true_rk4_raid_simulation(cop_h, mesh, waves, "heuristic_ring", seed=seed)

        # 3. Legacy Siloed Co-Located Batteries (Same $B Budget, No Engage-on-Remote)
        cop_s, _, _ = lsim.deploy_baseline_defense("siloed_legacy", copy.deepcopy(infra_base), mesh, budget_musd)
        res_s = lsim.execute_true_rk4_raid_simulation(cop_s, mesh, waves, "siloed_greedy", seed=seed)

        for arch_name, r in [
            ("Neural Lattice Kill-Web", res_n),
            ("Heuristic Ring Mesh", res_h),
            ("Legacy Siloed Batteries", res_s),
        ]:
            print(
                f"{arch_name:<26} | "
                f"{r['cascading_operational_survival_pct']:6.1f}%  | "
                f"{r['threats_neutralized']:2d}/{r['total_threats_with_mirvs']:<2d}     | "
                f"{r['engage_on_remote_kills']:<9d} | "
                f"{r['ew_soft_kills']:<8d} | "
                f"{r['debris_collateral_events']:<9d} | "
                f"${r['interceptor_spend_musd']:7.2f}M  | "
                f"{r['sead_nodes_destroyed']}"
            )
            rows.append({
                "scenario": scen_label,
                "region": reg_key,
                "architecture": arch_name,
                "budget_musd": budget_musd,
                "cascading_operational_survival_pct": r["cascading_operational_survival_pct"],
                "structural_survival_pct": r["structural_survival_pct"],
                "intercept_rate_pct": r["intercept_rate_pct"],
                "threats_neutralized": r["threats_neutralized"],
                "total_threats": r["total_threats_with_mirvs"],
                "engage_on_remote_kills": r["engage_on_remote_kills"],
                "ew_soft_kills": r["ew_soft_kills"],
                "debris_collateral_events": r["debris_collateral_events"],
                "sead_nodes_destroyed": r["sead_nodes_destroyed"],
                "interceptor_spend_musd": r["interceptor_spend_musd"],
                "attacker_strike_cost_musd": r["attacker_strike_cost_musd"],
                "favorable_shot_exchange_ratio": r["favorable_shot_exchange_ratio"],
            })

        if featured_diag_data is None:
            featured_diag_data = (reg["title"], infra_base, mesh, pl_n, res_n)
            # Export Lattice SDK compliant Entity Snapshot & Tasks v2 log!
            with open(os.path.join(BASE_DIR, "lattice_cop_snapshot.json"), "w", encoding="utf-8") as f:
                json.dump(res_n["lattice_cop_snapshot"], f, indent=2)
            with open(os.path.join(BASE_DIR, "lattice_tasks_stream.json"), "w", encoding="utf-8") as f:
                json.dump(res_n["lattice_tasks_stream"], f, indent=2)

    df = pd.DataFrame(rows)
    csv_path = os.path.join(BASE_DIR, "lattice_gauntlet_summary.csv")
    json_path = os.path.join(BASE_DIR, "lattice_gauntlet_results.json")
    plot_path = os.path.join(BASE_DIR, "lattice_mesh_diagnostic.png")

    df.to_csv(csv_path, index=False)
    if featured_diag_data is not None:
        render_spatial_mesh_diagnostic_plot(*featured_diag_data, df, plot_path)

    agg = df.groupby("architecture")[
        ["cascading_operational_survival_pct", "intercept_rate_pct", "engage_on_remote_kills", "ew_soft_kills", "debris_collateral_events", "interceptor_spend_musd"]
    ].mean().round(2).to_dict(orient="index")

    payload = {"aggregate_by_architecture": agg, "scenario_runs": rows}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "=" * 104)
    print("MEAN PERFORMANCE ACROSS ALL 4 UNSEEN GLOBAL GAUNTLET TESTS:")
    for k, v in agg.items():
        print(
            f"  * {k:<25} -> Mean Survival: {v['cascading_operational_survival_pct']:5.1f}% | "
            f"Mean Kills: {v['intercept_rate_pct']:5.1f}% | Mean Shot Spend: ${v['interceptor_spend_musd']:5.2f}M | "
            f"Mean Debris Hits: {v['debris_collateral_events']:.2f}"
        )
    print("-" * 104)
    print(f"Exported Gauntlet Summary CSV   : {csv_path}")
    print(f"Exported Gauntlet Results JSON  : {json_path}")
    print(f"Exported Lattice COP Snapshot   : {os.path.join(BASE_DIR, 'lattice_cop_snapshot.json')}")
    print(f"Exported Lattice Tasks v2 Log   : {os.path.join(BASE_DIR, 'lattice_tasks_stream.json')}")
    print(f"Exported Spatial Mesh Plot PNG  : {plot_path}")
    print("=" * 104)
    return payload
