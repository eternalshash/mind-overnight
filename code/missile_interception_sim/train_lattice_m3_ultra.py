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
