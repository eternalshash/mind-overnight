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

    def __init__(self, d_model: int = 128, n_heads: int = 4):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.ln = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.SiLU(),
            nn.Linear(d_model * 2, d_model),
        )
        self.ln2 = nn.LayerNorm(d_model)

    def forward(
        self,
        q_in: torch.Tensor,
        kv_in: torch.Tensor,
        kv_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        B, Nq, _ = q_in.shape
        Nk = kv_in.shape[1]
        q = self.q_proj(q_in).view(B, Nq, self.n_heads, self.d_k).transpose(1, 2)
        k = self.k_proj(kv_in).view(B, Nk, self.n_heads, self.d_k).transpose(1, 2)
        v = self.v_proj(kv_in).view(B, Nk, self.n_heads, self.d_k).transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)
        if kv_mask is not None:
            scores = scores.masked_fill(~kv_mask[:, None, None, :], -1e9)
        attn = torch.softmax(scores, dim=-1)
        ctx = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, Nq, self.d_model)
        x = self.ln(q_in + self.out_proj(ctx))
        return self.ln2(x + self.ffn(x))


class LatticeMeshDeploymentNet(nn.Module):
    """
    Autonomous Pre-Raid Spatial Mesh Placement Policy (`TEMPLATE_GEO` -> Mesh Grid).
    Under Strict Fog of War, observes ONLY:
      - Crucial Infrastructure Graph tokens [B, N_infra, 7]
      - 3D Geodesic Mesh Terrain/Horizon/Coverage tokens [B, M_mesh, 18]
      - Remaining Defense Budget & Portfolio state [B, 12]
    Outputs joint logits [B, M_mesh * 9 + 1 (STOP)] over every candidate mesh vertex
    and all 9 decoupled Lattice Sensor, EW, and Kinetic Shooter node types!
    """

    def __init__(self, d_model: int = 128, n_node_types: int = 9):
        super().__init__()
        self.n_node_types = n_node_types
        self.infra_enc = nn.Sequential(nn.Linear(7, d_model), nn.LayerNorm(d_model), nn.SiLU())
        self.mesh_enc = nn.Sequential(nn.Linear(18, d_model), nn.LayerNorm(d_model), nn.SiLU())
        self.ctx_enc = nn.Sequential(nn.Linear(12, d_model), nn.LayerNorm(d_model), nn.SiLU())

        self.infra_self_attn = MultiHeadSetAttention(d_model, n_heads=4)
        self.mesh_cross_attn = MultiHeadSetAttention(d_model, n_heads=4)
        self.mesh_self_attn = MultiHeadSetAttention(d_model, n_heads=4)

        self.node_head = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.SiLU(),
            nn.Linear(d_model, n_node_types),
        )
        self.stop_head = nn.Sequential(
            nn.Linear(d_model * 2, 64),
            nn.SiLU(),
            nn.Linear(64, 1),
        )
        self.value_head = nn.Sequential(
            nn.Linear(d_model * 2, 64),
            nn.SiLU(),
            nn.Linear(64, 1),
        )

    def forward(
        self,
        infra_tok: torch.Tensor,   # [B, N_inf, 7]
        mesh_tok: torch.Tensor,    # [B, M, 18]
        budget_ctx: torch.Tensor,  # [B, 12]
        action_mask: torch.Tensor, # [B, M * 9 + 1] bool (True = physically affordable & valid)
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        h_inf = self.infra_self_attn(self.infra_enc(infra_tok), self.infra_enc(infra_tok))
        h_mesh = self.mesh_enc(mesh_tok)
        h_mesh = self.mesh_cross_attn(h_mesh, h_inf)
        h_mesh = self.mesh_self_attn(h_mesh, h_mesh)

        h_ctx = self.ctx_enc(budget_ctx)  # [B, D]
        ctx_exp = h_ctx.unsqueeze(1).expand(-1, h_mesh.shape[1], -1)
        joint_in = torch.cat([h_mesh, ctx_exp], dim=-1)

        mesh_node_logits = self.node_head(joint_in).reshape(h_mesh.shape[0], -1)  # [B, M*9]
        pooled = torch.cat([h_mesh.mean(dim=1), h_ctx], dim=-1)
        stop_logit = self.stop_head(pooled)  # [B, 1]

        all_logits = torch.cat([mesh_node_logits, stop_logit], dim=-1)
        all_logits = all_logits.masked_fill(~action_mask, -1e9)
        state_val = self.value_head(pooled).squeeze(-1)
        return all_logits, state_val


class LatticeKillWebPolicyNet(nn.Module):
    """
    Edge-Biased Relational Cross-Attention Live Fire-Control & EW Agent.
    Reads ONLY live `EntityManagerCOP` Track tokens, Asset tokens, and pairwise
    surrogate kinematics; outputs pure learned task assignments (`INTERCEPT_TRACK`,
    `JAM_SECTOR`, or `HOLD_FIRE`) + salvo count (1 vs 2).
    """

    def __init__(self, d_model: int = 128):
        super().__init__()
        self.d_model = d_model
        self.trk_enc = nn.Sequential(nn.Linear(12, d_model), nn.LayerNorm(d_model), nn.SiLU())
        self.ast_enc = nn.Sequential(nn.Linear(10, d_model), nn.LayerNorm(d_model), nn.SiLU())
        self.edge_enc = nn.Sequential(
            nn.Linear(6, 64),
            nn.SiLU(),
            nn.Linear(64, 32),
            nn.SiLU(),
        )

        # Track-to-Track Self-Attention lets the agent perceive full wave composition & drone-bait traps!
        self.trk_self_attn = MultiHeadSetAttention(d_model, n_heads=4)
        self.ast_self_attn = MultiHeadSetAttention(d_model, n_heads=4)

        self.q_pair = nn.Linear(d_model, 64)
        self.k_pair = nn.Linear(d_model, 64)
        self.pair_scorer = nn.Sequential(
            nn.Linear(64 + 32, 64),
            nn.SiLU(),
            nn.Linear(64, 1),
        )
        self.hold_fire_head = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.SiLU(),
            nn.Linear(64, 1),
        )
        self.salvo_head = nn.Sequential(
            nn.Linear(d_model + 32, 64),
            nn.SiLU(),
            nn.Linear(64, 2),
        )

    def forward(
        self,
        trk_tok: torch.Tensor,    # [B, Nt, 12]
        ast_tok: torch.Tensor,    # [B, Na, 10]
        edge_feat: torch.Tensor,  # [B, Nt, Na, 6]
        pair_mask: torch.Tensor,  # [B, Nt, Na + 1] bool (last col = HOLD_FIRE always True)
        trk_valid: Optional[torch.Tensor] = None,
        ast_valid: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        ht = self.trk_self_attn(self.trk_enc(trk_tok), self.trk_enc(trk_tok), kv_mask=trk_valid)
        ha = self.ast_self_attn(self.ast_enc(ast_tok), self.ast_enc(ast_tok), kv_mask=ast_valid)

        qt = self.q_pair(ht).unsqueeze(2)  # [B, Nt, 1, 64]
        ka = self.k_pair(ha).unsqueeze(1)  # [B, 1, Na, 64]
        he = self.edge_enc(edge_feat)      # [B, Nt, Na, 32]

        rel = F.silu(qt + ka)
        pair_logits = self.pair_scorer(torch.cat([rel, he], dim=-1)).squeeze(-1)  # [B, Nt, Na]
        hold_logits = self.hold_fire_head(ht)  # [B, Nt, 1]

        action_logits = torch.cat([pair_logits, hold_logits], dim=-1)  # [B, Nt, Na + 1]
        action_logits = action_logits.masked_fill(~pair_mask, -1e9)

        # Salvo logits conditioned on track state + best available edge context
        best_edge = he.max(dim=2).values  # [B, Nt, 32]
        salvo_logits = self.salvo_head(torch.cat([ht, best_edge], dim=-1))  # [B, Nt, 2]
        return action_logits, salvo_logits


# ==============================================================================
# 3. STAGE 2: GPU-BATCHED GLOBAL MULTI-WAVE RAID ENVIRONMENT (1,000,000+ EPISODES)
# ==============================================================================

def _build_node_catalog_tensors(device: torch.device) -> Dict[str, torch.Tensor]:
    """Packs the 9 Lattice node specs onto `MPS` GPU tensors for vectorized rollout."""
    costs = [n.deploy_cost_musd for n in lmesh.LATTICE_NODE_CATALOG]
    shot_costs = [n.shot_cost_musd for n in lmesh.LATTICE_NODE_CATALOG]
    mags = [float(n.magazine_size) for n in lmesh.LATTICE_NODE_CATALOG]
    s_ranges = [n.sensor_range_km for n in lmesh.LATTICE_NODE_CATALOG]
    s_sigmas = [n.sensor_sigma_m for n in lmesh.LATTICE_NODE_CATALOG]
    p_alts = [n.platform_alt_agl_m for n in lmesh.LATTICE_NODE_CATALOG]
    w_ranges = [n.weapon_range_km for n in lmesh.LATTICE_NODE_CATALOG]
    min_alts = [n.min_alt_m for n in lmesh.LATTICE_NODE_CATALOG]
    max_alts = [n.max_alt_m for n in lmesh.LATTICE_NODE_CATALOG]
    speeds = [n.interceptor_speed_mps for n in lmesh.LATTICE_NODE_CATALOG]
    max_gs = [n.max_g_load for n in lmesh.LATTICE_NODE_CATALOG]
    tiers = [float(n.tier) for n in lmesh.LATTICE_NODE_CATALOG]
    is_sensor = [1.0 if n.role == "sensor" else 0.0 for n in lmesh.LATTICE_NODE_CATALOG]
    is_ew = [1.0 if n.role == "ew" else 0.0 for n in lmesh.LATTICE_NODE_CATALOG]
    is_shooter = [1.0 if n.role == "shooter" else 0.0 for n in lmesh.LATTICE_NODE_CATALOG]
    can_sea = [
        1.0 if n.node_type_id in ("altius_600_isr_picket", "sm3_block_iia_complex") else 0.0
        for n in lmesh.LATTICE_NODE_CATALOG
    ]
    return {
        "deploy_cost": torch.tensor(costs, dtype=torch.float32, device=device),
        "shot_cost": torch.tensor(shot_costs, dtype=torch.float32, device=device),
        "mag_size": torch.tensor(mags, dtype=torch.float32, device=device),
        "sensor_range": torch.tensor(s_ranges, dtype=torch.float32, device=device),
        "sensor_sigma": torch.tensor(s_sigmas, dtype=torch.float32, device=device),
        "plat_alt": torch.tensor(p_alts, dtype=torch.float32, device=device),
        "weapon_range": torch.tensor(w_ranges, dtype=torch.float32, device=device),
        "min_alt": torch.tensor(min_alts, dtype=torch.float32, device=device),
        "max_alt": torch.tensor(max_alts, dtype=torch.float32, device=device),
        "speed": torch.tensor(speeds, dtype=torch.float32, device=device),
        "max_g": torch.tensor(max_gs, dtype=torch.float32, device=device),
        "tier": torch.tensor(tiers, dtype=torch.float32, device=device),
        "is_sensor": torch.tensor(is_sensor, dtype=torch.float32, device=device),
        "is_ew": torch.tensor(is_ew, dtype=torch.float32, device=device),
        "is_shooter": torch.tensor(is_shooter, dtype=torch.float32, device=device),
        "can_sea": torch.tensor(can_sea, dtype=torch.float32, device=device),
    }


def run_batched_gpu_raid_episodes(
    batch_size: int,
    deploy_net: LatticeMeshDeploymentNet,
    killweb_net: LatticeKillWebPolicyNet,
    surrogate_net: LatticeKinematicSurrogateNet,
    cat_t: Dict[str, torch.Tensor],
    device: torch.device,
    adversarial_difficulty: float = 0.5,
    deterministic: bool = False,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, Dict[str, float]]:
    """
    Simulates `batch_size` (e.g., 1,024) complete Global Theater Raid episodes
    simultaneously on the Apple Metal `MPS` GPU under Strict Fog of War:
      1. Samples randomized global Crucial Infrastructure clusters & 3D terrain meshes
         (distinct from `GLOBAL_TEST_REGIONS` so held-out regions remain 100% unseen!).
      2. `deploy_net` sequentially places Sensors, EW Domes, and Multi-Tier Shooters
         under randomized Defense Budgets ($140M - $380M) with ZERO threat knowledge.
      3. Generates adversarial multi-wave Time-on-Target raids:
         - Wave 1: Drone swarm bait + SEAD anti-radar strikes (degrading/killing exposed radars!)
         - Wave 2: Low-altitude 35m stealth sea-skimming & supersonic cruise missiles
         - Wave 3: Quasi-ballistic weave + Mach 9-11 HGV + Exo-ICBM MIRV warheads!
      4. `killweb_net` executes pure learned multi-wave fire-control & EW assignments.
      5. Computes exact survival reward, debris standoff penalties, & cost-exchange!
    """
    B = batch_size
    N_inf = 5
    M = 48  # Candidate geodesic mesh vertices per batched global theater
    max_placements = 12

    # 1. Sample randomized Crucial Infrastructure graphs [B, N_inf]
    inf_r = torch.rand(B, N_inf, device=device) * 48.0 + 6.0
    inf_ang = torch.rand(B, N_inf, device=device) * (2.0 * math.pi)
    inf_e = inf_r * torch.sin(inf_ang)
    inf_n = inf_r * torch.cos(inf_ang)
    inf_e[:, 0], inf_n[:, 0] = 0.0, 0.0  # Central Power/C2 anchor

    is_hub = torch.zeros(B, N_inf, device=device)
    is_hub[:, :2] = 1.0  # Nodes 0 & 1 are upstream POWER_GRID & SATCOM_C2
    intrinsic_val = torch.rand(B, N_inf, device=device) * 70.0 + 115.0
    cascade_val = intrinsic_val + is_hub * 55.0
    keepout_km = torch.rand(B, N_inf, device=device) * 8.0 + 9.0
    inf_elev_km = torch.rand(B, N_inf, device=device) * 0.45

    infra_tok = torch.stack([
        inf_e / 150.0,
        inf_n / 150.0,
        intrinsic_val / 200.0,
        cascade_val / 250.0,
        keepout_km / 25.0,
        is_hub,
        inf_elev_km,
    ], dim=-1)  # [B, N_inf, 7]

    # 2. Sample 3D Geodesic Mesh rings [B, M] around infrastructure
    ring_radii = torch.tensor(
        [16.0] * 8 + [34.0] * 12 + [68.0] * 12 + [125.0] * 10 + [185.0] * 6,
        dtype=torch.float32, device=device
    ).unsqueeze(0).expand(B, -1)
    base_angles = torch.linspace(0.0, 2.0 * math.pi * (1.0 - 1.0 / M), M, device=device).unsqueeze(0)
    mesh_ang = base_angles + torch.rand(B, M, device=device) * 0.35
    mesh_e = ring_radii * torch.sin(mesh_ang)
    mesh_n = ring_radii * torch.cos(mesh_ang)

    sea_az = torch.rand(B, 1, device=device) * (2.0 * math.pi)
    coastal_proj = torch.cos(mesh_ang - sea_az)
    is_sea = ((coastal_proj > 0.35) & (ring_radii > 45.0)).float()
    elev_km = (1.0 - is_sea) * (0.25 + 1.35 * torch.rand(B, M, device=device))
    prominence = (1.0 - is_sea) * (elev_km - 0.55) * 1.4

    # 3D Terrain-masked low-altitude vs airborne horizon features on the mesh
    g_low_hor_norm = torch.clamp(0.18 + 0.48 * elev_km + 0.22 * prominence + 0.15 * is_sea, 0.08, 0.95)
    air_low_hor_norm = torch.full((B, M), 0.88, device=device)
    drone_hor_norm = torch.clamp(g_low_hor_norm + 0.22, 0.15, 0.98)

    # Distances from mesh cells to infrastructure [B, M, N_inf]
    dm_inf = torch.sqrt(
        (mesh_e.unsqueeze(2) - inf_e.unsqueeze(1)) ** 2
        + (mesh_n.unsqueeze(2) - inf_n.unsqueeze(1)) ** 2 + 1e-4
    )
    min_d_inf = dm_inf.min(dim=2).values
    tot_cval = cascade_val.sum(dim=1, keepdim=True)
    w_dist_inf = (dm_inf * cascade_val.unsqueeze(1)).sum(dim=2) / tot_cval

    inside_ko = (dm_inf < keepout_km.unsqueeze(1)).any(dim=2).float()
    standoff_score = torch.where(
        inside_ko > 0.5,
        torch.full_like(min_d_inf, 0.12),
        torch.exp(-torch.abs(min_d_inf - 34.0) / 55.0),
    )
    umb_45 = ((dm_inf <= 48.0).float() * cascade_val.unsqueeze(1)).sum(dim=2) / tot_cval
    umb_105 = ((dm_inf <= 105.0).float() * cascade_val.unsqueeze(1)).sum(dim=2) / tot_cval
    umb_220 = ((dm_inf <= 220.0).float() * cascade_val.unsqueeze(1)).sum(dim=2) / tot_cval

    static_mesh_14 = torch.stack([
        elev_km, prominence, g_low_hor_norm, air_low_hor_norm, drone_hor_norm,
        torch.clamp(min_d_inf / 100.0, 0.0, 3.0),
        torch.clamp(w_dist_inf / 100.0, 0.0, 3.0),
        standoff_score, umb_45, umb_105, umb_220, is_sea,
        mesh_e / 200.0, mesh_n / 200.0,
    ], dim=-1)  # [B, M, 14]

    # 3. Sequential Budget-Constrained Mesh Placement Rollout (Strict Fog of War!)
    init_budget = torch.rand(B, device=device) * 220.0 + 160.0  # $160M - $380M
    rem_budget = init_budget.clone()
    occupied = torch.zeros(B, M, dtype=torch.bool, device=device)
    type_counts = torch.zeros(B, 9, device=device)
    dyn_cov = torch.zeros(B, M, 4, device=device)

    placed_e = torch.zeros(B, max_placements, device=device)
    placed_n = torch.zeros(B, max_placements, device=device)
    placed_elev = torch.zeros(B, max_placements, device=device)
    placed_type = torch.zeros(B, max_placements, dtype=torch.long, device=device)
    placed_valid = torch.zeros(B, max_placements, dtype=torch.bool, device=device)

    deploy_log_probs = torch.zeros(B, device=device)
    deploy_entropy = torch.zeros(B, device=device)
    first_val_pred: Optional[torch.Tensor] = None

    mesh_pair_dist = torch.sqrt(
        (mesh_e.unsqueeze(2) - mesh_e.unsqueeze(1)) ** 2
        + (mesh_n.unsqueeze(2) - mesh_n.unsqueeze(1)) ** 2 + 1e-4
    )  # [B, M, M]

    min_node_cost = float(cat_t["deploy_cost"].min().item())
    batch_idx = torch.arange(B, device=device)

    for step in range(max_placements):
        can_continue = rem_budget >= min_node_cost
        if not can_continue.any():
            break

        mesh_tok = torch.cat([static_mesh_14, dyn_cov], dim=-1)  # [B, M, 18]
        budget_ctx = torch.cat([
            (rem_budget / 400.0).unsqueeze(1),
            (rem_budget / init_budget).unsqueeze(1),
            type_counts / 6.0,
            torch.full((B, 1), step / float(max_placements), device=device),
        ], dim=-1)  # [B, 12]

        # Build physical feasibility mask [B, M, 9]
        affordable = cat_t["deploy_cost"].view(1, 1, 9) <= rem_budget.view(B, 1, 1)
        terrain_ok = (is_sea.unsqueeze(2) < 0.5) | (cat_t["can_sea"].view(1, 1, 9) > 0.5)
        cell_free = ~occupied.unsqueeze(2)
        valid_mn = affordable & terrain_ok & cell_free  # [B, M, 9]
        has_any_valid = valid_mn.view(B, -1).any(dim=1)

        # Prevent premature STOP while >= 45% of defense budget remains unspent
        allow_stop = (~has_any_valid) | ((rem_budget / init_budget) < 0.20)
        action_mask = torch.cat([valid_mn.reshape(B, M * 9), allow_stop.unsqueeze(1)], dim=-1)

        logits, v_pred = deploy_net(infra_tok, mesh_tok, budget_ctx, action_mask)
        if first_val_pred is None:
            first_val_pred = v_pred

        probs = torch.softmax(logits, dim=-1)
        log_probs = torch.log_softmax(logits, dim=-1)
        ent = -(probs * torch.clamp(log_probs, min=-20.0)).sum(dim=-1)

        if deterministic:
            act = logits.argmax(dim=-1)
        else:
            act = torch.multinomial(probs, num_samples=1).squeeze(-1)

        is_stop = act == (M * 9)
        active = can_continue & (~is_stop)
        deploy_log_probs = deploy_log_probs + torch.where(can_continue, log_probs[batch_idx, act], torch.zeros_like(deploy_log_probs))
        deploy_entropy = deploy_entropy + torch.where(can_continue, ent, torch.zeros_like(deploy_entropy))

        safe_act = torch.clamp(act, max=M * 9 - 1)
        m_idx = safe_act // 9
        t_idx = safe_act % 9

        cost_spent = torch.where(active, cat_t["deploy_cost"][t_idx], torch.zeros_like(rem_budget))
        rem_budget = rem_budget - cost_spent

        # Record placed node
        placed_e[:, step] = mesh_e[batch_idx, m_idx]
        placed_n[:, step] = mesh_n[batch_idx, m_idx]
        placed_elev[:, step] = elev_km[batch_idx, m_idx]
        placed_type[:, step] = t_idx
        placed_valid[:, step] = active

        occupied[batch_idx, m_idx] = occupied[batch_idx, m_idx] | active
        one_hot_t = F.one_hot(t_idx, num_classes=9).float() * active.float().unsqueeze(1)
        type_counts = type_counts + one_hot_t

        # Update dynamic coverage state on mesh cells
        d_from_new = mesh_pair_dist[batch_idx, m_idx]  # [B, M]
        s_rng = cat_t["sensor_range"][t_idx].unsqueeze(1)
        w_rng = cat_t["weapon_range"][t_idx].unsqueeze(1)
        tier_v = cat_t["tier"][t_idx].unsqueeze(1)
        act_f = active.float().unsqueeze(1)

        dyn_cov[:, :, 0] += act_f * (d_from_new <= s_rng * 0.75).float() * 0.5
        dyn_cov[:, :, 1] += act_f * (cat_t["is_ew"][t_idx].unsqueeze(1) > 0.5).float() * (d_from_new <= 55.0).float()
        dyn_cov[:, :, 2] += act_f * ((tier_v >= 3.0) & (d_from_new <= w_rng)).float() * 0.5
        dyn_cov[:, :, 3] += act_f * ((tier_v >= 1.0) & (tier_v <= 2.5) & (d_from_new <= w_rng)).float() * 0.5
        dyn_cov = torch.clamp(dyn_cov, max=2.5)

    # 4. Generate Multi-Wave Adversarial Time-on-Target Raid (2 Waves x 9 Tracks = 18 Threats/Raid)
    # Wave 0: Drone-bait swarm + SEAD anti-radar strike + Subsonic stealth cruise
    # Wave 1: Supersonic cruise + Quasi-ballistic weave + Mach 10 HGV + Exo-ICBM MIRVs
    node_mags = cat_t["mag_size"][placed_type] * placed_valid.float()  # [B, Na]
    node_init_mags = torch.clamp(node_mags.clone(), min=1.0)
    node_alive = placed_valid.clone()

    # SEAD Node Attrition Check before Wave 1: if Red launches SEAD and outer radar has zero SHORAD/EW cover, 35% chance lost!
    sead_prob = 0.15 + 0.30 * adversarial_difficulty
    ast_dist_pair = torch.sqrt(
        (placed_e.unsqueeze(2) - placed_e.unsqueeze(1)) ** 2
        + (placed_n.unsqueeze(2) - placed_n.unsqueeze(1)) ** 2 + 1e-4
    )
    shorad_ew_mask = placed_valid & ((cat_t["is_ew"][placed_type] > 0.5) | (cat_t["tier"][placed_type] >= 3.0))
    protected_by_umbrella = ((ast_dist_pair <= 75.0) & shorad_ew_mask.unsqueeze(1)).any(dim=2)
    sead_roll = torch.rand(B, max_placements, device=device)
    sead_killed = (~protected_by_umbrella) & (sead_roll < sead_prob) & (cat_t["is_sensor"][placed_type] > 0.5)
    node_alive = node_alive & (~sead_killed)

    # Mesh connectivity check: isolated shooters (>350 km from any peer) suffer degraded link
    peer_online = ((ast_dist_pair <= 340.0) & node_alive.unsqueeze(1)).sum(dim=2) >= 1
    sensor_mask = node_alive & ((cat_t["sensor_range"][placed_type] >= 80.0))
    airborne_isr_count = (node_alive & (placed_type == 1)).float().sum(dim=1)  # ALTIUS-600 count
    sentry_ridge_count = (node_alive & (placed_type == 0)).float().sum(dim=1)

    kw_log_probs = torch.zeros(B, device=device)
    kw_entropy = torch.zeros(B, device=device)

    infra_damage = torch.zeros(B, N_inf, device=device)
    debris_penalties = torch.zeros(B, device=device)
    interceptor_spend_musd = torch.zeros(B, device=device)
    attacker_raid_cost_musd = torch.zeros(B, device=device)
    total_threats_killed = torch.zeros(B, device=device)
    total_threats_spawned = float(16)

    for wave_idx in range(2):
        Nt = 8
        # Wave 0 = 5 cheap drones ($0.04M) + 3 stealth sea-skimming cruise ($2.2M) -> BAIT WAVE!
        # Wave 1 = 2 supersonic cruise ($3.5M) + 2 ballistic ($4.5M) + 2 HGV ($13M) + 2 MIRV RVs ($28M) -> LETHAL WAVE!
        if wave_idx == 0:
            arch_ids = torch.tensor([0, 0, 0, 0, 0, 1, 1, 1], device=device).unsqueeze(0).expand(B, -1)
            t_speeds = torch.tensor([65., 75., 85., 70., 95., 265., 285., 275.], device=device).unsqueeze(0).expand(B, -1)
            t_alts = torch.tensor([180., 260., 320., 150., 400., 35., 30., 45.], device=device).unsqueeze(0).expand(B, -1)
            t_man_g = torch.tensor([2.5, 3.0, 4.0, 2.0, 4.5, 5.5, 6.0, 5.5], device=device).unsqueeze(0).expand(B, -1)
            t_ew_jam = torch.tensor([0.05, 0.05, 0.1, 0.05, 0.15, 0.25, 0.35, 0.25], device=device).unsqueeze(0).expand(B, -1)
            t_ew_susc = torch.tensor([0.72, 0.68, 0.60, 0.72, 0.50, 0.24, 0.18, 0.25], device=device).unsqueeze(0).expand(B, -1)
            t_costs = torch.tensor([0.04, 0.04, 0.08, 0.04, 0.15, 2.0, 3.2, 1.9], device=device).unsqueeze(0).expand(B, -1)
            t_dmg = torch.tensor([0.32, 0.32, 0.34, 0.32, 0.36, 0.68, 0.75, 0.68], device=device).unsqueeze(0).expand(B, -1)
            sub_ranges = (98.0, 40.0)  # Two range-closing ticks: Outer (only PAC-3 reaches -> learn HOLD_FIRE on drones!) -> Inner (EW/SHORAD kill zone!)
        else:
            arch_ids = torch.tensor([2, 2, 3, 3, 4, 4, 5, 5], device=device).unsqueeze(0).expand(B, -1)
            t_speeds = torch.tensor([980., 1050., 1950., 2400., 2950., 3350., 6200., 6800.], device=device).unsqueeze(0).expand(B, -1)
            t_alts = torch.tensor([120., 3500., 48000., 85000., 44000., 48000., 260000., 380000.], device=device).unsqueeze(0).expand(B, -1)
            t_man_g = torch.tensor([12.0, 14.0, 24.0, 16.0, 22.0, 20.0, 0.8, 0.8], device=device).unsqueeze(0).expand(B, -1)
            t_ew_jam = torch.tensor([0.28, 0.30, 0.50, 0.45, 0.50, 0.45, 0.45, 0.55], device=device).unsqueeze(0).expand(B, -1) * (0.6 + 0.6 * adversarial_difficulty)
            t_ew_susc = torch.tensor([0.14, 0.12, 0.04, 0.03, 0.02, 0.02, 0.0, 0.0], device=device).unsqueeze(0).expand(B, -1)
            t_costs = torch.tensor([2.8, 3.5, 3.2, 8.5, 12.0, 14.0, 25.0, 30.0], device=device).unsqueeze(0).expand(B, -1)
            t_dmg = torch.tensor([0.80, 0.82, 0.92, 0.95, 0.98, 0.98, 1.0, 1.0], device=device).unsqueeze(0).expand(B, -1)
            sub_ranges = (520.0, 82.0)  # Tick 0: Exo/Upper midcourse window (SM-3/THAAD!) -> Tick 1: Endo terminal window (PAC-3/SHORAD!)

        attacker_raid_cost_musd = attacker_raid_cost_musd + t_costs.sum(dim=1)

        tgt_idx = torch.randint(0, N_inf, (B, Nt), device=device)
        tgt_e = torch.gather(inf_e, 1, tgt_idx)
        tgt_n = torch.gather(inf_n, 1, tgt_idx)
        tgt_cval = torch.gather(cascade_val, 1, tgt_idx)
        tgt_ko = torch.gather(keepout_km, 1, tgt_idx)
        ing_ang = sea_az + (torch.rand(B, Nt, device=device) - 0.5) * (math.pi * 1.4)

        track_alive = torch.ones(B, Nt, dtype=torch.bool, device=device)
        ew_tried = torch.zeros(B, Nt, dtype=torch.bool, device=device)

        for sub_idx, nom_r_km in enumerate(sub_ranges):
            if not track_alive.any():
                break

            # Exo/Upper threats stand further out on Tick 0; cruise/drones close in
            cur_det_km = torch.where(
                (wave_idx == 1) & (sub_idx == 0) & (t_alts < 20_000.0),
                torch.full((B, Nt), 102.0, device=device),
                torch.where(
                    (wave_idx == 1) & (sub_idx == 0) & (t_alts >= 20_000.0) & (t_alts < 100_000.0),
                    torch.full((B, Nt), 175.0, device=device),
                    torch.full((B, Nt), nom_r_km, device=device),
                ),
            )

            trk_e = tgt_e + cur_det_km * torch.sin(ing_ang)
            trk_n = tgt_n + cur_det_km * torch.cos(ing_ang)
            d_trk_ast = torch.sqrt(
                (trk_e.unsqueeze(2) - placed_e.unsqueeze(1)) ** 2
                + (trk_n.unsqueeze(2) - placed_n.unsqueeze(1)) ** 2 + 1e-4
            )

            # 3D Ridge-Shadowed Horizon: low-elevation ground radars (<0.55 km) only see <500m threats within 26 km!
            ast_s_rng = cat_t["sensor_range"][placed_type].unsqueeze(1)
            ast_p_alt = cat_t["plat_alt"][placed_type].unsqueeze(1) + placed_elev.unsqueeze(1) * 1000.0
            smooth_hor = 4.12 * (torch.sqrt(ast_p_alt) + torch.sqrt(t_alts.unsqueeze(2)))
            ridge_cap = torch.where(
                (t_alts.unsqueeze(2) < 500.0) & (ast_p_alt < 600.0),
                torch.full_like(smooth_hor, 26.0),
                smooth_hor,
            )
            can_see = node_alive.unsqueeze(1) & (d_trk_ast <= torch.minimum(ast_s_rng, ridge_cap))
            space_cue = (t_alts > 55_000.0).float()
            custody_cnt = can_see.float().sum(dim=2) + space_cue
