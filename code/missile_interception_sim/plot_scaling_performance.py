#!/usr/bin/env python3
"""
================================================================================
MODEL PERFORMANCE VS. SIMULATION VOLUME SCALING ANALYZER & PLOTTER
File: plot_scaling_performance.py
================================================================================
Generates a 3-panel empirical scaling figure (`lattice_performance_vs_runs.png`)
and CSV (`lattice_scaling_metrics.csv`) quantifying how model accuracy, threat
interception rate, and cascading infrastructure survival improve as simulation
volume scales from 0 (untrained) up to 2,000,000 3-DoF RK4 physics engagements
and 1,001,472 multi-wave global raid episodes (18.02M+ total trajectories).
================================================================================
"""

from __future__ import annotations

import json
import os
import time

os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

import train_lattice_m3_ultra as tlm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def measure_stage1_rk4_sample_scaling(device: torch.device) -> pd.DataFrame:
    """
    Empirically trains `LatticeKinematicSurrogateNet` across increasing 3-DoF RK4
    dataset sizes (2k -> 10k -> 50k -> 250k -> 1M -> 2M) and evaluates on a fixed
    100,000-trajectory held-out RK4 validation set.
    """
    threat_mat, shooter_mat = tlm._build_catalog_arrays_for_numba()
    # Warm-up JIT
    _ = tlm.generate_rk4_engagement_dataset_numba(64, threat_mat, shooter_mat, rk4_steps=40, seed=999)

    X_test_np, Y_test_np = tlm.generate_rk4_engagement_dataset_numba(
        100_000, threat_mat, shooter_mat, rk4_steps=40, seed=77777
    )
    X_test = torch.from_numpy(X_test_np).to(device)
    Y_test = torch.from_numpy(Y_test_np).to(device)

    X_pool_np, Y_pool_np = tlm.generate_rk4_engagement_dataset_numba(
        2_000_000, threat_mat, shooter_mat, rk4_steps=40, seed=2026
    )

    sample_sizes = [2_000, 10_000, 50_000, 250_000, 1_000_000, 2_000_000]
    rows = []

    for n_runs in sample_sizes:
        torch.manual_seed(42)
        net = tlm.LatticeKinematicSurrogateNet().to(device)
        opt = torch.optim.AdamW(net.parameters(), lr=2.5e-3, weight_decay=1e-4)

        X_sub = torch.from_numpy(X_pool_np[:n_runs])
        Y_sub = torch.from_numpy(Y_pool_np[:n_runs])

        bs = min(16384, max(256, n_runs // 8))
        epochs = 12 if n_runs >= 250_000 else 16

        net.train()
        for _ in range(epochs):
            perm = torch.randperm(n_runs)
            for s in range(0, n_runs, bs):
                idx = perm[s:s + bs]
                xb = X_sub[idx].to(device)
                yb = Y_sub[idx].to(device)
                pk_p, cpa_p, tint_p, deb_p = net(xb)
                loss = (
                    F.mse_loss(pk_p, yb[:, 0]) * 6.0
                    + F.smooth_l1_loss(torch.log1p(cpa_p), torch.log1p(yb[:, 1]))
                    + F.smooth_l1_loss(tint_p / 100.0, yb[:, 2] / 100.0)
                    + 0.5 * F.smooth_l1_loss(deb_p / 10.0, yb[:, 3] / 10.0)
                )
                opt.zero_grad()
                loss.backward()
                opt.step()

        net.eval()
        with torch.no_grad():
            v_pk, v_cpa, v_t, _ = net(X_test)
            pk_mae_pct = float(torch.abs(v_pk - Y_test[:, 0]).mean().item()) * 100.0
            pk_acc_pct = 100.0 - pk_mae_pct
            t_mae_s = float(torch.abs(v_t - Y_test[:, 2]).mean().item())

        rows.append({
            "rk4_simulations": n_runs,
            "rk4_integration_steps": n_runs * 40,
            "pk_mae_pct": round(pk_mae_pct, 3),
            "pk_precision_pct": round(pk_acc_pct, 3),
            "tint_mae_s": round(t_mae_s, 3),
        })
        print(f"  [Stage 1 Scaling] {n_runs:9,d} RK4 runs -> Pk Precision: {pk_acc_pct:.2f}% (MAE {pk_mae_pct:.2f}%) | T_int MAE: {t_mae_s:.2f}s")

    return pd.DataFrame(rows)


def measure_zero_run_untrained_baseline(device: torch.device) -> dict:
    """Evaluates completely untrained (0-run random init) Deployment + KillWeb nets."""
    torch.manual_seed(42)
    surr, _, _, _ = tlm.load_trained_lattice_models(device=device)
    untrained_dep = tlm.LatticeMeshDeploymentNet().to(device)
    untrained_kw = tlm.LatticeKillWebPolicyNet().to(device)
    untrained_dep.eval()
    untrained_kw.eval()
    cat_t = tlm._build_node_catalog_tensors(device)
    with torch.no_grad():
        _, _, _, _, m0 = tlm.run_batched_gpu_raid_episodes(
            batch_size=1024,
            deploy_net=untrained_dep,
            killweb_net=untrained_kw,
            surrogate_net=surr,
            cat_t=cat_t,
            device=device,
            adversarial_difficulty=0.25,
            deterministic=False,
        )
    return m0


def generate_scaling_plots() -> str:
    device = tlm.get_compute_device(prefer_mps=True)
    print("Measuring Stage 1 RK4 Physics Surrogate scaling & 0-run baseline on M3 Ultra...")
    df_s1 = measure_stage1_rk4_sample_scaling(device)
    m_zero = measure_zero_run_untrained_baseline(device)

    telem_path = os.path.join(BASE_DIR, "lattice_models", "training_telemetry.json")
    with open(telem_path, "r", encoding="utf-8") as f:
        telem = json.load(f)

    curve = telem["stage2_adversarial_self_play"]["training_curve"]
    s2_rows = [{
        "episodes_completed": 0,
        "simulated_threats": 0,
        "total_trajectories_incl_stage1": 0,
        "adversarial_difficulty": 0.25,
        "operational_survival_pct": round(m_zero["operational_survival_pct"], 2),
        "intercept_rate_pct": round(m_zero["intercept_rate_pct"], 2),
        "mean_reward": round(m_zero["mean_reward"], 3),
    }]
    for pt in curve:
        ep = int(pt["episodes_completed"])
        s2_rows.append({
            "episodes_completed": ep,
            "simulated_threats": ep * 16,
            "total_trajectories_incl_stage1": 2_000_000 + ep * 16,
            "adversarial_difficulty": pt["adversarial_difficulty"],
            "operational_survival_pct": pt["operational_survival_pct"],
            "intercept_rate_pct": pt["intercept_rate_pct"],
            "mean_reward": pt["mean_reward"],
        })
    df_s2 = pd.DataFrame(s2_rows)

    csv_out = os.path.join(BASE_DIR, "lattice_scaling_metrics.csv")
    df_s2.to_csv(csv_out, index=False)

    # Render 3-Panel High-Resolution Scaling Graph
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(19.5, 6.2), facecolor="#060b14")

    # --- Panel 1: Stage 1 RK4 Physics Surrogate Precision vs. Simulation Runs ---
    ax1.set_facecolor("#0b1322")
    l1 = ax1.plot(
        df_s1["rk4_simulations"], df_s1["pk_precision_pct"],
        "-o", color="#00f0ff", linewidth=2.6, markersize=7, label="Pk Prediction Precision (%)",
    )
    ax1.set_xscale("log")
    ax1.set_xlabel("Stage 1: 3-DoF RK4 Physics Runs (Log Scale)", color="#cbd5e1", fontsize=10)
    ax1.set_ylabel("Surrogate Pk Precision (100 - MAE %)", color="#00f0ff", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#00f0ff")
    ax1.tick_params(axis="x", colors="#94a3b8")
    ax1.set_ylim(88.0, 99.2)
    ax1.grid(color="#1e293b", linestyle=":", linewidth=0.8)

    ax1_r = ax1.twinx()
    l2 = ax1_r.plot(
        df_s1["rk4_simulations"], df_s1["tint_mae_s"],
        "--s", color="#f59e0b", linewidth=2.2, markersize=6.5, label="Intercept Time MAE (sec)",
    )
    ax1_r.set_ylabel("Time-to-Intercept Error MAE (seconds)", color="#f59e0b", fontsize=10)
    ax1_r.tick_params(axis="y", labelcolor="#f59e0b")

    lines_1 = l1 + l2
    labels_1 = [ln.get_label() for ln in lines_1]
    ax1.legend(lines_1, labels_1, loc="center right", facecolor="#0f172a", edgecolor="#334155", labelcolor="white", fontsize=8.5)
    ax1.set_title("1. Physics Surrogate Scaling\n(2,000 -> 2,000,000 RK4 Trajectories)", color="white", fontsize=11, fontweight="bold")

    # --- Panel 2: Stage 2 Kill-Web Intercept & Survival vs. Global Raid Episodes ---
    ax2.set_facecolor("#0b1322")
    x_k = df_s2["episodes_completed"] / 1000.0
    ax2.plot(x_k, df_s2["intercept_rate_pct"], "-o", color="#00e676", linewidth=2.6, markersize=6, label="Threat Intercept Rate (%)")
    ax2.plot(x_k, df_s2["operational_survival_pct"], "-^", color="#38bdf8", linewidth=2.5, markersize=6, label="Cascading Infra Survival (%)")
    ax2.fill_between(x_k, df_s2["operational_survival_pct"], alpha=0.14, color="#38bdf8")

    # Annotate 0-run vs Warm-Start vs 1M-Episode gains
    ax2.annotate(
        f"Untrained (0 runs)\nSurv: {df_s2['operational_survival_pct'].iloc[0]:.1f}% | Kills: {df_s2['intercept_rate_pct'].iloc[0]:.1f}%",
        xy=(0, df_s2["operational_survival_pct"].iloc[0]),
        xytext=(110, 16),
        arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=1.1),
        color="#e2e8f0", fontsize=8.2,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f172a", edgecolor="#334155"),
    )
    ax2.annotate(
        f"1.0M Raids (16M Threats)\nSurv: {df_s2['operational_survival_pct'].iloc[-1]:.1f}% | Kills: {df_s2['intercept_rate_pct'].iloc[-1]:.1f}%",
        xy=(x_k.iloc[-1], df_s2["intercept_rate_pct"].iloc[-1]),
        xytext=(510, 81),
        arrowprops=dict(arrowstyle="->", color="#00e676", lw=1.2),
        color="#bbf7d0", fontsize=8.2,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#064e3b", edgecolor="#10b981"),
    )

    ax2.set_xlabel("Stage 2: Global Multi-Wave Raid Episodes (Thousands)", color="#cbd5e1", fontsize=10)
    ax2.set_ylabel("Model Effectiveness (%)", color="#cbd5e1", fontsize=10)
    ax2.set_ylim(5, 92)
    ax2.tick_params(colors="#94a3b8")
    ax2.grid(color="#1e293b", linestyle=":", linewidth=0.8)
    ax2.legend(loc="lower right", facecolor="#0f172a", edgecolor="#334155", labelcolor="white", fontsize=8.5)
    ax2.set_title("2. Neural Kill-Web vs. Raid Episodes\n(0 -> 1,001,472 Multi-Wave Raids on MPS)", color="white", fontsize=11, fontweight="bold")

    # --- Panel 3: Composite Tactical Reward & Adversarial Curriculum vs. Total Simulated Threats ---
    ax3.set_facecolor("#0b1322")
    x_millions = df_s2["total_trajectories_incl_stage1"] / 1_000_000.0
    l3 = ax3.plot(x_millions, df_s2["mean_reward"], "-D", color="#c084fc", linewidth=2.6, markersize=5.8, label="Composite C2 Reward")
    ax3.set_xlabel("Total Cumulative Simulated Trajectories (Millions)", color="#cbd5e1", fontsize=10)
    ax3.set_ylabel("Composite Lattice C2 Reward", color="#c084fc", fontsize=10)
    ax3.tick_params(axis="y", labelcolor="#c084fc")
    ax3.tick_params(axis="x", colors="#94a3b8")
    ax3.grid(color="#1e293b", linestyle=":", linewidth=0.8)

    ax3_r = ax3.twinx()
    l4 = ax3_r.plot(
        x_millions, df_s2["adversarial_difficulty"] * 100.0,
        ":", color="#fb7185", linewidth=2.2, label="Red EW/SEAD Curriculum Difficulty (%)",
    )
    ax3_r.set_ylabel("Adversarial EW & SEAD Difficulty (%)", color="#fb7185", fontsize=10)
    ax3_r.tick_params(axis="y", labelcolor="#fb7185")
    ax3_r.set_ylim(0, 115)

    lines_3 = l3 + l4
    labels_3 = [ln.get_label() for ln in lines_3]
    ax3.legend(lines_3, labels_3, loc="lower right", facecolor="#0f172a", edgecolor="#334155", labelcolor="white", fontsize=8.5)
    ax3.set_title("3. Reward Scaling Under Rising Difficulty\n(Up to 18.02M Total Simulated Trajectories)", color="white", fontsize=11, fontweight="bold")

    plt.suptitle(
        "Anduril Lattice Autonomous Kill-Web — Empirical Performance vs. Simulation Volume (Apple M3 Ultra: 32 CPU Cores + Metal MPS)",
        color="#f8fafc", fontsize=13, fontweight="bold", y=0.99,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    png_out = os.path.join(BASE_DIR, "lattice_performance_vs_runs.png")
    plt.savefig(png_out, dpi=240, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved Scaling Plot -> {png_out}")
    return png_out


if __name__ == "__main__":
    generate_scaling_plots()
