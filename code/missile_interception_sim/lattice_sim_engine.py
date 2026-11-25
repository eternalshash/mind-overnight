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

    lmesh.update_self_healing_mesh_links(cop.get_live_assets(), cop.get_infrastructure_entities())
    return cop, placements, round(budget_musd - rem_b, 2)


def register_infrastructure_on_cop(cop: lsdk.EntityManagerCOP, infra_nodes: List[lmesh.CrucialInfraNode]) -> None:
    lmesh.compute_cascading_infrastructure_values(infra_nodes)
    for n in infra_nodes:
        ent = lsdk.LatticeEntity(
            entity_id=n.node_id,
            is_live=True,
            expiry_time_s=999_999.0,
            description=f"Crucial Infrastructure: {n.name}",
            provenance=lsdk.Provenance("lattice-geo-registry", "CrucialInfrastructure"),
            aliases=lsdk.AliasesComponent(name=n.name),
            location=lsdk.LocationComponent(position=lsdk.Position(n.lat, n.lon, 15.0)),
            mil_view=lsdk.MilViewComponent(lsdk.Disposition.DISPOSITION_FRIENDLY, lsdk.Environment.ENVIRONMENT_LAND),
            ontology=lsdk.OntologyComponent(lsdk.OntologyTemplate.TEMPLATE_GEO, n.category),
            geo_infra=lsdk.GeoInfrastructureComponent(
                infra_category=n.category,
                intrinsic_value=n.intrinsic_value,
                cascading_systemic_value=n.cascading_value,
                debris_keep_out_km=n.debris_keep_out_km,
                blast_radius_km=n.blast_radius_km,
                upstream_dependencies=list(n.upstream_ids),
            ),
        )
        cop.publish_entity(ent)


def instantiate_lattice_asset_entity(
    entity_id: str,
    spec: lmesh.LatticeNodeSpec,
    lat: float,
    lon: float,
    terrain_elev_m: float,
    engage_on_remote_override: Optional[bool] = None,
) -> lsdk.LatticeEntity:
    alt_msl = terrain_elev_m + spec.platform_alt_agl_m
    env = lsdk.Environment.ENVIRONMENT_AIR if spec.platform_alt_agl_m > 500.0 else lsdk.Environment.ENVIRONMENT_LAND
    eor = spec.engage_on_remote if engage_on_remote_override is None else engage_on_remote_override

    sensors_comp = lsdk.SensorsComponent([
        lsdk.SensorMount(
            sensor_id=f"{entity_id}-sens",
            sensor_type="AIRBORNE_ISR" if spec.platform_alt_agl_m > 500.0 else "RADAR_MULTI_MODE",
            max_range_km=spec.sensor_range_km,
            min_alt_m=5.0,
            max_alt_m=max(50_000.0, spec.max_alt_m),
            base_sigma_m=spec.sensor_sigma_m,
        )
    ])

    payloads_list = []
    tasks_supported = [lsdk.TaskType.TASK_HOLD_FIRE]
    if spec.role == "shooter":
        payloads_list.append(lsdk.PayloadMount(
            payload_id=f"{entity_id}-mag",
            weapon_name=spec.name,
            tier=spec.tier,
            quantity_remaining=spec.magazine_size,
            quantity_initial=spec.magazine_size,
            unit_shot_cost_musd=spec.shot_cost_musd,
            max_range_km=spec.weapon_range_km,
            min_intercept_alt_m=spec.min_alt_m,
            max_intercept_alt_m=spec.max_alt_m,
            avg_speed_mps=spec.interceptor_speed_mps,
            max_g_load=spec.max_g_load,
            kill_radius_m=spec.kill_radius_m,
            engage_on_remote_capable=eor,
        ))
        tasks_supported.append(lsdk.TaskType.TASK_INTERCEPT_TRACK)
    elif spec.role == "ew":
        payloads_list.append(lsdk.PayloadMount(
            payload_id=f"{entity_id}-ew",
            weapon_name=spec.name,
            tier=0,
            quantity_remaining=999,
            quantity_initial=999,
            unit_shot_cost_musd=spec.shot_cost_musd,
            max_range_km=spec.ew_jam_radius_km,
            min_intercept_alt_m=spec.min_alt_m,
            max_intercept_alt_m=spec.max_alt_m,
            avg_speed_mps=3e8,
            max_g_load=99.0,
            kill_radius_m=0.0,
            engage_on_remote_capable=True,
        ))
        tasks_supported.append(lsdk.TaskType.TASK_JAM_SECTOR)
    else:
        tasks_supported.append(lsdk.TaskType.TASK_RETASK_ISR_ORBIT)

    return lsdk.LatticeEntity(
        entity_id=entity_id,
        is_live=True,
        expiry_time_s=999_999.0,
        description=spec.name,
        provenance=lsdk.Provenance("lattice-asset-gateway", spec.node_type_id),
        aliases=lsdk.AliasesComponent(name=spec.name, callsign=entity_id.upper()),
        location=lsdk.LocationComponent(
            position=lsdk.Position(lat, lon, alt_msl),
            pos_covariance_diag_m2=(1.0, 1.0, 1.0),
        ),
        mil_view=lsdk.MilViewComponent(lsdk.Disposition.DISPOSITION_FRIENDLY, env),
        ontology=lsdk.OntologyComponent(lsdk.OntologyTemplate.TEMPLATE_ASSET, spec.node_type_id),
        sensors=sensors_comp,
        payloads=lsdk.PayloadsComponent(payloads_list),
        task_catalog=lsdk.TaskCatalogComponent(tasks_supported),
        mesh_link=lsdk.MeshLinkComponent(
            comms_range_km=spec.comms_range_km,
            satcom_fallback=(engage_on_remote_override is not False),
        ),
        node_cost_musd=spec.deploy_cost_musd,
    )


# ==============================================================================
# 3. TRUE 3-DOF RK4 CLOSED-LOOP RAID EXECUTION ENGINE
# ==============================================================================

def execute_true_rk4_raid_simulation(
    cop: lsdk.EntityManagerCOP,
    mesh: lmesh.GeodesicSpatialMesh,
    strike_waves: List[StrikeWaveSpec],
    fire_control_mode: str,  # "neural_lattice", "siloed_greedy", "heuristic_ring"
    surrogate_net: Optional[tlm.LatticeKinematicSurrogateNet] = None,
    killweb_net: Optional[tlm.LatticeKillWebPolicyNet] = None,
    device: Optional[torch.device] = None,
    seed: int = 101,
) -> Dict[str, Any]:
    """
    Runs a complete time-stepped 3-DoF kinematic & RK4 terminal simulation (`dt=2.0s`
    theater clock + `48-step RK4` terminal homing + quadratic sub-step CPA) to
    evaluate defense performance without surrogate grading!
    """
    rng = np.random.default_rng(seed)
    task_mgr = lsdk.LatticeTaskManager(cop)
    infra_by_id = {e.entity_id: e for e in cop.get_infrastructure_entities()}
    assets_list = cop.get_live_assets()

    # 1. Instantiate all offensive threat bodies with synchronized Time-on-Target launch times!
    threats: List[ActiveThreatBody] = []
    attacker_total_cost_musd = 0.0

    radar_targets = [
        a for a in assets_list
        if a.ontology and a.ontology.platform_type in ("lattice_sentry_tower", "patriot_pac3_mse", "thaad_battery")
    ]

    for w_i, wave in enumerate(strike_waves):
        prof = lmesh.THREAT_ARSENAL[wave.weapon_id]
        for c_i in range(wave.count):
            attacker_total_cost_musd += prof.unit_cost_musd
            is_sead = wave.target_node_id == "SEAD_RADAR" and len(radar_targets) > 0
            if is_sead:
                r_tgt = radar_targets[(w_i + c_i) % len(radar_targets)]
                t_lat = r_tgt.location.position.latitude_degrees
                t_lon = r_tgt.location.position.longitude_degrees
                tid = r_tgt.entity_id
            else:
                inf_e = infra_by_id.get(wave.target_node_id, list(infra_by_id.values())[c_i % len(infra_by_id)])
                t_lat = inf_e.location.position.latitude_degrees
                t_lon = inf_e.location.position.longitude_degrees
                tid = inf_e.entity_id

            l_lat = wave.launch_lat + float(rng.uniform(-0.08, 0.08))
            l_lon = wave.launch_lon + float(rng.uniform(-0.08, 0.08))
            dist_m = lmesh.haversine_km(l_lat, l_lon, t_lat, t_lon) * 1000.0
            avg_spd = max(55.0, prof.max_speed_mps * (0.86 if prof.archetype_id <= 2 else 0.78))
            flight_dur_s = max(25.0, dist_m / avg_spd)

            tot_impact_s = wave.tot_arrival_window_s + float(rng.uniform(-6.0, 12.0))
            launch_t = tot_impact_s - flight_dur_s

            threats.append(ActiveThreatBody(
                uid=f"THREAT-{len(threats)+1:03d}-{prof.weapon_id[:8]}",
                weapon_profile=prof,
                launch_lat=l_lat,
                launch_lon=l_lon,
                target_lat=t_lat,
                target_lon=t_lon,
                target_id=tid,
                is_sead_hunter=is_sead,
                launch_time_s=launch_t,
                impact_time_s=tot_impact_s,
                ew_jam=min(1.0, prof.ew_jammer_SelfProtect + wave.ew_jamming_boost),
            ))

    if not threats:
        return {"error": "No threats in strike plan"}

    t_start = min(th.launch_time_s for th in threats)
    t_end = max(th.impact_time_s for th in threats) + 12.0
    dt_s = 2.0

    in_flight_interceptors: List[ActiveInterceptorBody] = []
    intercept_events: List[Dict[str, Any]] = []
    sead_nodes_lost = 0
    ew_soft_kills = 0
    debris_collateral_events = 0
    interceptor_spend_musd = 0.0

    # Shift simulation timeline so earliest launch begins at T=0.0s
    shift_s = -t_start if t_start < 0.0 else 0.0
    for th in threats:
        th.launch_time_s += shift_s
        th.impact_time_s += shift_s
    t_max = t_end + shift_s

    cos_c = max(0.15, math.cos(math.radians(mesh.center_lat)))
    sim_t = 0.0

    while sim_t <= t_max:
        # Cool down weapon launchers
        for ast in cop.get_live_assets():
            if ast.payloads:
                for p in ast.payloads.payloads:
                    p.cooldown_remaining_s = max(0.0, p.cooldown_remaining_s - dt_s)

        # 1. Propagate all active threat 3D trajectories & MIRV bus separation
        newly_spawned_mirvs: List[ActiveThreatBody] = []
        for th in threats:
            if th.is_neutralized or th.has_impacted:
                continue
            if sim_t < th.launch_time_s:
                continue
            th.is_active = True

            dur = max(10.0, th.impact_time_s - th.launch_time_s)
            u = min(1.0, max(0.0, (sim_t - th.launch_time_s) / dur))
