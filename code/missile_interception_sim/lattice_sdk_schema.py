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


