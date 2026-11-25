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

    arsenal: Dict[str, ThreatWeaponProfile] = {}
    for item in raw_items:
        wid = item["id"]
        role = item.get("role", "attacker")
        if role not in ("attacker", "dual_role") and wid not in enrichment:
            continue
        if wid not in enrichment:
            continue
        arch, cost, rcs, mg, ew_j, ew_s, mirv, decoys, sead = enrichment[wid]
        max_mps = float(item["max_speed_kmh"]) / 3.6
        if item.get("apogee_km") is not None:
            alt_m = float(item["apogee_km"]) * 1000.0
        else:
            alt_m = float(item.get("cruise_alt_m") or 200.0)
        arsenal[wid] = ThreatWeaponProfile(
            weapon_id=wid,
            name=item["name"],
            archetype_id=arch,
            unit_cost_musd=cost,
            max_speed_mps=max_mps,
            cruise_or_apogee_m=alt_m,
            rcs_m2=rcs,
            maneuver_g=mg,
            ew_jammer_SelfProtect=ew_j,
            ew_susceptibility=ew_s,
            mirv_count=mirv,
            decoy_count=decoys,
            warhead_mass_kg=float(item.get("warhead_mass_kg", 300.0)),
            can_target_sead=sead,
        )
    return arsenal


THREAT_ARSENAL: Dict[str, ThreatWeaponProfile] = build_threat_arsenal()
THREAT_IDS_ORDERED: List[str] = list(THREAT_ARSENAL.keys())


# ==============================================================================
# 2. CASCADING CRUCIAL INFRASTRUCTURE DEPENDENCY GRAPH
# ==============================================================================

@dataclass
class CrucialInfraNode:
    """Single critical infrastructure node in a theater or global region."""
    node_id: str
    name: str
    category: str  # "POWER_GRID", "SATCOM_C2", "COMMAND_BUNKER", "SEMICONDUCTOR_FAB", "NAVAL_PORT", "AIRBASE", "METRO"
    lat: float
    lon: float
    intrinsic_value: float
    debris_keep_out_km: float = 12.0
    blast_radius_km: float = 3.5
    upstream_ids: List[str] = field(default_factory=list)
    cascading_value: float = 0.0


def compute_cascading_infrastructure_values(nodes: List[CrucialInfraNode]) -> List[CrucialInfraNode]:
    """
    Propagates downstream dependency weights upstream (2-hop damped cascade) so
    infrastructure nodes like Power Substations and SATCOM Gateways reflect both
    their intrinsic value AND the critical systems that depend on them.
    """
    by_id = {n.node_id: n for n in nodes}
    downstream_bonus = {n.node_id: 0.0 for n in nodes}

    # Pass 1: Direct dependents contribute 45% of their value to upstream providers
    for n in nodes:
        if n.upstream_ids:
            share = (0.45 * n.intrinsic_value) / len(n.upstream_ids)
            for up_id in n.upstream_ids:
                if up_id in downstream_bonus:
                    downstream_bonus[up_id] += share

    # Pass 2: 2-hop transitive cascade (25% damping)
    pass2_bonus = dict(downstream_bonus)
    for n in nodes:
        if n.upstream_ids and downstream_bonus[n.node_id] > 0:
            share = (0.25 * downstream_bonus[n.node_id]) / len(n.upstream_ids)
            for up_id in n.upstream_ids:
                if up_id in pass2_bonus:
                    pass2_bonus[up_id] += share

    for n in nodes:
        n.cascading_value = round(n.intrinsic_value + pass2_bonus[n.node_id], 2)
    return nodes


def evaluate_cascading_operational_health(
    infra_entities: List[lsdk.LatticeEntity],
) -> Tuple[float, float]:
    """
    Computes post-raid (structural_survival_pct, cascading_operational_survival_pct).
    If an upstream POWER_GRID or SATCOM_C2 node is destroyed, dependent facilities
    lose up to 35% operational capacity even if not directly hit!
    """
    if not infra_entities:
        return 100.0, 100.0

    health_by_id: Dict[str, float] = {}
    for ent in infra_entities:
        if ent.geo_infra:
            health_by_id[ent.entity_id] = ent.geo_infra.structural_health

    total_intrinsic = 0.0
    surviving_structural = 0.0
    surviving_operational = 0.0

    for ent in infra_entities:
        gi = ent.geo_infra
        if gi is None:
            continue
        val = gi.intrinsic_value
        total_intrinsic += val
        s_health = gi.structural_health

        if gi.upstream_dependencies:
            up_healths = [health_by_id.get(uid, 1.0) for uid in gi.upstream_dependencies]
            mean_up = sum(up_healths) / len(up_healths)
            # 65% autonomous backup / 35% grid-coupled capacity
            cascade_mult = 0.65 + 0.35 * mean_up
        else:
            cascade_mult = 1.0

        gi.operational_capacity = max(0.0, min(1.0, s_health * cascade_mult))
        surviving_structural += val * s_health
        surviving_operational += val * gi.operational_capacity

    denom = max(1e-6, total_intrinsic)
    return 100.0 * surviving_structural / denom, 100.0 * surviving_operational / denom


# ==============================================================================
# 3. 32-CORE NUMBA 3D TERRAIN ELEVATION & HORIZON RAYCASTING ENGINE
# ==============================================================================

@njit(fastmath=True)
def procedural_global_terrain_elevation_m(lat_deg: float, lon_deg: float, sea_azimuth_rad: float) -> float:
    """
    Deterministic multi-scale 3D topographic & coastal elevation model (meters MSL)
    for any global coordinate:
      - Models coastal ocean basins (0 m MSL) along the maritime approach sector
      - Models coastal foothills, river valleys, and mountain ridgelines (up to ~2,100 m)
        inland so sensor placement on ridges vs valleys genuinely creates 3D radar
        shadowing for low-altitude cruise missiles and drone swarms!
    """
    lat_r = math.radians(lat_deg)
    lon_r = math.radians(lon_deg)

    # Multi-harmonic deterministic continental relief
    ridge_1 = math.sin(lat_r * 47.0 + lon_r * 31.0) * math.cos(lat_r * 29.0 - lon_r * 53.0)
    ridge_2 = 0.55 * math.sin(lat_r * 113.0 - lon_r * 89.0)
    ridge_3 = 0.30 * math.cos(lat_r * 211.0 + lon_r * 173.0)

    # Directional maritime gradient relative to local sea approach bearing
    proj_sea = math.cos(lat_r) * math.cos(lon_r * 12.0 - sea_azimuth_rad)
    raw = 380.0 + 620.0 * ridge_1 + 340.0 * ridge_2 + 190.0 * ridge_3 - 260.0 * proj_sea
    if raw <= 0.0:
        return 0.0  # Maritime / sea surface (0 m MSL)
    return min(2400.0, raw)


@njit(fastmath=True)
def check_3d_los_raycast(
    s_lat: float,
    s_lon: float,
    s_alt_msl_m: float,
    t_lat: float,
    t_lon: float,
    t_alt_msl_m: float,
    sea_azimuth_rad: float,
) -> Tuple[bool, float]:
    """
    Checks 3D Line-of-Sight between a Sensor at (s_lat, s_lon, s_alt_msl_m) and
    a Threat at (t_lat, t_lon, t_alt_msl_m) over curved 4/3-refraction WGS84 Earth
    PLUS intermediate 3D terrain ridge obstructions!
    Returns: (has_los, slant_range_km)
    """
    phi1 = math.radians(s_lat)
    phi2 = math.radians(t_lat)
    dphi = phi2 - phi1
    dlam = math.radians(t_lon - s_lon)
    a = math.sin(dphi * 0.5) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam * 0.5) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    ground_dist_m = EARTH_RADIUS_M * c
    alt_diff_m = t_alt_msl_m - s_alt_msl_m
    slant_km = math.sqrt(ground_dist_m * ground_dist_m + alt_diff_m * alt_diff_m) * 1e-3

    if ground_dist_m < 1500.0:
        return True, slant_km

    # 1. Smooth 4/3-Earth radar horizon upper bound
    max_smooth_horizon_m = math.sqrt(2.0 * EFFECTIVE_RADAR_EARTH_RADIUS_M * max(1.0, s_alt_msl_m)) + math.sqrt(
        2.0 * EFFECTIVE_RADAR_EARTH_RADIUS_M * max(1.0, t_alt_msl_m)
    )
    if ground_dist_m > max_smooth_horizon_m:
        return False, slant_km

    # 2. High exo-atmospheric threats (> 65 km) above local elevation mask (> 2.5 deg) clear terrestrial ridges
    if t_alt_msl_m > 65_000.0:
        elev_angle = math.atan2(t_alt_msl_m - s_alt_msl_m - (ground_dist_m ** 2) / (2.0 * EFFECTIVE_RADAR_EARTH_RADIUS_M), ground_dist_m)
        if elev_angle > 0.042:  # > 2.4 degrees above horizon
            return True, slant_km

    # 3. Ray-march 10 intermediate terrain ridge samples along the geodesic chord
    n_samples = 10
    for k in range(1, n_samples):
        u = float(k) / float(n_samples)
        m_lat = s_lat + (t_lat - s_lat) * u
        m_lon = s_lon + (t_lon - s_lon) * u
        terrain_h = procedural_global_terrain_elevation_m(m_lat, m_lon, sea_azimuth_rad)
        # Earth bulge drop at fraction u along chord of length D: D^2 * u * (1 - u) / (2 * R_eff)
        earth_bulge_m = (ground_dist_m * ground_dist_m * u * (1.0 - u)) / (2.0 * EFFECTIVE_RADAR_EARTH_RADIUS_M)
        ray_h_msl = s_alt_msl_m + (t_alt_msl_m - s_alt_msl_m) * u - earth_bulge_m
        if ray_h_msl < terrain_h + 6.0:
            return False, slant_km

    return True, slant_km


@njit(parallel=True, fastmath=True)
def compute_mesh_horizon_features_numba(
    mesh_lats: np.ndarray,
    mesh_lons: np.ndarray,
    infra_lats: np.ndarray,
    infra_lons: np.ndarray,
    infra_vals: np.ndarray,
    infra_keepout_km: np.ndarray,
    sea_azimuth_rad: float,
) -> np.ndarray:
    """
    32-Core Parallel Spatial Mesh Evaluator!
    For every candidate vertex on the geodesic mesh, ray-casts across 16 azimuths
    and 3 threat altitude bands (35m sea-skimmer, 400m drone, 35km HGV) to compute
    a rich 12-feature geometric & topographic descriptor tensor:
      [0]  terrain_elev_km          (elevation MSL in km)
      [1]  ridge_prominence_norm    (height above surrounding 15km ring -> high ground bonus!)
      [2]  ground_low_horizon_km    (360-deg mean LOS horizon vs 35m sea-skimming cruise from 30m tower)
      [3]  airborne_low_horizon_km  (360-deg mean LOS horizon vs 35m cruise from 2.8km ALTIUS orbit)
      [4]  drone_alt_horizon_km     (360-deg mean LOS horizon vs 400m drone swarm)
      [5]  min_dist_to_infra_km     (distance to nearest crucial infrastructure node)
      [6]  weighted_dist_infra_km   (systemic-value-weighted distance to infrastructure cluster)
      [7]  debris_standoff_score    (0 if inside debris keep-out zone, peaks at 18-55 km forward standoff!)
      [8]  umbrella_30km_val_share  (share of systemic value within 45 km SHORAD/EW umbrella)
      [9]  umbrella_100km_val_share (share of systemic value within 105 km PAC-3/Roadrunner umbrella)
      [10] umbrella_220km_val_share (share of systemic value within 220 km THAAD upper-tier umbrella)
      [11] is_maritime_cell         (1.0 if over water / coastal surf, 0.0 if inland solid ground)
    """
    n_mesh = mesh_lats.shape[0]
    n_infra = infra_lats.shape[0]
    feats = np.zeros((n_mesh, 12), dtype=np.float32)
    total_val = max(1.0, float(np.sum(infra_vals)))
