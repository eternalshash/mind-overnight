#!/usr/bin/env python3
"""
================================================================================
ACADEMIC ANALYSIS & TELEMETRY REPORTING SUITE
File: academic_analysis.py
================================================================================
Provides scientific-grade metrics, parametric sweeps, and publication-ready
visualizations for missile guidance and IAMD simulation research:
  1. Statistical Metrics:
     - Circular Error Probable (CEP50, CEP95)
     - Probability of Kill (P_k) confidence intervals
     - Miss distance distribution (mean, median, standard deviation)
     - Control effort / integrated G-load (energy expenditure metric)

  2. Parametric Sweeps:
     - Navigation ratio N sensitivity (N in [2.5, 5.5])
     - Target evasive G-load sensitivity (0G to 25G weave)
     - Electronic warfare / countermeasure degradation impact

  3. Publication-Grade Plots (Matplotlib):
     - Altitude vs Downrange trajectory profile
     - Commanded vs Achieved G-load & Autopilot lag
     - Seeker Line-of-Sight (LOS) rate convergence (Omega -> 0)
     - CEP Miss distance histogram & Cumulative Distribution Function (CDF)

  4. Data Export:
     - CSV / JSON export of full continuous trajectory states
================================================================================
"""

from __future__ import annotations
import math
import os
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg") # Non-interactive headless backend for automated script & server execution
import matplotlib.pyplot as plt

from gnc_engine import (
    G0, GuidanceLaw, WeaponSpec, GNCVehicle, GNCTelemetryFrame,
    CountermeasureState, compute_continuous_substep_cpa
)
from simbuilder import (
    SimBuilderCatalog, IADSSimulator, EngagementOutcome, RadarSensorNode
)


# ==============================================================================
# 1. ACADEMIC METRICS CALCULATION
# ==============================================================================

def compute_cep_metrics(miss_distances: List[float]) -> Dict[str, float]:
    """
    Computes standard aerospace Circular Error Probable (CEP) statistics:
      - CEP50: 50th percentile (median) miss distance
      - CEP95: 95th percentile miss distance
      - Mean, Std Dev, Min, Max
    """
    if not miss_distances:
        return {"cep50": 0.0, "cep95": 0.0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

    arr = np.array(miss_distances, dtype=float)
    return {
        "cep50": float(np.percentile(arr, 50)),
        "cep95": float(np.percentile(arr, 95)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def compute_pk_confidence_interval(
    kills: int,
    total: int,
    confidence: float = 0.95
) -> Tuple[float, float, float]:
    """
    Calculates Wilson score interval for Single-Shot Kill Probability (Pk).
    Returns: (pk_estimate, lower_bound, upper_bound)
    """
    if total <= 0:
        return 0.0, 0.0, 0.0

    p_hat = kills / total
    z = 1.96 if abs(confidence - 0.95) < 0.01 else 2.576 # 95% or 99%
    denom = 1.0 + (z ** 2) / total
    center = (p_hat + (z ** 2) / (2.0 * total)) / denom
    margin = (z * math.sqrt((p_hat * (1.0 - p_hat) / total) + ((z ** 2) / (4.0 * (total ** 2))))) / denom

    return p_hat, max(0.0, center - margin), min(1.0, center + margin)


# ==============================================================================
# 2. PARAMETRIC SWEEP EXPERIMENT RUNNER
# ==============================================================================

def run_navigation_ratio_sweep(
    interceptor_spec: WeaponSpec,
    threat_spec: WeaponSpec,
    n_values: List[float] = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5],
    dt: float = 0.02,
) -> pd.DataFrame:
    """
    Sweeps navigation ratio N and evaluates miss distance, intercept time,
    and peak G-load to identify the optimal guidance gain.
    """
    results = []

    for n in n_values:
        # Create a spec clone with this navigation ratio
        spec_copy = WeaponSpec(
            weapon_id=f"{interceptor_spec.weapon_id}_n{n}",
            name=f"{interceptor_spec.name} (N={n})",
            role=interceptor_spec.role,
            guidance_law=interceptor_spec.guidance_law,
            nav_ratio_n=n,
            aero=interceptor_spec.aero,
            propulsion=interceptor_spec.propulsion,
            seeker=interceptor_spec.seeker,
            autopilot=interceptor_spec.autopilot,
            kill_radius_htk_m=interceptor_spec.kill_radius_htk_m,
            kill_radius_blast_m=interceptor_spec.kill_radius_blast_m,
        )

        # Baseline head-on engagement: Threat at 50 km downrange
        threat_pos = np.array([50000.0, 5000.0, 18000.0])
        threat_vel = np.array([-1800.0, 0.0, -150.0]) # Mach 6 inbound
        int_pos = np.array([0.0, 0.0, 10.0])
        int_vel = np.array([600.0, 60.0, 350.0])

        target = GNCVehicle(threat_spec, threat_pos, threat_vel)
        interceptor = GNCVehicle(spec_copy, int_pos, int_vel)

        sim = IADSSimulator()
        sim.add_battery("BAT_SWEEP", spec_copy, int_pos)
        sim.active_interceptors.append((interceptor, target, "BAT_SWEEP"))

        # Step until termination
        t = 0.0
        outcomes = []
        while t < 60.0 and interceptor.active and target.active:
            # Weave target at 8G
            target.accel_achieved = np.array([0.0, 8.0 * G0 * math.sin(0.4 * t), 0.0])
            target.pos += target.vel * dt
            step_outcomes = sim.step_engagement(dt)
            if step_outcomes:
                outcomes.extend(step_outcomes)
                break
            t += dt

        if outcomes:
            res = outcomes[0]
            results.append({
                "nav_ratio_n": n,
                "kill": res.kill,
                "hit_type": res.hit_type,
                "miss_distance_m": res.cpa_miss_distance_m,
                "intercept_time_s": res.intercept_time_s,
                "closing_velocity_ms": res.closing_velocity_ms,
                "max_g": res.max_g_intercept,
            })

    return pd.DataFrame(results)


# ==============================================================================
# 3. PUBLICATION-QUALITY PLOTTING SUITE (MATPLOTLIB)
# ==============================================================================

def plot_engagement_telemetry(
    interceptor: GNCVehicle,
    target: GNCVehicle,
    output_path: str = "engagement_telemetry.png",
    title_suffix: str = ""
):
    """
    Renders a 4-panel aerospace research plot:
      Panel 1: 2D Altitude vs Downrange Profile (Trajectory flyout)
      Panel 2: Commanded vs Achieved G-load (Autopilot lag verification)
      Panel 3: Seeker Line-of-Sight Rate convergence (Proportional Navigation law)
      Panel 4: Mach & Closing Velocity vs Flight Time
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), facecolor="#0e1420")
    for ax in axes.flat:
        ax.set_facecolor("#161f30")
        ax.grid(True, linestyle="--", alpha=0.3, color="#8ba3c7")
        ax.tick_params(colors="#c0d2eb")
        for spine in ax.spines.values():
            spine.set_color("#3a4f73")

    i_hist = interceptor.telemetry_history
    t_hist = target.telemetry_history

    i_times = [f.time for f in i_hist]
    i_downrange_km = [math.hypot(f.pos[0], f.pos[1]) / 1000.0 for f in i_hist]
    i_alt_km = [f.pos[2] / 1000.0 for f in i_hist]
    i_g_cmd = [float(np.linalg.norm(f.accel_commanded)) / G0 for f in i_hist]
    i_g_act = [f.g_load for f in i_hist]
    i_los_rate = [math.degrees(f.los_rate_rad_s) for f in i_hist]
    i_mach = [f.mach for f in i_hist]
    i_vc = [f.closing_velocity_ms for f in i_hist]

    # Panel 1: Altitude vs Downrange
    ax1 = axes[0, 0]
    ax1.plot(i_downrange_km, i_alt_km, color="#00ffff", linewidth=2.5, label=f"Interceptor ({interceptor.spec.name})")
    if t_hist:
        t_downrange_km = [math.hypot(f.pos[0], f.pos[1]) / 1000.0 for f in t_hist]
        t_alt_km = [f.pos[2] / 1000.0 for f in t_hist]
        ax1.plot(t_downrange_km, t_alt_km, color="#ff4466", linewidth=2.0, linestyle="--", label="Target Track")
    ax1.set_title("Altitude vs Downrange Profile", color="#ffffff", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Downrange Range (km)", color="#c0d2eb")
    ax1.set_ylabel("Altitude MSL (km)", color="#c0d2eb")
    ax1.legend(facecolor="#161f30", edgecolor="#3a4f73", labelcolor="#ffffff")

    # Panel 2: Commanded vs Achieved G-load
    ax2 = axes[0, 1]
    ax2.plot(i_times, i_g_cmd, color="#ffaa00", linewidth=1.5, linestyle=":", label="Commanded G (Guidance)")
    ax2.plot(i_times, i_g_act, color="#00ff88", linewidth=2.0, label="Achieved G (Autopilot)")
    ax2.axhline(interceptor.spec.autopilot.max_g_load, color="#ff3333", linestyle="--", alpha=0.7, label="Structural G-Limit")
    ax2.set_title("Maneuver G-Load & Autopilot Dynamics", color="#ffffff", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Flight Time (s)", color="#c0d2eb")
    ax2.set_ylabel("Acceleration (g's)", color="#c0d2eb")
    ax2.legend(facecolor="#161f30", edgecolor="#3a4f73", labelcolor="#ffffff")

    # Panel 3: Seeker LOS Rate (Proportional Navigation drives Omega -> 0)
    ax3 = axes[1, 0]
    ax3.plot(i_times, i_los_rate, color="#cc66ff", linewidth=2.0, label="LOS Rate ||Ω|| (deg/s)")
    ax3.axhline(0.0, color="#ffffff", linestyle="--", alpha=0.3)
    ax3.set_title("Seeker Line-of-Sight Rate Convergence (TPN)", color="#ffffff", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Flight Time (s)", color="#c0d2eb")
    ax3.set_ylabel("LOS Rate (deg/s)", color="#c0d2eb")
    ax3.legend(facecolor="#161f30", edgecolor="#3a4f73", labelcolor="#ffffff")

    # Panel 4: Mach & Closing Velocity
    ax4 = axes[1, 1]
    ax4.plot(i_times, i_mach, color="#3399ff", linewidth=2.0, label="Interceptor Mach")
    ax4_twin = ax4.twinx()
    ax4_twin.plot(i_times, i_vc, color="#ff9933", linewidth=1.8, linestyle="--", label="Closing Velocity V_c (m/s)")
    ax4_twin.tick_params(colors="#ffaa55")
    ax4_twin.set_ylabel("Closing Velocity (m/s)", color="#ffaa55")
    ax4.set_title("Kinematics: Velocity & Mach Number", color="#ffffff", fontsize=12, fontweight="bold")
    ax4.set_xlabel("Flight Time (s)", color="#c0d2eb")
    ax4.set_ylabel("Mach Number", color="#c0d2eb")
    ax4.legend(loc="upper left", facecolor="#161f30", edgecolor="#3a4f73", labelcolor="#ffffff")

    plt.suptitle(f"3-DoF GNC Engagement Telemetry {title_suffix}", color="#ffffff", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_cep_histogram(
    miss_distances: List[float],
    kill_radius_m: float = 15.0,
    output_path: str = "cep_distribution.png",
    title: str = "Monte Carlo Miss Distance Distribution (CEP)"
):
    """
    Renders publication-ready CEP histogram and empirical Cumulative Distribution Function (CDF).
    """
    fig, (ax_hist, ax_cdf) = plt.subplots(1, 2, figsize=(14, 5.5), facecolor="#0e1420")
    for ax in (ax_hist, ax_cdf):
        ax.set_facecolor("#161f30")
        ax.grid(True, linestyle="--", alpha=0.3, color="#8ba3c7")
        ax.tick_params(colors="#c0d2eb")
        for spine in ax.spines.values():
            spine.set_color("#3a4f73")

    arr = np.array(miss_distances, dtype=float)
    cep50 = float(np.percentile(arr, 50))
    cep95 = float(np.percentile(arr, 95))

    # Histogram
    n, bins, patches = ax_hist.hist(arr, bins=25, color="#00bbff", edgecolor="#ffffff", alpha=0.75, density=False)
    ax_hist.axvline(cep50, color="#00ff88", linestyle="-", linewidth=2.5, label=f"CEP50 = {cep50:.2f} m")
    ax_hist.axvline(cep95, color="#ffaa00", linestyle="--", linewidth=2.0, label=f"CEP95 = {cep95:.2f} m")
    ax_hist.axvline(kill_radius_m, color="#ff3333", linestyle=":", linewidth=2.5, label=f"Lethal Radius = {kill_radius_m:.1f} m")
    ax_hist.set_title("Miss Distance Histogram", color="#ffffff", fontsize=12, fontweight="bold")
    ax_hist.set_xlabel("Closest Point of Approach (m)", color="#c0d2eb")
    ax_hist.set_ylabel("Trial Frequency", color="#c0d2eb")
    ax_hist.legend(facecolor="#161f30", edgecolor="#3a4f73", labelcolor="#ffffff")

    # CDF
    sorted_dist = np.sort(arr)
    cdf = np.arange(1, len(sorted_dist) + 1) / len(sorted_dist)
    ax_cdf.plot(sorted_dist, cdf * 100.0, color="#00ffcc", linewidth=2.5, label="Empirical CDF")
    ax_cdf.axhline(50.0, color="#00ff88", linestyle="--", alpha=0.6, label="50% Probability (CEP50)")
    ax_cdf.axhline(95.0, color="#ffaa00", linestyle="--", alpha=0.6, label="95% Probability (CEP95)")
    ax_cdf.axvline(kill_radius_m, color="#ff3333", linestyle=":", linewidth=2.0)
    ax_cdf.set_title("Cumulative Intercept Probability (CDF)", color="#ffffff", fontsize=12, fontweight="bold")
    ax_cdf.set_xlabel("Miss Distance (m)", color="#c0d2eb")
    ax_cdf.set_ylabel("Cumulative Probability (%)", color="#c0d2eb")
    ax_cdf.legend(facecolor="#161f30", edgecolor="#3a4f73", labelcolor="#ffffff")

    plt.suptitle(title, color="#ffffff", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


# ==============================================================================
# 4. TELEMETRY EXPORTER TO CSV
# ==============================================================================

def export_telemetry_to_csv(
    vehicle: GNCVehicle,
    filepath: str
) -> pd.DataFrame:
    """Exports full continuous time-series state records of a vehicle to CSV."""
    records = []
    for f in vehicle.telemetry_history:
        records.append({
            "time_s": f.time,
            "x_m": f.pos[0],
            "y_m": f.pos[1],
            "z_alt_m": f.pos[2],
            "vx_ms": f.vel[0],
            "vy_ms": f.vel[1],
            "vz_ms": f.vel[2],
            "mach": f.mach,
            "dynamic_pressure_pa": f.dynamic_pressure_pa,
            "g_load": f.g_load,
            "mass_kg": f.mass_kg,
            "thrust_n": f.thrust_n,
            "drag_n": f.drag_n,
            "trim_alpha_deg": f.angle_of_attack_deg,
            "los_rate_rad_s": f.los_rate_rad_s,
            "closing_velocity_ms": f.closing_velocity_ms,
            "distance_to_target_m": f.distance_to_target_m,
            "look_angle_deg": f.look_angle_deg,
            "accel_cmd_x": f.accel_commanded[0],
            "accel_cmd_y": f.accel_commanded[1],
            "accel_cmd_z": f.accel_commanded[2],
            "accel_act_x": f.accel_achieved[0],
            "accel_act_y": f.accel_achieved[1],
            "accel_act_z": f.accel_achieved[2],
        })
    df = pd.DataFrame(records)
    df.to_csv(filepath, index=False)
    return df
