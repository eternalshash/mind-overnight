#!/usr/bin/env python3
"""
================================================================================
M3 ULTRA LATTICE TRAINING PIPELINE: 32-CORE RK4 PHYSICS + METAL MPS SELF-PLAY
File: train_lattice_m3_ultra.py
================================================================================
Pushes Apple M3 Ultra hardware across two coupled training stages:

STAGE 1 (32 CPU Cores @ 100% via Numba `@njit(parallel=True)`):
  - Executes 2,000,000+ (configurable via `--physics-runs`) 3-DoF RK4 atmospheric
    & exo-atmospheric engagements with Mach wave drag, APN/ZEM guidance, first-order
    autopilot lag, Kalman sensor covariance error, EW self-screening jamming,
    continuous quadratic sub-step CPA, and kinetic debris throw physics.
  - Trains `LatticeKinematicSurrogateNet` on Apple Metal (`mps`).

STAGE 2 (Apple Metal `MPS` GPU @ 100% Batched Tensor Environment):
  - Simulates 1,000,000+ (configurable via `--raid-episodes`) full multi-wave
    Global Theater Raid episodes under Strict Fog of War across randomized
    global infrastructure graphs, 3D ridge-shadowed geodesic meshes, Time-on-Target
    drone-bait + stealth cruise + HGV + MIRV salvos, and SEAD radar attacks.
  - Trains two coordinate-invariant neural architectures (warm-start + RL policy
    gradient self-play with advantage baseline):
      1. `LatticeMeshDeploymentNet` (Infrastructure-to-Mesh Cross-Attention)
      2. `LatticeKillWebPolicyNet` (Edge-Biased Relational Cross-Attention C2)
  - Saves resumable checkpoints to `lattice_models/`.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure zero OpenMP dual-runtime collision between Numba (32-core pthreads) and PyTorch MPS on macOS ARM64
os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
from numba import njit, prange
import torch
import torch.nn as nn
import torch.nn.functional as F

import lattice_mesh as lmesh


MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lattice_models")


def get_compute_device(prefer_mps: bool = True) -> torch.device:
    if prefer_mps and torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# ==============================================================================
# 1. STAGE 1: 32-CORE NUMBA 3-DOF RK4 + GNC/EW/DEBRIS PHYSICS GENERATOR (2M+ RUNS)
# ==============================================================================

def _build_catalog_arrays_for_numba() -> Tuple[np.ndarray, np.ndarray]:
    """Packs threat arsenal and kinetic shooter catalog into contiguous float64 matrices."""
    threats = []
    for wid in lmesh.THREAT_IDS_ORDERED:
        t = lmesh.THREAT_ARSENAL[wid]
        threats.append([
            float(t.archetype_id),
            float(t.max_speed_mps),
            float(t.cruise_or_apogee_m),
            float(t.rcs_m2),
            float(t.maneuver_g),
            float(t.ew_jammer_SelfProtect),
            float(t.warhead_mass_kg),
        ])
    shooters = []
    for s in lmesh.LATTICE_NODE_CATALOG:
        if s.role == "shooter":
            shooters.append([
                float(s.tier),
                float(s.weapon_range_km),
                float(s.min_alt_m),
                float(s.max_alt_m),
                float(s.interceptor_speed_mps),
                float(s.max_g_load),
                float(s.kill_radius_m),
            ])
    return np.array(threats, dtype=np.float64), np.array(shooters, dtype=np.float64)


@njit(parallel=True, fastmath=True)
def generate_rk4_engagement_dataset_numba(
    n_runs: int,
    threat_mat: np.ndarray,
    shooter_mat: np.ndarray,
    rk4_steps: int = 40,
    seed: int = 2026,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Shards `n_runs` individual 3-DoF RK4 + APN/ZEM + EW/Covariance engagements
    uniformly across ALL 32 CPU hardware threads (`prange(n_runs)`).

    Returns:
      X: [n_runs, 14] normalized engagement state features
      Y: [n_runs, 4]  ground-truth [kill_prob, cpa_miss_m, t_int_s, debris_throw_km]
    """
    X = np.zeros((n_runs, 14), dtype=np.float32)
    Y = np.zeros((n_runs, 4), dtype=np.float32)

    n_threats = threat_mat.shape[0]
    n_shooters = shooter_mat.shape[0]

    for i in prange(n_runs):
        # Per-sample SplitMix64 PRNG (zero thread contention across 32 cores!)
        st = np.uint64(seed) + np.uint64(i + 1) * np.uint64(0x9E3779B97F4A7C15)
        st = (st ^ (st >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        st = (st ^ (st >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        u1 = float((st >> np.uint64(11)) & np.uint64(0x1FFFFF)) / float(0x200000)

        st = (st + np.uint64(0x9E3779B97F4A7C15)) * np.uint64(0xBF58476D1CE4E5B9)
        u2 = float((st >> np.uint64(11)) & np.uint64(0x1FFFFF)) / float(0x200000)

        st = (st + np.uint64(0x9E3779B97F4A7C15)) * np.uint64(0xBF58476D1CE4E5B9)
        u3 = float((st >> np.uint64(11)) & np.uint64(0x1FFFFF)) / float(0x200000)

        st = (st + np.uint64(0x9E3779B97F4A7C15)) * np.uint64(0xBF58476D1CE4E5B9)
        u4 = float((st >> np.uint64(11)) & np.uint64(0x1FFFFF)) / float(0x200000)

        st = (st + np.uint64(0x9E3779B97F4A7C15)) * np.uint64(0xBF58476D1CE4E5B9)
        u5 = float((st >> np.uint64(11)) & np.uint64(0x1FFFFF)) / float(0x200000)

        t_idx = int(i % n_threats)
        s_idx = int((i // n_threats) % n_shooters)

        arch = threat_mat[t_idx, 0]
        vt_max = threat_mat[t_idx, 1] * (0.82 + 0.22 * u1)
        alt_ref = threat_mat[t_idx, 2]
        man_g = threat_mat[t_idx, 4] * (0.6 + 0.6 * u2)
        ew_jam = min(1.0, threat_mat[t_idx, 5] * (0.5 + 0.9 * u3))

        s_range_km = shooter_mat[s_idx, 1]
        s_min_alt = shooter_mat[s_idx, 2]
        s_max_alt = shooter_mat[s_idx, 3]
        vm_nom = shooter_mat[s_idx, 4]
        s_max_g = shooter_mat[s_idx, 5]
        kill_rad = shooter_mat[s_idx, 6]

        # Sample realistic engagement geometry (both inside and outside envelope so net learns boundaries!)
        ground_range_km = s_range_km * (0.08 + 1.32 * u4)
        if arch <= 1.0:
            alt_m = max(12.0, alt_ref * (0.4 + 1.8 * u2))
        elif arch == 2.0:
            alt_m = 25.0 + 14000.0 * (u2 * u2)
        elif arch == 3.0:
            alt_m = 4000.0 + alt_ref * math.sin(math.pi * (0.15 + 0.75 * u2))
        elif arch == 4.0:
            alt_m = 22000.0 + 58000.0 * u2
        else:
            alt_m = 55000.0 + alt_ref * (0.12 + 0.85 * u2)

        slant_km = math.sqrt(ground_range_km * ground_range_km + (alt_m * 1e-3) ** 2)
        closing_cos = -0.35 + 1.35 * u5  # [-0.35 receding -> +1.0 head-on]
        is_eor = 1.0 if (u3 > 0.52) else 0.0
        track_sigma_m = (14.0 + 55.0 * u1) if is_eor < 0.5 else (18.0 + 95.0 * (u1 * u1))

        # Altitude & range envelope margin [-1.0 -> +1.0]
        if alt_m < s_min_alt:
            alt_env = -min(1.0, (s_min_alt - alt_m) / max(50.0, s_min_alt))
        elif alt_m > s_max_alt:
            alt_env = -min(1.0, (alt_m - s_max_alt) / max(1000.0, s_max_alt * 0.35))
        else:
            alt_env = 1.0

        # Interceptor flyout time with boost + atmospheric Mach drag loss
        rho_ratio = math.exp(-alt_m / 7500.0)
        drag_factor = 1.0 - 0.16 * rho_ratio * min(1.5, ground_range_km / max(5.0, s_range_km))
        vm_eff = max(180.0, vm_nom * drag_factor)
        commit_delay_s = 1.8 + 1.4 * is_eor
        eff_closing_mps = max(150.0, vm_eff + vt_max * 0.55 * closing_cos)
        t_int_s = commit_delay_s + (slant_km * 1000.0) / eff_closing_mps

        # 3-DoF RK4 Terminal Homing Simulation (final 10.0 seconds to CPA)
        t_term = 10.0
        dt = t_term / float(rk4_steps)
        vx_close = max(220.0, vm_eff + vt_max * max(-0.2, closing_cos))
        rx = -vx_close * t_term

        # Initial lateral/vertical handoff error driven by Kalman track covariance + EW glint
        handoff_err = track_sigma_m * (1.0 + 0.85 * ew_jam)
        ry = (u1 - 0.5) * 2.4 * handoff_err
        rz = (u2 - 0.5) * 2.2 * handoff_err
        vy = -ry / t_term + (u4 - 0.5) * 35.0
        vz = -rz / t_term + (u5 - 0.5) * 30.0

        # First-order autopilot lag state (achieved missile acceleration)
        am_y = 0.0
        am_z = 0.0
        tau_ap = 0.11 + 0.06 * ew_jam

        # Aerodynamic authority scales down in thin upper mesosphere unless Tier 1/2 DACS equipped
        if shooter_mat[s_idx, 0] <= 2.5:
            g_avail = s_max_g * 9.80665  # Exo/Upper DACS thrusters retain full divert G!
        else:
            aero_scale = max(0.18, min(1.0, math.exp(-max(0.0, alt_m - 22000.0) / 14000.0)))
            g_avail = s_max_g * 9.80665 * aero_scale

        min_dist_sq = rx * rx + ry * ry + rz * rz
        nav_N = 4.2

        for step in range(rk4_steps):
            if rx >= 0.0:
                break
            t_cur = float(step) * dt
            # Target 3D evasive weave / barrel-roll / skip-glide acceleration
            omega = 2.6 + 1.2 * u3
            at_y = man_g * 9.80665 * math.sin(omega * t_cur + u1 * 6.283)
            at_z = man_g * 9.80665 * 0.75 * math.cos(0.85 * omega * t_cur + u2 * 6.283)

            # Seeker angular glint / EW jamming noise near terminal burn-through
            burn_through_factor = min(1.0, (-rx) / 4500.0)
            glint_y = ew_jam * 18.0 * burn_through_factor * math.sin(9.5 * t_cur)
            glint_z = ew_jam * 15.0 * burn_through_factor * math.cos(8.3 * t_cur)

            # Augmented ZEM Optimal Guidance command
            t_go = max(2.2 * dt, -rx / vx_close)
            zem_y = (ry + glint_y) + vy * t_go - 0.5 * at_y * t_go * t_go * 0.35
            zem_z = (rz + glint_z) + vz * t_go - 0.5 * at_z * t_go * t_go * 0.35
            cmd_y = -nav_N * zem_y / (t_go * t_go)
            cmd_z = -nav_N * zem_z / (t_go * t_go)

            cmd_mag = math.sqrt(cmd_y * cmd_y + cmd_z * cmd_z)
            if cmd_mag > g_avail:
                sc = g_avail / cmd_mag
                cmd_y *= sc
                cmd_z *= sc

            # RK2/RK4 midpoint integration of autopilot lag + relative kinematics
            dam_y1 = (cmd_y - am_y) / tau_ap
            dam_z1 = (cmd_z - am_z) / tau_ap
            am_y_mid = am_y + 0.5 * dt * dam_y1
            am_z_mid = am_z + 0.5 * dt * dam_z1

            rel_ay = am_y_mid - at_y
            rel_az = am_z_mid - at_z

            drx = vx_close * dt
            dry = vy * dt + 0.5 * rel_ay * dt * dt
            drz = vz * dt + 0.5 * rel_az * dt * dt

            # Continuous quadratic sub-timestep CPA interpolation
            dr_sq = drx * drx + dry * dry + drz * drz
            if dr_sq > 1e-8:
                tau_cpa = -(rx * drx + ry * dry + rz * drz) / dr_sq
                if tau_cpa < 0.0:
                    tau_cpa = 0.0
                elif tau_cpa > 1.0:
                    tau_cpa = 1.0
                cx = rx + tau_cpa * drx
                cy = ry + tau_cpa * dry
                cz = rz + tau_cpa * drz
                c_sq = cx * cx + cy * cy + cz * cz
                if c_sq < min_dist_sq:
                    min_dist_sq = c_sq

            rx += drx
            ry += dry
            rz += drz
            vy += rel_ay * dt
            vz += rel_az * dt
            am_y += dt * (cmd_y - am_y_mid) / tau_ap
            am_z += dt * (cmd_z - am_z_mid) / tau_ap

        cpa_m = math.sqrt(min_dist_sq)

        # Apply physical range & altitude envelope gates to true kill probability
        range_ratio = slant_km / max(1.0, s_range_km)
        if range_ratio > 1.12 or alt_env < -0.15 or closing_cos < -0.25:
            pk = 0.01 * math.exp(-max(0.0, range_ratio - 1.0) * 4.0)
            cpa_m = max(cpa_m, 120.0 * max(1.0, range_ratio))
        else:
            # Smooth physical lethality curve vs kill_radius_m, range margin, and EW
            cpa_ratio = cpa_m / max(2.0, kill_rad)
            kin_pk = 1.0 / (1.0 + math.exp(3.2 * (cpa_ratio - 1.05)))
            range_atten = 1.0 if range_ratio <= 0.88 else math.exp(-5.5 * (range_ratio - 0.88) ** 2)
            env_atten = 1.0 if alt_env >= 0.0 else math.exp(6.0 * alt_env)
            pk = max(0.005, min(0.985, kin_pk * range_atten * env_atten * (1.0 - 0.14 * ew_jam)))

        # Ballistic kinetic debris throw distance downrange: v_horiz * sqrt(2*h/g) * drag_decay
        fall_t = math.sqrt(2.0 * min(60_000.0, alt_m) / 9.80665)
        debris_throw_km = min(35.0, (vt_max * 0.32 * fall_t * math.exp(-alt_m / 45000.0)) * 1e-3)

        X[i, 0] = slant_km / 1000.0
        X[i, 1] = ground_range_km / 1000.0
        X[i, 2] = alt_m / 200_000.0
        X[i, 3] = math.log1p(alt_m) / 15.0
        X[i, 4] = vt_max / 7500.0
        X[i, 5] = closing_cos
        X[i, 6] = man_g / 30.0
        X[i, 7] = ew_jam
        X[i, 8] = vm_nom / 4500.0
        X[i, 9] = s_max_g / 40.0
        X[i, 10] = s_range_km / 1200.0
        X[i, 11] = alt_env
        X[i, 12] = track_sigma_m / 150.0
        X[i, 13] = is_eor

        Y[i, 0] = pk
        Y[i, 1] = cpa_m
        Y[i, 2] = t_int_s
        Y[i, 3] = debris_throw_km

    return X, Y


# ==============================================================================
# 2. NEURAL NETWORK ARCHITECTURES (COORDINATE-INVARIANT PYTORCH MPS MODELS)
# ==============================================================================

class ResidualBlock(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.ln1 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.ln2 = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.silu(self.ln1(self.fc1(x)))
        h = self.ln2(self.fc2(h))
        return F.silu(x + h)


class LatticeKinematicSurrogateNet(nn.Module):
    """
    Physics-Informed Neural Surrogate trained on 2,000,000+ 3-DoF RK4 engagements.
    Predicts [pk, cpa_miss_m, t_intercept_s, debris_throw_km] in microseconds.
    """

    def __init__(self, in_dim: int = 14, hidden_dim: int = 192):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
        )
        self.b1 = ResidualBlock(hidden_dim)
        self.b2 = ResidualBlock(hidden_dim)
        self.b3 = ResidualBlock(hidden_dim)
        self.head = nn.Linear(hidden_dim, 4)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        h = self.b3(self.b2(self.b1(self.stem(x))))
        raw = self.head(h)
        pk = torch.sigmoid(raw[..., 0])
        cpa_m = F.softplus(raw[..., 1]) * 25.0
        t_int_s = F.softplus(raw[..., 2]) * 80.0
        debris_km = F.softplus(raw[..., 3]) * 8.0
        return pk, cpa_m, t_int_s, debris_km


class MultiHeadSetAttention(nn.Module):
    """Explicit MPS-native multi-head self/cross attention without CPU fallback."""

