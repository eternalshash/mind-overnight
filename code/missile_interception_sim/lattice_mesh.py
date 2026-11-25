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


LATTICE_NODE_CATALOG: List[LatticeNodeSpec] = [
    # 0. Autonomous Forward Radar/EO Sentry Tower (Cheap over-the-horizon ridge sensor)
    LatticeNodeSpec(
        node_type_id="lattice_sentry_tower",
        name="Lattice Autonomous Sentry Radar/EO Tower",
        role="sensor",
        tier=0,
        deploy_cost_musd=2.0,
        shot_cost_musd=0.0,
        magazine_size=0,
        sensor_range_km=165.0,
        sensor_sigma_m=32.0,
        platform_alt_agl_m=35.0,
        weapon_range_km=0.0,
        min_alt_m=10.0,
        max_alt_m=35_000.0,
        interceptor_speed_mps=0.0,
        max_g_load=0.0,
        kill_radius_m=0.0,
        comms_range_km=320.0,
        engage_on_remote=False,
    ),
    # 1. Airborne ALTIUS-600 ISR Mesh Picket Orbit (Defeats Earth curvature vs 30m sea-skimmers!)
    LatticeNodeSpec(
        node_type_id="altius_600_isr_picket",
        name="ALTIUS-600 Airborne ISR Mesh Picket (4-Ship Orbit)",
        role="sensor",
        tier=0,
        deploy_cost_musd=3.5,
        shot_cost_musd=0.0,
        magazine_size=0,
        sensor_range_km=240.0,
        sensor_sigma_m=26.0,
        platform_alt_agl_m=2800.0,  # Airborne 2.8 km altitude unlocks ~220 km sea-skimmer horizon!
        weapon_range_km=0.0,
        min_alt_m=5.0,
        max_alt_m=25_000.0,
        interceptor_speed_mps=0.0,
        max_g_load=0.0,
        kill_radius_m=0.0,
        comms_range_km=420.0,
        engage_on_remote=False,
    ),
    # 2. Lattice Autonomous Soft-Kill EW / GNSS-RF Jammer Dome ($0 per drone/cruise soft-kill!)
    LatticeNodeSpec(
        node_type_id="lattice_ew_jammer",
        name="Lattice Pulsar Autonomous EW / GNSS-RF Jammer Dome",
        role="ew",
        tier=0,
        deploy_cost_musd=4.0,
        shot_cost_musd=0.001,
        magazine_size=999,
        sensor_range_km=95.0,
        sensor_sigma_m=55.0,
        platform_alt_agl_m=25.0,
        weapon_range_km=55.0,
        min_alt_m=5.0,
        max_alt_m=12_000.0,
        interceptor_speed_mps=300_000_000.0,
        max_g_load=99.0,
        kill_radius_m=0.0,
        comms_range_km=300.0,
        engage_on_remote=True,
        ew_jam_radius_km=55.0,
        ew_power_kw=120.0,
    ),
    # 3. Tier 5: Rheinmetall Skynex 35mm AHEAD / Phalanx C-RAM Battery
    LatticeNodeSpec(
        node_type_id="skynex_ahead_ciws",
        name="Skynex 35mm AHEAD / C-RAM Point Defense",
        role="shooter",
        tier=5,
        deploy_cost_musd=7.5,
        shot_cost_musd=0.008,  # $8k programmable airburst burst!
        magazine_size=48,
        sensor_range_km=30.0,
        sensor_sigma_m=18.0,
        platform_alt_agl_m=12.0,
        weapon_range_km=6.5,
        min_alt_m=5.0,
        max_alt_m=4_000.0,
        interceptor_speed_mps=1150.0,
        max_g_load=38.0,
        kill_radius_m=12.0,
        comms_range_km=220.0,
        engage_on_remote=True,
    ),
    # 4. Tier 4: Anduril Roadrunner-M Autonomous VTOL C-UAS / Cruise Nest
    LatticeNodeSpec(
        node_type_id="roadrunner_m_nest",
        name="Anduril Roadrunner-M Autonomous Interceptor Nest",
        role="shooter",
        tier=4,
        deploy_cost_musd=11.0,
        shot_cost_musd=0.18,  # $180k twin-turbojet interceptor
        magazine_size=28,
        sensor_range_km=45.0,  # Tiny organic sensor -> thrives on Lattice Engage-on-Remote!
        sensor_sigma_m=38.0,
        platform_alt_agl_m=15.0,
        weapon_range_km=95.0,
        min_alt_m=15.0,
        max_alt_m=10_500.0,
        interceptor_speed_mps=330.0,
        max_g_load=18.0,
        kill_radius_m=28.0,
        comms_range_km=300.0,
        engage_on_remote=True,
    ),
    # 5. Tier 4B: Iron Dome Tamir / NASAMS SHORAD-MRAD Battery
    LatticeNodeSpec(
        node_type_id="iron_dome_tamir_battery",
        name="Iron Dome Tamir / NASAMS Multi-Canister Battery",
        role="shooter",
        tier=4,
        deploy_cost_musd=18.0,
        shot_cost_musd=0.12,  # $120k Tamir round
        magazine_size=40,
        sensor_range_km=110.0,
        sensor_sigma_m=30.0,
        platform_alt_agl_m=18.0,
        weapon_range_km=70.0,
        min_alt_m=15.0,
        max_alt_m=12_000.0,
        interceptor_speed_mps=760.0,
        max_g_load=28.0,
        kill_radius_m=26.0,
        comms_range_km=280.0,
        engage_on_remote=True,
    ),
    # 6. Tier 3: Patriot PAC-3 MSE Lower-Tier ATBM / Cruise / HGV Terminal Battery
    LatticeNodeSpec(
        node_type_id="patriot_pac3_mse",
        name="MIM-104 Patriot PAC-3 MSE IBCS/Lattice Battery",
        role="shooter",
        tier=3,
        deploy_cost_musd=38.0,
        shot_cost_musd=4.0,  # $4.0M per PAC-3 MSE!
        magazine_size=32,
        sensor_range_km=210.0,
        sensor_sigma_m=22.0,
        platform_alt_agl_m=22.0,
        weapon_range_km=110.0,
        min_alt_m=45.0,
        max_alt_m=38_000.0,
        interceptor_speed_mps=1820.0,
        max_g_load=35.0,
        kill_radius_m=16.0,
        comms_range_km=380.0,
        engage_on_remote=True,
    ),
    # 7. Tier 2: THAAD Upper-Tier Endo/Exo Ballistic & Hypersonic Glide Battery
    LatticeNodeSpec(
        node_type_id="thaad_battery",
        name="THAAD Upper-Tier + AN/TPY-2 X-Band Battery",
        role="shooter",
        tier=2,
        deploy_cost_musd=65.0,
        shot_cost_musd=12.0,  # $12.0M per THAAD round
        magazine_size=24,
        sensor_range_km=850.0,
        sensor_sigma_m=20.0,
        platform_alt_agl_m=25.0,
        weapon_range_km=220.0,
        min_alt_m=38_000.0,
        max_alt_m=155_000.0,
        interceptor_speed_mps=2750.0,
        max_g_load=30.0,
        kill_radius_m=15.0,
        comms_range_km=550.0,
        engage_on_remote=True,
    ),
    # 8. Tier 1: Aegis Ashore / Naval SM-3 Block IIA & GBI Exo-Midcourse Complex
    LatticeNodeSpec(
        node_type_id="sm3_block_iia_complex",
        name="Aegis SM-3 Block IIA / GBI Exo-Midcourse Complex",
        role="shooter",
        tier=1,
        deploy_cost_musd=85.0,
        shot_cost_musd=24.0,  # $24.0M per SM-3 Block IIA
        magazine_size=20,
        sensor_range_km=1400.0,
        sensor_sigma_m=25.0,
        platform_alt_agl_m=30.0,
        weapon_range_km=1200.0,
        min_alt_m=68_000.0,
        max_alt_m=1_350_000.0,
        interceptor_speed_mps=4350.0,
        max_g_load=28.0,
        kill_radius_m=15.0,
        comms_range_km=900.0,
        engage_on_remote=True,
    ),
]

NODE_BY_ID: Dict[str, LatticeNodeSpec] = {n.node_type_id: n for n in LATTICE_NODE_CATALOG}


@dataclass(frozen=True)
class ThreatWeaponProfile:
    """Unified physical, EW, MIRV, and real-world cost profile for offensive threats."""
    weapon_id: str
    name: str
    archetype_id: int  # 0=Drone, 1=SubsonicCruise, 2=SupersonicCruise, 3=TacticalBallistic, 4=HypersonicGlide, 5=ExoICBM_MIRV
    unit_cost_musd: float
    max_speed_mps: float
    cruise_or_apogee_m: float
    rcs_m2: float
    maneuver_g: float
    ew_jammer_SelfProtect: float  # [0.0 -> 1.0]
    ew_susceptibility: float      # Susceptibility to Lattice GNSS/RF soft-kill [0.0 -> 1.0]
    mirv_count: int = 1
    decoy_count: int = 0
    warhead_mass_kg: float = 400.0
    can_target_sead: bool = False


def build_threat_arsenal() -> Dict[str, ThreatWeaponProfile]:
    """Loads `weapons_catalog.json` and enriches all offensive weapons with RCS, EW, MIRV & USD cost specs."""
    cat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weapons_catalog.json")
    raw_items = []
    if os.path.exists(cat_path):
        with open(cat_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f).get("weapons", [])

    # Calibrated open-source CSIS / DoD unit cost ($M USD), RCS (m^2), maneuver G, EW susceptibility
    enrichment = {
        "shahed_136":            (0, 0.035, 0.08,  1.8, 0.00, 0.72, 1, 0, False),
        "lancet_3":              (0, 0.040, 0.04,  4.5, 0.05, 0.65, 1, 0, True),
        "switchblade_600":       (0, 0.085, 0.03,  4.0, 0.05, 0.55, 1, 0, True),
        "anduril_bolt_m":        (0, 0.045, 0.02,  3.5, 0.05, 0.45, 1, 0, False),
        "anduril_altius_700m":   (0, 0.160, 0.05,  5.0, 0.15, 0.35, 1, 0, True),
        "bgm_109_tomahawk":      (1, 2.000, 0.05,  5.5, 0.20, 0.22, 1, 0, False),
        "storm_shadow":          (1, 3.200, 0.015, 6.5, 0.35, 0.15, 1, 0, True),
        "anduril_barracuda_100": (1, 0.190, 0.06,  5.0, 0.15, 0.30, 1, 0, False),
        "anduril_barracuda_250": (1, 0.250, 0.05,  5.5, 0.20, 0.28, 1, 0, True),
        "anduril_barracuda_500": (1, 0.380, 0.06,  5.5, 0.25, 0.25, 1, 0, False),
        "kalibr_3m54":           (2, 1.800, 0.12, 10.0, 0.25, 0.18, 1, 0, False),
        "brahmos":               (2, 3.500, 0.25, 14.0, 0.30, 0.12, 1, 0, True),
        "mgm140_atacms":         (3, 1.500, 0.25, 12.0, 0.20, 0.05, 1, 0, True),
        "iskander_m":            (3, 3.200, 0.15, 28.0, 0.55, 0.04, 1, 2, True),
        "df_21d":                (3, 8.500, 0.30, 18.0, 0.45, 0.03, 1, 2, False),
        "df_17":                 (4, 14.00, 0.08, 22.0, 0.50, 0.02, 1, 1, False),
        "kh_47m2_kinzhal":       (4, 10.50, 0.14, 18.0, 0.45, 0.03, 1, 1, True),
        "3m22_zircon":           (4, 12.00, 0.09, 16.0, 0.45, 0.02, 1, 0, False),
        "agm_183a_arrw":         (4, 15.00, 0.07, 20.0, 0.40, 0.02, 1, 0, False),
        "minuteman_iii":         (5, 45.00, 0.05,  8.0, 0.40, 0.00, 3, 4, False),
        "rs_28_sarmat":          (5, 75.00, 0.06, 10.0, 0.60, 0.00, 6, 6, False),
    }
