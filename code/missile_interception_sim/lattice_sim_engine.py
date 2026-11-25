#!/usr/bin/env python3
"""
================================================================================
TRUE 3-DOF RK4 CLOSED-LOOP LATTICE KILL-WEB & WARGAME SIMULATION ENGINE
File: lattice_sim_engine.py
================================================================================
Evaluates the trained Neural Lattice Commander (`LatticeMeshDeploymentNet` +
`LatticeKillWebPolicyNet`) inside TRUE time-stepped 3-DoF RK4 WGS84 physics
with ZERO surrogate grading and ZERO hardcoded fire-control rule cheats:

1. Pre-Raid Deployment (Strict Fog of War):
   - AI observes ONLY the Crucial Infrastructure Graph, 3D Geodesic Mesh
     Terrain/Horizon features, and Defense Budget ($B), placing `TEMPLATE_ASSET`
     Sensors, EW Domes, and Shooters onto the COP.
2. Live Multi-Wave Time-on-Target (ToT) Raid Simulation:
   - Steps true 3D threat trajectories (including MIRV post-boost warhead
     bus separation + decoys, SEAD anti-radar strikes, 30m sea-skimming,
     hypersonic skip-glide, and terminal high-G weaves).
   - Ray-casts 3D WGS84 + Terrain Ridge Line-of-Sight (`check_3d_los_raycast`)
     for every surviving sensor, fuses noisy measurements via Kalman Covariance
     Intersection into `EntityManagerCOP`, and expires stale lost-LOS tracks.
   - Neural `LatticeKillWebPolicyNet` reads ONLY the live COP and dispatches
     `anduril.tasks.v2` commands (`INTERCEPT_TRACK`, `JAM_SECTOR`, `HOLD_FIRE`).
   - Active interceptors fly true 3-DoF RK4 APN/ZEM guidance with sub-step CPA
     interpolation, debris throw keep-out evaluation, and cascading infra BDA.
3. Fair Same-Budget Baselines for Quantitative Ablation:
   - `SiloedLegacyBaseline`: Co-located batteries (no decoupled forward Lattice
     sensors/ISR, no Engage-on-Remote, greedy earliest-TTI firing).
   - `HeuristicRingBaseline`: Uniform ring placement + rule-based firing.
================================================================================
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

import lattice_mesh as lmesh
import lattice_sdk_schema as lsdk
import train_lattice_m3_ultra as tlm


# ==============================================================================
# 1. STRIKE WAVE & ACTIVE PHYSICS OBJECTS
# ==============================================================================

@dataclass
class StrikeWaveSpec:
    """User or Red-Team strike wave definition."""
    weapon_id: str
    count: int
    launch_lat: float
    launch_lon: float
    target_node_id: str  # Infrastructure node_id OR "SEAD_RADAR" to hunt forward radars!
    tot_arrival_window_s: float = 180.0  # Synchronized Time-on-Target impact time!
    ew_jamming_boost: float = 0.0


@dataclass
