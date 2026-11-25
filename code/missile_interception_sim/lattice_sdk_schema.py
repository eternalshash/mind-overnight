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

