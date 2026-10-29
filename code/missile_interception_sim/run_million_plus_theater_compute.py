#!/usr/bin/env python3
"""
================================================================================
STANDALONE HIGH-COMPUTE THEATER WARFARE MONTE CARLO & CALIBRATION ENGINE
File: run_million_plus_theater_compute.py
================================================================================
100% SELF-CONTAINED / FORKABLE SINGLE-FILE HIGH-COMPUTE RUNNER.
Can be copied or forked independently onto any multi-core workstation, server,
or cluster to execute 1,000,000+ 3D kinematic missile defense engagements.

PURPOSE:
1. Simulates 1,000,000+ (configurable via `--runs`) 3D theater engagements
   across 4 operational theaters (Eastern Europe, Persian Gulf, Taiwan Strait,
   CONUS Homeland) and 4 threat classes (Drone Swarm, Supersonic Cruise,
   Quasi-Ballistic Maneuvering, Hypersonic Glide / ICBM).
2. Computes high-precision empirical telemetry:
   - Time-To-Impact (TTI) vs. Defender Time-To-Intercept (TTI_def)
   - Continuous quadratic Closest Point of Approach (CPA) miss distances
   - Finite battery magazine exhaustion and leaker penetration probabilities
   - Optimal forward-screen battery placement ratio for "Auto-Shield"
3. Calibrates and exports `calibrated_vulnerability_weights.json`, which is
   automatically ingested by `theater_vulnerability.py` to make the Theater
   Warfare Vulnerability & Keep-Safe Detection Algorithm empirically precise.

USAGE:
  # Standard 1,000,000-engagement high-compute run (default):
  python3 run_million_plus_theater_compute.py --runs 1000000

  # Massive 5,000,000-engagement cluster run:
  python3 run_million_plus_theater_compute.py --runs 5000000

  # Quick verification benchmark (e.g., 100,000 runs):
  python3 run_million_plus_theater_compute.py --runs 100000
================================================================================
"""

import argparse
import json
import math
import os
import sys
import time
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd

try:
    import numba
    from numba import njit, prange
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    prange = range


# ==============================================================================
# 1. EMBEDDED MULTI-THEATER GEOSPATIAL & ASSET CATALOG (ZERO EXTERNAL DEPS)
# ==============================================================================
# Each asset row: [theater_id, asset_idx, lat, lon, strategic_value, blast_tol_km, nearest_bat_dist_km, bat_wez_km, bat_mag, bat_speed_kms, bat_commit_s]
EMBEDDED_THEATER_ASSETS = np.array([
    # Theater 0: Eastern Europe / Black Sea
    [0, 0, 50.45,  30.52, 160.0, 25.0,   0.5,   70.0, 32.0, 1.60, 3.5],  # Kyiv National Strategic C2 HQ
    [0, 1, 46.49,  30.74, 120.0, 30.0,   1.9,   45.0, 24.0, 0.90, 2.5],  # Odesa Deep-Water Naval Terminal
    [0, 2, 47.81,  31.22, 145.0, 20.0, 152.6,   45.0, 24.0, 1.60, 3.5],  # Yuzhnoukrainsk Nuclear Power Grid
    # Theater 1: Persian Gulf / Arabian Peninsula
    [1, 3, 26.67,  50.16, 160.0, 30.0,   0.5,   80.0, 32.0, 1.60, 3.5],  # Ras Tanura Oil Export Terminal
    [1, 4, 24.25,  54.55, 150.0, 25.0,   0.5,  150.0, 48.0, 2.60, 4.0],  # Al Dhafra Coalition Airbase
    [1, 5, 26.21,  50.60, 155.0, 20.0,  67.3,   80.0, 32.0, 1.60, 3.5],  # NSA Bahrain / US 5th Fleet HQ
    # Theater 2: Taiwan Strait / Indo-Pacific
    [2, 6, 25.13, 121.55, 160.0, 20.0,  11.7,   70.0, 32.0, 1.60, 3.5],  # Heng Shan Joint Command Bunker
    [2, 7, 24.81, 120.94, 150.0, 25.0,  78.0,   95.0, 36.0, 1.60, 3.5],  # Hsinchu Airbase & Semiconductor Hub
    [2, 8, 22.61, 120.28, 135.0, 30.0, 177.6,   95.0, 36.0, 1.60, 3.5],  # Kaohsiung Strategic Naval Complex
    # Theater 3: CONUS Homeland Defense
    [3, 9, 38.74, -104.85, 160.0, 25.0, 778.9,  250.0, 48.0, 2.60, 4.0], # NORAD Cheyenne Mountain Complex
    [3, 10, 41.11, -95.91, 160.0, 25.0, 1390.7, 250.0, 48.0, 4.20, 6.0], # US STRATCOM Offutt AFB
    [3, 11, 47.50, -111.18, 150.0, 30.0, 910.0, 1000.0, 20.0, 4.20, 6.0], # Malmstrom AFB Nuclear Silo Wing
], dtype=np.float64)

