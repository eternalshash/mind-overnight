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
class ActiveThreatBody:
    """True ground-truth 3-DoF physical state (HIDDEN from AI until sensor LOS!)."""
    uid: str
    weapon_profile: lmesh.ThreatWeaponProfile
    launch_lat: float
    launch_lon: float
    target_lat: float
    target_lon: float
    target_id: str
    is_sead_hunter: bool
    launch_time_s: float
    impact_time_s: float
    ew_jam: float
    is_decoy: bool = False
    mirv_has_split: bool = False
    is_active: bool = False
    is_neutralized: bool = False
    has_impacted: bool = False
    neutralized_by: str = ""
    lat: float = 0.0
    lon: float = 0.0
    alt_msl_m: float = 0.0
    vel_enu: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    history_latlon: List[Tuple[float, float, float]] = field(default_factory=list)


@dataclass
class ActiveInterceptorBody:
    """In-flight kinetic interceptor launched via a Lattice `INTERCEPT_TRACK` task."""
    int_id: str
    task_id: str
    shooter_entity_id: str
    shooter_spec: lmesh.LatticeNodeSpec
    target_uid: str
    engage_on_remote: bool
    launch_time_s: float
    predicted_hit_time_s: float
    lat: float
    lon: float
    alt_msl_m: float
    salvo_size: int
    resolved: bool = False


# ==============================================================================
# 2. PRE-RAID DEPLOYMENT: PURE LEARNED NEURAL MESH vs. BASELINES
# ==============================================================================

def deploy_neural_lattice_mesh(
    infra_nodes: List[lmesh.CrucialInfraNode],
    mesh: lmesh.GeodesicSpatialMesh,
    budget_musd: float,
    deploy_net: tlm.LatticeMeshDeploymentNet,
    device: torch.device,
) -> Tuple[lsdk.EntityManagerCOP, List[Dict[str, Any]], float]:
    """
    Executes `LatticeMeshDeploymentNet` under Strict Fog of War (zero threat data!)
    to place decoupled Sensors, EW Domes, and Multi-Tier Shooters onto `mesh`.
    """
    cop = lsdk.EntityManagerCOP()
    register_infrastructure_on_cop(cop, infra_nodes)

    cat_t = tlm._build_node_catalog_tensors(device)
    cos_c = max(0.15, math.cos(math.radians(mesh.center_lat)))

    # Build [1, N_inf, 7] tensor matching training scaling
    inf_rows = []
    for n in infra_nodes:
        de = (n.lon - mesh.center_lon) * 111.320 * cos_c
        dn = (n.lat - mesh.center_lat) * 111.132
        elev_km = lmesh.procedural_global_terrain_elevation_m(n.lat, n.lon, mesh.sea_azimuth_rad) / 1000.0
        is_hub = 1.0 if n.category in ("POWER_GRID", "SATCOM_C2") else 0.0
        inf_rows.append([de / 150.0, dn / 150.0, n.intrinsic_value / 200.0, n.cascading_value / 250.0, n.debris_keep_out_km / 25.0, is_hub, elev_km])
    infra_tok = torch.tensor([inf_rows], dtype=torch.float32, device=device)

    M = mesh.lats.shape[0]
    static_14 = np.concatenate(
        [mesh.features, (mesh.rel_east_km / 200.0)[:, None], (mesh.rel_north_km / 200.0)[:, None]],
        axis=1,
    )
    static_t = torch.tensor(static_14, dtype=torch.float32, device=device).unsqueeze(0)  # [1, M, 14]
    is_sea_t = torch.tensor(mesh.features[:, 11], dtype=torch.float32, device=device).unsqueeze(0)

    mesh_e_t = torch.tensor(mesh.rel_east_km, dtype=torch.float32, device=device)
    mesh_n_t = torch.tensor(mesh.rel_north_km, dtype=torch.float32, device=device)
    d_mesh_pair = torch.sqrt((mesh_e_t[:, None] - mesh_e_t[None, :]) ** 2 + (mesh_n_t[:, None] - mesh_n_t[None, :]) ** 2 + 1e-4)

    rem_b = float(budget_musd)
    min_cost = float(min(s.deploy_cost_musd for s in lmesh.LATTICE_NODE_CATALOG))
    occupied = torch.zeros(1, M, dtype=torch.bool, device=device)
    type_counts = torch.zeros(1, 9, device=device)
    dyn_cov = torch.zeros(1, M, 4, device=device)

    placements: List[Dict[str, Any]] = []
    max_steps = 28

    with torch.no_grad():
        for step in range(max_steps):
            if rem_b < min_cost:
                break
            mesh_tok = torch.cat([static_t, dyn_cov], dim=-1)
            rem_t = torch.tensor([[rem_b / 400.0, rem_b / max(1.0, budget_musd)]], dtype=torch.float32, device=device)
            step_t = torch.tensor([[min(1.0, step / 12.0)]], dtype=torch.float32, device=device)
            b_ctx = torch.cat([rem_t, type_counts / 6.0, step_t], dim=-1)

            affordable = cat_t["deploy_cost"].view(1, 1, 9) <= rem_b
            terrain_ok = (is_sea_t.unsqueeze(2) < 0.5) | (cat_t["can_sea"].view(1, 1, 9) > 0.5)
            valid_mn = affordable & terrain_ok & (~occupied.unsqueeze(2))
            if not valid_mn.any():
                break

            allow_stop = torch.tensor([[rem_b / max(1.0, budget_musd) < 0.06]], dtype=torch.bool, device=device)
            mask = torch.cat([valid_mn.reshape(1, M * 9), allow_stop], dim=-1)

            logits, _ = deploy_net(infra_tok, mesh_tok, b_ctx, mask)
            act = int(logits[0].argmax().item())
            if act == M * 9:
                break

            m_idx = act // 9
            t_idx = act % 9
            spec = lmesh.LATTICE_NODE_CATALOG[t_idx]
            rem_b -= spec.deploy_cost_musd
            occupied[0, m_idx] = True
            type_counts[0, t_idx] += 1.0

            d_new = d_mesh_pair[m_idx].unsqueeze(0)
            dyn_cov[:, :, 0] += (d_new <= spec.sensor_range_km * 0.75).float() * 0.5
            if spec.role == "ew":
                dyn_cov[:, :, 1] += (d_new <= 55.0).float()
            elif spec.tier >= 3:
                dyn_cov[:, :, 2] += (d_new <= spec.weapon_range_km).float() * 0.5
            elif spec.tier >= 1:
                dyn_cov[:, :, 3] += (d_new <= spec.weapon_range_km).float() * 0.5
            dyn_cov = torch.clamp(dyn_cov, max=2.5)

            lat = float(mesh.lats[m_idx])
            lon = float(mesh.lons[m_idx])
            terr_m = lmesh.procedural_global_terrain_elevation_m(lat, lon, mesh.sea_azimuth_rad)
            ent_id = f"asset-{spec.node_type_id[:10]}-{len(placements)+1:02d}"
            ent = instantiate_lattice_asset_entity(ent_id, spec, lat, lon, terr_m)
            cop.publish_entity(ent)
            placements.append({
                "entity_id": ent_id,
                "node_type_id": spec.node_type_id,
                "name": spec.name,
                "role": spec.role,
                "tier": spec.tier,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "terrain_elev_m": round(terr_m, 1),
                "deploy_cost_musd": spec.deploy_cost_musd,
                "mesh_vertex_idx": m_idx,
            })

    lmesh.update_self_healing_mesh_links(cop.get_live_assets(), cop.get_infrastructure_entities())
    spent = round(budget_musd - rem_b, 2)
    return cop, placements, spent


def deploy_baseline_defense(
    mode: str,
    infra_nodes: List[lmesh.CrucialInfraNode],
    mesh: lmesh.GeodesicSpatialMesh,
    budget_musd: float,
) -> Tuple[lsdk.EntityManagerCOP, List[Dict[str, Any]], float]:
    """
    Deploys fair same-budget ($B) comparison baselines:
      - `siloed_legacy`: Co-located traditional SAM/CIWS batteries directly on HVAs
        (NO forward Lattice Sentry radars, NO airborne ALTIUS ISR, NO Engage-on-Remote!).
      - `heuristic_ring`: Fixed geometric ring rule around center.
    """
    cop = lsdk.EntityManagerCOP()
    register_infrastructure_on_cop(cop, infra_nodes)
    rem_b = float(budget_musd)
    placements: List[Dict[str, Any]] = []

    if mode == "siloed_legacy":
        # Legacy doctrine buys heavy co-located batteries right near HVAs (often inside debris keep-out!)
        order = ["thaad_battery", "patriot_pac3_mse", "iron_dome_tamir_battery", "patriot_pac3_mse", "skynex_ahead_ciws", "sm3_block_iia_complex"]
        idx = 0
        while rem_b >= 7.5 and idx < 24:
            spec = lmesh.NODE_BY_ID[order[idx % len(order)]]
            if spec.deploy_cost_musd > rem_b:
                idx += 1
                if idx > 30:
                    break
                continue
            tgt_inf = infra_nodes[idx % len(infra_nodes)]
            lat = tgt_inf.lat + 0.03 * math.cos(idx * 1.7)
            lon = tgt_inf.lon + 0.03 * math.sin(idx * 1.7)
            terr_m = lmesh.procedural_global_terrain_elevation_m(lat, lon, mesh.sea_azimuth_rad)
            ent_id = f"siloed-{spec.node_type_id[:8]}-{len(placements)+1:02d}"
            ent = instantiate_lattice_asset_entity(ent_id, spec, lat, lon, terr_m, engage_on_remote_override=False)
            cop.publish_entity(ent)
            rem_b -= spec.deploy_cost_musd
            placements.append({
                "entity_id": ent_id, "node_type_id": spec.node_type_id, "name": spec.name,
                "role": spec.role, "tier": spec.tier, "lat": round(lat, 5), "lon": round(lon, 5),
                "terrain_elev_m": round(terr_m, 1), "deploy_cost_musd": spec.deploy_cost_musd,
            })
            idx += 1
    else:
        # Heuristic uniform ring around center
        order = ["thaad_battery", "patriot_pac3_mse", "roadrunner_m_nest", "iron_dome_tamir_battery", "lattice_sentry_tower", "skynex_ahead_ciws"]
        land_indices = [i for i in range(len(mesh.lats)) if mesh.features[i, 11] < 0.5]
        idx = 0
        while rem_b >= 2.0 and idx < 26 and land_indices:
            spec = lmesh.NODE_BY_ID[order[idx % len(order)]]
            if spec.deploy_cost_musd > rem_b:
                idx += 1
                continue
            m_i = land_indices[(idx * 7) % len(land_indices)]
            lat, lon = float(mesh.lats[m_i]), float(mesh.lons[m_i])
            terr_m = lmesh.procedural_global_terrain_elevation_m(lat, lon, mesh.sea_azimuth_rad)
            ent_id = f"ring-{spec.node_type_id[:8]}-{len(placements)+1:02d}"
            ent = instantiate_lattice_asset_entity(ent_id, spec, lat, lon, terr_m, engage_on_remote_override=True)
            cop.publish_entity(ent)
            rem_b -= spec.deploy_cost_musd
            placements.append({
                "entity_id": ent_id, "node_type_id": spec.node_type_id, "name": spec.name,
                "role": spec.role, "tier": spec.tier, "lat": round(lat, 5), "lon": round(lon, 5),
                "terrain_elev_m": round(terr_m, 1), "deploy_cost_musd": spec.deploy_cost_musd,
            })
            idx += 1
