#!/usr/bin/env python3
"""
================================================================================
GEODESIC SPATIAL MESH, 3D TERRAIN HORIZON & CRUCIAL INFRASTRUCTURE ENGINE
File: lattice_mesh.py
================================================================================
Implements:
1. Decoupled Anduril Lattice Node Catalog & Real-World Weapon Economics ($M USD)
   spanning Sensors (Sentry Towers, ALTIUS-600 ISR Orbits), Soft-Kill EW Domes,
   and 5 Kinetic Shooter Tiers (CIWS -> Roadrunner-M/Tamir -> PAC-3 -> THAAD -> SM-3/GBI),
   plus all 28+ offensive munitions from `weapons_catalog.json`.
2. Cascading Crucial Infrastructure Dependency Graph (`InfrastructureGraph`)
   with PageRank-style systemic cascade multipliers & Debris Keep-Out Perimeters.
3. 32-Core Numba-Accelerated Geodesic Hexagonal Spatial Mesh & 3D WGS84 + Terrain
   Ridge Horizon Raycaster (`compute_mesh_horizon_features`), identifying high
   ridgelines, coastal sea-skimming corridors, debris standoff clearance, and
   k-connected self-healing RF/SATCOM mesh topology.
================================================================================
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Use Numba's native POSIX pthread workqueue across all 32 cores so Anaconda libiomp5 never collides with PyTorch libomp on macOS ARM64
os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
from numba import njit, prange

import lattice_sdk_schema as lsdk

EARTH_RADIUS_M = 6_371_000.0
EARTH_RADIUS_KM = 6_371.0
EFFECTIVE_RADAR_EARTH_RADIUS_M = 8_495_000.0  # 4/3 Earth atmospheric refraction model


# ==============================================================================
# 1. DECOUPLED LATTICE NODE CATALOG & REAL-WORLD WEAPON ECONOMICS ($M USD)
# ==============================================================================

@dataclass(frozen=True)
class LatticeNodeSpec:
    """Specification and real-world procurement/deployment slice cost ($M USD)."""
    node_type_id: str
    name: str
    role: str  # "sensor", "ew", "shooter"
    tier: int  # 0=Sensor/EW, 1=Exo, 2=Upper, 3=Mid, 4=SHORAD, 5=CIWS
    deploy_cost_musd: float
    shot_cost_musd: float
    magazine_size: int
    sensor_range_km: float
    sensor_sigma_m: float
    platform_alt_agl_m: float  # e.g., 25m tower vs 2,500m airborne ALTIUS ISR orbit!
    weapon_range_km: float
    min_alt_m: float
    max_alt_m: float
    interceptor_speed_mps: float
    max_g_load: float
    kill_radius_m: float
    comms_range_km: float
    engage_on_remote: bool
    ew_jam_radius_km: float = 0.0
    ew_power_kw: float = 0.0
