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
