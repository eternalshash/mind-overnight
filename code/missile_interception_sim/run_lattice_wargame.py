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

