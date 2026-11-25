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

            # MIRV Post-Boost Vehicle bus separation at u = 0.42 in exo-atmosphere!
            if th.weapon_profile.mirv_count > 1 and (not th.mirv_has_split) and u >= 0.42:
                th.mirv_has_split = True
                inf_vals = list(infra_by_id.values())
                for m_i in range(1, th.weapon_profile.mirv_count):
                    alt_inf = inf_vals[(m_i + len(newly_spawned_mirvs)) % len(inf_vals)]
                    newly_spawned_mirvs.append(ActiveThreatBody(
                        uid=f"{th.uid}-MIRV{m_i+1}",
                        weapon_profile=th.weapon_profile,
                        launch_lat=th.launch_lat,
                        launch_lon=th.launch_lon,
                        target_lat=alt_inf.location.position.latitude_degrees,
                        target_lon=alt_inf.location.position.longitude_degrees,
                        target_id=alt_inf.entity_id,
                        is_sead_hunter=False,
                        launch_time_s=th.launch_time_s,
                        impact_time_s=th.impact_time_s + m_i * 2.5,
                        ew_jam=th.ew_jam,
                        mirv_has_split=True,
                        is_active=True,
                    ))

            # Geodesic ground track + lateral hypersonic/quasi-ballistic weave
            base_lat = th.launch_lat + (th.target_lat - th.launch_lat) * u
            base_lon = th.launch_lon + (th.target_lon - th.launch_lon) * u
            arch = th.weapon_profile.archetype_id

            weave_lat = 0.0
            if arch == 4 and 0.20 < u < 0.92:
                weave_lat = 0.045 * math.sin(5.0 * math.pi * u)
            elif arch == 3 and u > 0.70:
                weave_lat = 0.015 * math.sin(9.0 * math.pi * u)

            th.lat = base_lat + weave_lat
            th.lon = base_lon
            terr_h = lmesh.procedural_global_terrain_elevation_m(th.lat, th.lon, mesh.sea_azimuth_rad)

            if arch in (0, 1):  # Terrain-following / sea-skimming drone or cruise
                th.alt_msl_m = terr_h + th.weapon_profile.cruise_or_apogee_m
            elif arch == 2:  # Supersonic ramjet high-low cruise
                th.alt_msl_m = terr_h + (35.0 if u > 0.65 else min(12_000.0, th.weapon_profile.cruise_or_apogee_m))
            elif arch == 4:  # Hypersonic boost-glide skip profile (glides 42-52 km until terminal dive u > 0.88)
                glide_h = 45_000.0 + 5_500.0 * math.sin(3.5 * math.pi * u)
                dive_env = 1.0 if u <= 0.86 else max(0.05, (1.0 - u) / 0.14)
                th.alt_msl_m = max(terr_h + 25.0, glide_h * min(1.0, u / 0.14) * dive_env)
            else:  # Ballistic / ICBM suborbital Keplerian arc
                th.alt_msl_m = max(terr_h + 10.0, th.weapon_profile.cruise_or_apogee_m * 4.0 * u * (1.0 - u))

            # ENU velocity vector
            vn = ((th.target_lat - th.launch_lat) * 111_132.0) / dur
            ve = ((th.target_lon - th.launch_lon) * 111_320.0 * cos_c) / dur
            vu = -0.35 * th.weapon_profile.max_speed_mps if (arch >= 3 and u > 0.5) else 0.0
            th.vel_enu = (ve, vn, vu)
            if len(th.history_latlon) == 0 or int(sim_t) % 6 == 0:
                th.history_latlon.append((th.lat, th.lon, th.alt_msl_m))

        threats.extend(newly_spawned_mirvs)

        # 2. Sensor 3D Terrain Raycasting & Multi-Sensor Kalman Track Fusion onto `EntityManagerCOP`
        live_assets = cop.get_live_assets()
        local_los_matrix: Dict[Tuple[str, str], bool] = {}

        for th in threats:
            if (not th.is_active) or th.is_neutralized or th.has_impacted:
                cop.delete_entity(f"trk-{th.uid}")
                continue

            detecting: List[Tuple[str, float]] = []
            # Space-IR boost cueing ONLY detects bright exo-atmospheric ballistic/ICBM plumes (>55 km alt) at coarse 135m sigma
            if th.alt_msl_m > 55_000.0 and fire_control_mode != "siloed_greedy":
                detecting.append(("space-ir-opir", 135.0))

            for ast in live_assets:
                if not ast.sensors or not ast.location:
                    continue
                sm = ast.sensors.sensors[0]
                if not sm.operational or sm.max_range_km <= 1.0:
                    continue

                ap = ast.location.position
                has_los, slant_km = lmesh.check_3d_los_raycast(
                    ap.latitude_degrees, ap.longitude_degrees, ap.altitude_hae_meters,
                    th.lat, th.lon, th.alt_msl_m, mesh.sea_azimuth_rad,
                )
                # Radar range equation RCS + EW self-protect jamming burn-through reduction
                rcs_factor = max(0.42, (th.weapon_profile.rcs_m2 / 0.25) ** 0.25)
                jam_factor = 1.0 / ((1.0 + 1.8 * th.ew_jam) ** 0.25)
                eff_max_range_km = sm.max_range_km * rcs_factor * jam_factor

                if has_los and slant_km <= eff_max_range_km and sm.min_alt_m <= th.alt_msl_m <= sm.max_alt_m:
                    local_los_matrix[(th.uid, ast.entity_id)] = True
                    # In siloed_legacy mode, batteries DO NOT share tracks onto a fused mesh!
                    range_sigma = sm.base_sigma_m * (0.65 + 0.85 * (slant_km / max(10.0, sm.max_range_km))) * (1.0 + 0.6 * th.ew_jam)
                    detecting.append((ast.entity_id, range_sigma))
                else:
                    local_los_matrix[(th.uid, ast.entity_id)] = False

            trk_eid = f"trk-{th.uid}"
            existing = cop.entities.get(trk_eid)

            if detecting:
                prior_loc = existing.location if (existing and existing.is_live) else None
                # Siloed mode cannot multi-sensor triangulate covariance!
                fusion_inputs = [min(detecting, key=lambda x: x[1])] if fire_control_mode == "siloed_greedy" else detecting
                est_pos, est_vel, cov_diag = lsdk.fuse_sensor_measurements(
                    th.lat, th.lon, th.alt_msl_m, th.vel_enu, fusion_inputs, prior_loc, dt_s, rng
                )
                in_fl = existing.tracked_by.assigned_interceptors_in_flight if (existing and existing.tracked_by) else 0
                ew_j_cur = existing.tracked_by.ew_jammed_intensity if (existing and existing.tracked_by) else 0.0
                ew_att = existing.tracked_by.ew_jam_attempted if (existing and existing.tracked_by) else False

                trk_ent = lsdk.LatticeEntity(
                    entity_id=trk_eid,
                    is_live=True,
                    created_time_s=existing.created_time_s if existing else sim_t,
                    expiry_time_s=sim_t + 10.0,  # Track coasts up to 10s if LOS is subsequently lost!
                    description=f"Tracked Inbound Contact {th.uid}",
                    provenance=lsdk.Provenance("lattice-sensor-fusion", "FusedTrack", sim_t),
                    aliases=lsdk.AliasesComponent(name=th.uid),
                    location=lsdk.LocationComponent(est_pos, est_vel, cov_diag),
                    mil_view=lsdk.MilViewComponent(
                        lsdk.Disposition.DISPOSITION_HOSTILE,
                        lsdk.Environment.ENVIRONMENT_SPACE if est_pos.altitude_hae_meters > 80_000.0 else lsdk.Environment.ENVIRONMENT_AIR,
                    ),
                    ontology=lsdk.OntologyComponent(lsdk.OntologyTemplate.TEMPLATE_TRACK, "AERIAL_THREAT"),
                    tracked_by=lsdk.TrackedByComponent(
                        sensor_entity_ids={sid for sid, _ in detecting},
                        last_los_update_time_s=sim_t,
                        is_coasting=False,
                        assigned_interceptors_in_flight=in_fl,
                        ew_jammed_intensity=ew_j_cur,
                        ew_jam_attempted=ew_att,
                    ),
                )
                cop.publish_entity(trk_ent)
            elif existing and existing.is_live and sim_t <= existing.expiry_time_s:
                # Coasting track with growing covariance until `expiry_time_s`!
                est_pos, est_vel, cov_diag = lsdk.fuse_sensor_measurements(
                    th.lat, th.lon, th.alt_msl_m, th.vel_enu, [], existing.location, dt_s, rng
                )
                existing.location = lsdk.LocationComponent(est_pos, est_vel, cov_diag)
                if existing.tracked_by:
                    existing.tracked_by.sensor_entity_ids = set()
                    existing.tracked_by.is_coasting = True

        cop.sweep_expired(sim_t)

        # 3. Autonomous Fire Control & EW Tasking Decision Step
        live_tracks = cop.get_live_tracks(sim_t)
        actionable_tracks = [
            tr for tr in live_tracks
            if tr.tracked_by and tr.tracked_by.assigned_interceptors_in_flight == 0
        ]
        # Order actionable tracks by highest closing speed / urgency so hypersonic & MIRV threats are serviced immediately
        actionable_tracks.sort(
            key=lambda tr: -(tr.location.velocity_enu.speed_mps if tr.location else 0.0)
        )
        combat_assets = [
            a for a in cop.get_live_assets()
            if a.payloads and len(a.payloads.payloads) > 0
        ]

        if actionable_tracks and combat_assets:
            if fire_control_mode == "neural_lattice":
                decisions = _neural_killweb_step(
                    actionable_tracks, combat_assets, list(infra_by_id.values()),
                    mesh, local_los_matrix, surrogate_net, killweb_net, device,
                )
            else:
                decisions = _baseline_greedy_step(
                    fire_control_mode, actionable_tracks, combat_assets,
                    list(infra_by_id.values()), local_los_matrix,
                )

            th_by_uid = {th.uid: th for th in threats}
            for trk_ent, chosen_asset, salvo_cnt, conf in decisions:
                raw_uid = trk_ent.entity_id.replace("trk-", "", 1)
                th_obj = th_by_uid.get(raw_uid)
                if th_obj is None or th_obj.is_neutralized:
                    continue

                spec = lmesh.NODE_BY_ID[chosen_asset.ontology.platform_type]
                has_local = local_los_matrix.get((raw_uid, chosen_asset.entity_id), False)

                if spec.role == "ew":
                    t_res = task_mgr.dispatch_task(
                        lsdk.TaskType.TASK_JAM_SECTOR, chosen_asset.entity_id, trk_ent.entity_id,
                        sim_t, salvo_count=1, local_los_available=True, neural_confidence=conf,
                    )
                    if t_res.status == lsdk.TaskStatus.STATUS_EXECUTING:
                        interceptor_spend_musd += spec.shot_cost_musd
                        if trk_ent.tracked_by:
                            trk_ent.tracked_by.ew_jam_attempted = True
                        d_km = lmesh.haversine_km(
                            chosen_asset.location.position.latitude_degrees,
                            chosen_asset.location.position.longitude_degrees,
                            th_obj.lat, th_obj.lon,
                        )
                        p_soft_kill = th_obj.weapon_profile.ew_susceptibility * max(0.0, 1.15 - d_km / 55.0)
                        if float(rng.random()) < p_soft_kill:
                            th_obj.is_neutralized = True
                            th_obj.neutralized_by = f"{chosen_asset.entity_id} (EW Soft-Kill)"
                            ew_soft_kills += 1
                            cop.delete_entity(trk_ent.entity_id)
                            intercept_events.append({
                                "time_s": round(sim_t, 1), "threat_uid": raw_uid,
                                "weapon": th_obj.weapon_profile.name, "effector": spec.name,
                                "mode": "EW_SOFT_KILL", "cpa_m": 0.0, "alt_km": round(th_obj.alt_msl_m * 1e-3, 2),
                                "engage_on_remote": False, "debris_violation": False,
                            })
                        else:
                            # Threat survived soft-kill via INS backup, but its offensive RF jammer is suppressed
                            # and kinetic shooters remain free (`assigned_interceptors_in_flight == 0`) to kill it!
                            th_obj.ew_jam = max(0.0, th_obj.ew_jam * 0.55)
                else:
                    # Siloed baseline physically cannot Engage-on-Remote without local LOS!
                    if fire_control_mode == "siloed_greedy" and not has_local:
                        continue
                    t_res = task_mgr.dispatch_task(
                        lsdk.TaskType.TASK_INTERCEPT_TRACK, chosen_asset.entity_id, trk_ent.entity_id,
                        sim_t, salvo_count=salvo_cnt, local_los_available=has_local, neural_confidence=conf,
                    )
                    if t_res.status == lsdk.TaskStatus.STATUS_EXECUTING:
                        interceptor_spend_musd += t_res.salvo_count * spec.shot_cost_musd
                        ap = chosen_asset.location.position
                        d_km = lmesh.haversine_km(ap.latitude_degrees, ap.longitude_degrees, th_obj.lat, th_obj.lon)
                        slant_m = math.hypot(d_km * 1000.0, th_obj.alt_msl_m - ap.altitude_hae_meters)
                        fly_s = 1.6 + slant_m / max(250.0, spec.interceptor_speed_mps + th_obj.weapon_profile.max_speed_mps * 0.45)
                        in_flight_interceptors.append(ActiveInterceptorBody(
                            int_id=f"INT-{len(in_flight_interceptors)+1:04d}",
                            task_id=t_res.task_id,
                            shooter_entity_id=chosen_asset.entity_id,
                            shooter_spec=spec,
                            target_uid=raw_uid,
                            engage_on_remote=t_res.engage_on_remote,
                            launch_time_s=sim_t,
                            predicted_hit_time_s=sim_t + fly_s,
                            lat=ap.latitude_degrees,
                            lon=ap.longitude_degrees,
                            alt_msl_m=ap.altitude_hae_meters,
                            salvo_size=t_res.salvo_count,
                        ))

        # 4. Resolve True 3-DoF RK4 Terminal Interceptions & Sub-Step CPA
        th_map = {th.uid: th for th in threats}
        for ib in in_flight_interceptors:
            if ib.resolved or sim_t < ib.predicted_hit_time_s:
                continue
            ib.resolved = True
            th_obj = th_map.get(ib.target_uid)
            trk_ent = cop.entities.get(f"trk-{ib.target_uid}")
            if th_obj is None or th_obj.is_neutralized or th_obj.has_impacted:
                continue

            # Run true 48-step 3-DoF RK4 terminal engagement between `ib` and `th_obj`!
            sigma_m = trk_ent.location.position_sigma_m if (trk_ent and trk_ent.location) else 95.0
            killed, cpa_m, deb_km = _run_single_true_rk4_terminal_duel(
                ib.shooter_spec, th_obj, sigma_m, ib.salvo_size, rng
            )
            if killed:
                th_obj.is_neutralized = True
                th_obj.neutralized_by = ib.shooter_entity_id
                cop.delete_entity(f"trk-{ib.target_uid}")

                # Check if kinetic intercept occurred inside any Crucial Infrastructure Debris Keep-Out Zone!
                deb_viol = False
                for inf_e in infra_by_id.values():
                    ip = inf_e.location.position
                    d_inf = lmesh.haversine_km(th_obj.lat, th_obj.lon, ip.latitude_degrees, ip.longitude_degrees)
                    if inf_e.geo_infra and d_inf < (inf_e.geo_infra.debris_keep_out_km + deb_km * 0.25) and th_obj.alt_msl_m < 35_000.0:
                        deb_viol = True
                        debris_collateral_events += 1
                        inf_e.geo_infra.debris_collateral_hits += 1
                        inf_e.geo_infra.structural_health = max(0.0, inf_e.geo_infra.structural_health - 0.12)

                intercept_events.append({
                    "time_s": round(sim_t, 1),
                    "threat_uid": ib.target_uid,
                    "weapon": th_obj.weapon_profile.name,
                    "effector": ib.shooter_spec.name,
                    "salvo": ib.salvo_size,
                    "mode": "ENGAGE_ON_REMOTE" if ib.engage_on_remote else "ORGANIC_LOS",
                    "cpa_m": round(cpa_m, 2),
                    "alt_km": round(th_obj.alt_msl_m * 1e-3, 2),
                    "int_lat": round(th_obj.lat, 4),
                    "int_lon": round(th_obj.lon, 4),
                    "engage_on_remote": ib.engage_on_remote,
                    "debris_violation": deb_viol,
                })
            else:
                # Shoot-Look-Shoot BDA: clear in-flight counter so surviving track can be re-engaged!
                if trk_ent and trk_ent.tracked_by:
                    trk_ent.tracked_by.assigned_interceptors_in_flight = max(
                        0, trk_ent.tracked_by.assigned_interceptors_in_flight - ib.salvo_size
                    )

        # 5. Resolve Leaker Impacts on Crucial Infrastructure or SEAD Radar Targets!
        for th in threats:
            if th.is_active and (not th.is_neutralized) and (not th.has_impacted) and sim_t >= th.impact_time_s:
                th.has_impacted = True
                cop.delete_entity(f"trk-{th.uid}")

                if th.is_sead_hunter:
                    ast_hit = cop.entities.get(th.target_id)
                    if ast_hit and ast_hit.is_live:
                        ast_hit.is_live = False
                        sead_nodes_lost += 1
                        # Self-healing Lattice mesh immediately recomputes multi-hop RF/SATCOM routing!
                        lmesh.update_self_healing_mesh_links(cop.get_live_assets(), cop.get_infrastructure_entities())
                else:
                    inf_hit = infra_by_id.get(th.target_id)
                    if inf_hit and inf_hit.geo_infra:
                        inf_hit.geo_infra.leaker_direct_hits += 1
                        dmg = min(0.85, 0.25 + th.weapon_profile.warhead_mass_kg / 750.0)
                        inf_hit.geo_infra.structural_health = max(0.0, inf_hit.geo_infra.structural_health - dmg)

        sim_t += dt_s

    # Final Post-Raid BDA & Cascading Infrastructure Evaluation
    struct_surv, op_surv = lmesh.evaluate_cascading_operational_health(list(infra_by_id.values()))
    mesh_post = lmesh.update_self_healing_mesh_links(cop.get_live_assets(), cop.get_infrastructure_entities())

    total_threats = len(threats)
    kills = sum(1 for t in threats if t.is_neutralized)
    leakers = sum(1 for t in threats if t.has_impacted)
    eor_kills = sum(1 for e in intercept_events if e.get("engage_on_remote"))

    deploy_spend = sum(a.node_cost_musd for a in cop.entities.values() if a.ontology and a.ontology.template == lsdk.OntologyTemplate.TEMPLATE_ASSET)

    return {
        "fire_control_mode": fire_control_mode,
        "structural_survival_pct": round(struct_surv, 2),
        "cascading_operational_survival_pct": round(op_surv, 2),
        "total_threats_with_mirvs": total_threats,
        "threats_neutralized": kills,
        "intercept_rate_pct": round(100.0 * kills / max(1, total_threats), 2),
        "leaker_impacts": leakers,
        "engage_on_remote_kills": eor_kills,
        "ew_soft_kills": ew_soft_kills,
        "debris_collateral_events": debris_collateral_events,
        "sead_nodes_destroyed": sead_nodes_lost,
        "mesh_self_healing_post_raid": mesh_post,
        "deployment_spend_musd": round(deploy_spend, 2),
        "interceptor_spend_musd": round(interceptor_spend_musd, 2),
        "attacker_strike_cost_musd": round(attacker_total_cost_musd, 2),
        "favorable_shot_exchange_ratio": round(attacker_total_cost_musd / max(0.5, interceptor_spend_musd), 2),
        "intercept_events": intercept_events,
        "infrastructure_bda": [
            {
                "entity_id": e.entity_id,
                "name": e.aliases.name if e.aliases else e.entity_id,
                "category": e.geo_infra.infra_category,
                "structural_health_pct": round(e.geo_infra.structural_health * 100.0, 1),
                "operational_capacity_pct": round(e.geo_infra.operational_capacity * 100.0, 1),
                "direct_leaker_hits": e.geo_infra.leaker_direct_hits,
                "debris_collateral_hits": e.geo_infra.debris_collateral_hits,
            }
            for e in infra_by_id.values() if e.geo_infra
        ],
        "threat_trajectories": [
            {
                "uid": t.uid, "weapon": t.weapon_profile.name, "neutralized": t.is_neutralized,
                "impacted": t.has_impacted, "path": t.history_latlon,
            }
            for t in threats
        ],
        "lattice_cop_snapshot": cop.export_cop_snapshot(sim_t),
        "lattice_tasks_stream": task_mgr.export_tasks_log(),
    }


def _neural_killweb_step(
    tracks: List[lsdk.LatticeEntity],
    assets: List[lsdk.LatticeEntity],
    infra_ents: List[lsdk.LatticeEntity],
    mesh: lmesh.GeodesicSpatialMesh,
    local_los_matrix: Dict[Tuple[str, str], bool],
    surrogate_net: tlm.LatticeKinematicSurrogateNet,
    killweb_net: tlm.LatticeKillWebPolicyNet,
    device: torch.device,
) -> List[Tuple[lsdk.LatticeEntity, lsdk.LatticeEntity, int, float]]:
    """
    Pure Learned Neural C2 Inference over live `EntityManagerCOP` entities!
    Zero hardcoded weapon-matching rules: builds Track, Asset, and Surrogate
    Edge tensors and decodes `LatticeKillWebPolicyNet` logits directly.
    """
    cos_c = max(0.15, math.cos(math.radians(mesh.center_lat)))
    Nt = len(tracks)
    Na = len(assets)

    trk_rows = []
    trk_meta = []
    for tr in tracks:
        p = tr.location.position
        v = tr.location.velocity_enu
        spd = max(30.0, v.speed_mps)
        de = (p.longitude_degrees - mesh.center_lon) * 111.320 * cos_c
        dn = (p.latitude_degrees - mesh.center_lat) * 111.132

        # Estimate threatened HVA purely from observable position & velocity bearing!
        best_inf = infra_ents[0]
        min_d = 1e9
        for inf in infra_ents:
            ip = inf.location.position
            d = lmesh.haversine_km(p.latitude_degrees, p.longitude_degrees, ip.latitude_degrees, ip.longitude_degrees)
            if d < min_d:
                min_d = d
                best_inf = inf
