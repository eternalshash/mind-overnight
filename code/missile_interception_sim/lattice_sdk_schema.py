#!/usr/bin/env python3
"""
================================================================================
ANDURIL LATTICE SDK ENTITY-COMPONENT COP & TASKING SCHEMA LAYER
File: lattice_sdk_schema.py
================================================================================
Implements a compositional, zero-inheritance Common Operational Picture (COP)
and Tasking protocol aligned with Anduril's official Lattice SDK schemas:
  - `anduril.entitymanager.v1` (Entities as composable "bags of components",
    `is_live`, `expiry_time` track coasting/staleness, `provenance`)
  - `anduril.ontology.v1` (`TEMPLATE_ASSET`, `TEMPLATE_TRACK`, `TEMPLATE_GEO`)
  - `anduril.tasks.v2` (`Task`, `TaskStatus`, `TaskCatalog` autonomous C2 API)

Includes Multi-Sensor Covariance Intersection / Kalman Track Fusion for
`velocityEnu` and `errorCovariance`, gating "Engage-on-Remote" fire control.
================================================================================
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


# ==============================================================================
# 1. LATTICE ONTOLOGY & TASKING ENUMERATIONS
# ==============================================================================

class OntologyTemplate(str, Enum):
    """Top-level entity templates in `anduril.ontology.v1`."""
    TEMPLATE_ASSET = "TEMPLATE_ASSET"   # Controllable friendly sensor, EW, or shooter node
    TEMPLATE_TRACK = "TEMPLATE_TRACK"   # Observed threat contact on the COP
    TEMPLATE_GEO = "TEMPLATE_GEO"       # Crucial infrastructure HVA or keep-out zone


class Disposition(str, Enum):
    """Tactical allegiance in `milView` component."""
    DISPOSITION_FRIENDLY = "DISPOSITION_FRIENDLY"
    DISPOSITION_HOSTILE = "DISPOSITION_HOSTILE"
    DISPOSITION_SUSPECT = "DISPOSITION_SUSPECT"
    DISPOSITION_NEUTRAL = "DISPOSITION_NEUTRAL"
    DISPOSITION_UNKNOWN = "DISPOSITION_UNKNOWN"


class Environment(str, Enum):
    """Operational domain in `milView` component."""
    ENVIRONMENT_AIR = "ENVIRONMENT_AIR"
    ENVIRONMENT_SPACE = "ENVIRONMENT_SPACE"
    ENVIRONMENT_LAND = "ENVIRONMENT_LAND"
    ENVIRONMENT_SURFACE = "ENVIRONMENT_SURFACE"
    ENVIRONMENT_SUBSURFACE = "ENVIRONMENT_SUBSURFACE"


class TaskType(str, Enum):
    """Autonomous C2 directives supported in `anduril.tasks.v2`."""
    TASK_INTERCEPT_TRACK = "INTERCEPT_TRACK"
    TASK_JAM_SECTOR = "JAM_SECTOR"
    TASK_RETASK_ISR_ORBIT = "RETASK_ISR_ORBIT"
    TASK_HOLD_FIRE = "HOLD_FIRE"


class TaskStatus(str, Enum):
    """Lifecycle state of a Lattice `Task`."""
    STATUS_SENT = "STATUS_SENT"
    STATUS_WILCO = "STATUS_WILCO"
    STATUS_EXECUTING = "STATUS_EXECUTING"
    STATUS_DONE_OK = "STATUS_DONE_OK"
    STATUS_REJECTED = "STATUS_REJECTED"
    STATUS_FAILED = "STATUS_FAILED"


# ==============================================================================
# 2. COMPOSABLE ENTITY COMPONENTS (`anduril.entitymanager.v1`)
# ==============================================================================

@dataclass
class Provenance:
    """Source lineage metadata for an entity update."""
    integration_name: str
    data_type: str
    source_update_time_s: float = 0.0

    def to_lattice_dict(self, epoch_dt: datetime) -> Dict[str, Any]:
        ts = (epoch_dt + timedelta(seconds=float(self.source_update_time_s))).isoformat()
        return {
            "integrationName": self.integration_name,
            "dataType": self.data_type,
            "sourceUpdateTime": ts,
        }


@dataclass
class AliasesComponent:
    """Human-readable naming & callsigns."""
    name: str
    callsign: str = ""

    def to_lattice_dict(self) -> Dict[str, Any]:
        out = {"name": self.name}
        if self.callsign:
            out["callsign"] = self.callsign
        return out


@dataclass
class Position:
    """WGS84 geodetic coordinates with Height Above Ellipsoid (HAE) in meters."""
    latitude_degrees: float
    longitude_degrees: float
    altitude_hae_meters: float = 0.0

    def to_lattice_dict(self) -> Dict[str, float]:
        return {
            "latitudeDegrees": round(float(self.latitude_degrees), 6),
            "longitudeDegrees": round(float(self.longitude_degrees), 6),
            "altitudeHaeMeters": round(float(self.altitude_hae_meters), 2),
        }


@dataclass
class VelocityEnu:
    """Local East-North-Up Cartesian velocity vector in meters/second."""
    e: float = 0.0
    n: float = 0.0
    u: float = 0.0

    @property
    def speed_mps(self) -> float:
        return math.sqrt(self.e * self.e + self.n * self.n + self.u * self.u)

    def to_lattice_dict(self) -> Dict[str, float]:
        return {
            "e": round(float(self.e), 2),
            "n": round(float(self.n), 2),
            "u": round(float(self.u), 2),
        }


@dataclass
class LocationComponent:
    """Spatial positioning, ENU velocity, and 3D positional error covariance (m^2)."""
    position: Position
    velocity_enu: VelocityEnu = field(default_factory=VelocityEnu)
    # Diagonal 3x3 positional covariance [sigma_e^2, sigma_n^2, sigma_u^2] in m^2
    pos_covariance_diag_m2: Tuple[float, float, float] = (2500.0, 2500.0, 3600.0)

    @property
    def position_sigma_m(self) -> float:
        """RMS 3D positional uncertainty in meters (fire-control quality metric)."""
        return math.sqrt(max(1e-3, sum(self.pos_covariance_diag_m2) / 3.0))

    @property
    def is_fire_control_quality(self) -> bool:
        """Engage-on-Remote requires RMS track uncertainty <= 85 m."""
        return self.position_sigma_m <= 85.0

    def to_lattice_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position.to_lattice_dict(),
            "velocityEnu": self.velocity_enu.to_lattice_dict(),
            "positionErrorCovarianceM2": [round(x, 2) for x in self.pos_covariance_diag_m2],
            "rmsPositionSigmaM": round(self.position_sigma_m, 2),
        }


@dataclass
class MilViewComponent:
    """Military disposition and domain classification."""
    disposition: Disposition
    environment: Environment

    def to_lattice_dict(self) -> Dict[str, str]:
        return {
            "disposition": self.disposition.value,
            "environment": self.environment.value,
        }


@dataclass
class OntologyComponent:
    """High-level entity template and platform ontology."""
    template: OntologyTemplate
    platform_type: str = "GENERIC"

    def to_lattice_dict(self) -> Dict[str, str]:
        return {
            "template": self.template.value,
            "platformType": self.platform_type,
        }


@dataclass
class SensorMount:
    """Individual onboard sensor specification inside `SensorsComponent`."""
    sensor_id: str
    sensor_type: str  # "RADAR_X_BAND", "RADAR_S_BAND", "EO_IR", "AIRBORNE_ISR", "SPACE_IR"
    max_range_km: float
    min_alt_m: float = 10.0
    max_alt_m: float = 100_000.0
    base_sigma_m: float = 45.0
    operational: bool = True
    jamming_load: float = 0.0  # [0.0 -> 2.0+]


@dataclass
class SensorsComponent:
    """Collection of sensors mounted on a controllable Lattice Asset."""
    sensors: List[SensorMount] = field(default_factory=list)

    def to_lattice_dict(self) -> Dict[str, Any]:
        return {
            "sensors": [
                {
                    "sensorId": s.sensor_id,
                    "sensorType": s.sensor_type,
                    "maxRangeKm": s.max_range_km,
                    "operational": s.operational,
                    "jammingLoad": round(s.jamming_load, 3),
                }
                for s in self.sensors
            ]
        }


@dataclass
class PayloadMount:
    """Kinetic effector or soft-kill EW payload inside `PayloadsComponent`."""
    payload_id: str
    weapon_name: str
    tier: int  # 0=SoftKill EW, 1=Exo(GBI/SM3), 2=Upper(THAAD), 3=Mid(PAC3/S400), 4=SHORAD(Roadrunner/Tamir), 5=CIWS
    quantity_remaining: int
    quantity_initial: int
    unit_shot_cost_musd: float
    max_range_km: float
    min_intercept_alt_m: float
    max_intercept_alt_m: float
    avg_speed_mps: float
    max_g_load: float
    kill_radius_m: float
    engage_on_remote_capable: bool = True
    cooldown_remaining_s: float = 0.0


@dataclass
class PayloadsComponent:
    """Equipped kinetic magazines or EW emitters on a Lattice Asset."""
    payloads: List[PayloadMount] = field(default_factory=list)

    @property
    def total_remaining(self) -> int:
        return sum(p.quantity_remaining for p in self.payloads)

    @property
    def total_initial(self) -> int:
        return max(1, sum(p.quantity_initial for p in self.payloads))

    @property
    def magazine_fraction(self) -> float:
        return self.total_remaining / float(self.total_initial)

    def to_lattice_dict(self) -> Dict[str, Any]:
        return {
            "payloads": [
                {
                    "payloadId": p.payload_id,
                    "weaponName": p.weapon_name,
                    "tier": p.tier,
                    "quantityRemaining": p.quantity_remaining,
                    "quantityInitial": p.quantity_initial,
                    "unitShotCostMusd": p.unit_shot_cost_musd,
                    "engageOnRemoteCapable": p.engage_on_remote_capable,
                }
                for p in self.payloads
            ]
        }


@dataclass
class TrackedByComponent:
    """Kill-web provenance tracking which mesh sensors hold active custody of a Track."""
    sensor_entity_ids: Set[str] = field(default_factory=set)
    last_los_update_time_s: float = 0.0
    is_coasting: bool = False
    assigned_interceptors_in_flight: int = 0
    ew_jammed_intensity: float = 0.0
    ew_jam_attempted: bool = False

    @property
    def sensor_count(self) -> int:
        return len(self.sensor_entity_ids)

    def to_lattice_dict(self) -> Dict[str, Any]:
        return {
            "activelyTrackedByEntityIds": sorted(self.sensor_entity_ids),
            "sensorCustodyCount": self.sensor_count,
            "isCoasting": self.is_coasting,
            "assignedInterceptorsInFlight": self.assigned_interceptors_in_flight,
            "ewJammedIntensity": round(self.ew_jammed_intensity, 3),
        }


@dataclass
class TaskCatalogComponent:
    """Declares which Lattice `TaskType` commands an Asset can accept."""
    supported_tasks: List[TaskType] = field(default_factory=list)

    def supports(self, task_type: TaskType) -> bool:
        return task_type in self.supported_tasks

    def to_lattice_dict(self) -> Dict[str, Any]:
        return {"supportedTasks": [t.value for t in self.supported_tasks]}


@dataclass
class MeshLinkComponent:
    """RF / SATCOM tactical mesh networking & self-healing routing state."""
    comms_range_km: float = 280.0
    satcom_fallback: bool = True
    connected_peer_ids: List[str] = field(default_factory=list)
    hop_count_to_c2: int = 1
    link_latency_ms: float = 12.0
    is_online_in_mesh: bool = True

    def to_lattice_dict(self) -> Dict[str, Any]:
        return {
            "commsRangeKm": self.comms_range_km,
            "connectedPeerCount": len(self.connected_peer_ids),
            "hopCountToC2": self.hop_count_to_c2,
            "linkLatencyMs": round(self.link_latency_ms, 1),
            "isOnlineInMesh": self.is_online_in_mesh,
        }


@dataclass
class GeoInfrastructureComponent:
    """Crucial architecture / High-Value Asset metadata & cascading dependency state."""
    infra_category: str  # "POWER_GRID", "SATCOM_C2", "COMMAND_BUNKER", "SEMICONDUCTOR_FAB", "NAVAL_PORT", "AIRBASE", "METRO"
    intrinsic_value: float
    cascading_systemic_value: float
    debris_keep_out_km: float
    blast_radius_km: float
    upstream_dependencies: List[str] = field(default_factory=list)
    structural_health: float = 1.0  # [0.0 -> 1.0]
    operational_capacity: float = 1.0  # Includes upstream cascade losses
    debris_collateral_hits: int = 0
    leaker_direct_hits: int = 0

    def to_lattice_dict(self) -> Dict[str, Any]:
        return {
            "infraCategory": self.infra_category,
            "intrinsicValue": self.intrinsic_value,
            "cascadingSystemicValue": round(self.cascading_systemic_value, 2),
            "debrisKeepOutKm": self.debris_keep_out_km,
            "structuralHealth": round(self.structural_health, 3),
            "operationalCapacity": round(self.operational_capacity, 3),
            "debrisCollateralHits": self.debris_collateral_hits,
            "leakerDirectHits": self.leaker_direct_hits,
        }


# ==============================================================================
# 3. COMPOSITIONAL LATTICE ENTITY & ENTITY MANAGER COP
# ==============================================================================

@dataclass
class LatticeEntity:
    """
    Core interoperable Lattice COP Entity (`anduril.entitymanager.v1.Entity`).
    Acts as a composable bag of optional components with explicit `expiry_time_s`
    so lost-LOS tracks coast with growing covariance and automatically expire.
    """
    entity_id: str
    is_live: bool = True
    created_time_s: float = 0.0
    expiry_time_s: float = 3600.0
    description: str = ""
    provenance: Optional[Provenance] = None
    aliases: Optional[AliasesComponent] = None
    location: Optional[LocationComponent] = None
    mil_view: Optional[MilViewComponent] = None
    ontology: Optional[OntologyComponent] = None
    sensors: Optional[SensorsComponent] = None
    payloads: Optional[PayloadsComponent] = None
    tracked_by: Optional[TrackedByComponent] = None
    task_catalog: Optional[TaskCatalogComponent] = None
    mesh_link: Optional[MeshLinkComponent] = None
    geo_infra: Optional[GeoInfrastructureComponent] = None
    node_cost_musd: float = 0.0

    def is_expired(self, sim_time_s: float) -> bool:
        return (not self.is_live) or (sim_time_s > self.expiry_time_s)

    def to_lattice_json(self, epoch_dt: Optional[datetime] = None) -> Dict[str, Any]:
        """Serializes entity to canonical Lattice SDK camelCase JSON format."""
        if epoch_dt is None:
            epoch_dt = datetime(2026, 11, 25, 0, 0, 0, tzinfo=timezone.utc)
        exp_iso = (epoch_dt + timedelta(seconds=float(self.expiry_time_s))).isoformat()
