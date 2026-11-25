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
