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

