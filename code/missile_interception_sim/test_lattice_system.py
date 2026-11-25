#!/usr/bin/env python3
"""
================================================================================
AUTOMATED PYTEST VERIFICATION SUITE FOR ANDURIL LATTICE MESH & KILL-WEB ENGINE
File: test_lattice_system.py
================================================================================
Verifies:
1. `anduril.entitymanager.v1` / `ontology.v1` / `tasks.v2` COP compliance,
   Kalman multi-sensor covariance intersection, and lost-LOS track expiry.
2. 32-core Numba 3D terrain ridge horizon raycasting & cascading infrastructure
   dependency graph propagation.
3. Pure learned PyTorch `MPS` Neural Mesh Deployment & Kill-Web Fire Control
   under Strict Fog of War.
4. Post-training True 3-DoF RK4 superiority over Legacy Siloed Defense and
   self-healing mesh resilience under SEAD node destruction.
================================================================================
"""

import copy
import json
import os
import unittest

import numpy as np
import torch

import lattice_mesh as lmesh
import lattice_sdk_schema as lsdk
import lattice_sim_engine as lsim
import run_lattice_wargame as rlw
import train_lattice_m3_ultra as tlm


class TestLatticeKillWebSystem(unittest.TestCase):

    def test_01_lattice_sdk_cop_kalman_fusion_and_track_expiry(self):
        """Verify Lattice Entity-Component JSON schema, Kalman covariance triangulation, and expiry_time."""
        cop = lsdk.EntityManagerCOP()
        rng = np.random.default_rng(42)

        # Single coarse sensor -> higher sigma (~95m -> not yet fire-control quality for EoR)
        pos1, vel1, cov1 = lsdk.fuse_sensor_measurements(
            25.0, 121.5, 45.0, (-220.0, -80.0, 0.0), [("space-ir", 120.0)], None, 2.0, rng
        )
        loc1 = lsdk.LocationComponent(pos1, vel1, cov1)
        self.assertFalse(loc1.is_fire_control_quality)

        # Dual forward Lattice Sentry + ALTIUS sensors -> triangulated fire-control sigma (<= 85m)!
        pos2, vel2, cov2 = lsdk.fuse_sensor_measurements(
            25.0, 121.5, 45.0, (-220.0, -80.0, 0.0),
            [("sentry-01", 32.0), ("altius-01", 26.0)], loc1, 2.0, rng,
        )
        loc2 = lsdk.LocationComponent(pos2, vel2, cov2)
        self.assertTrue(loc2.is_fire_control_quality)
        self.assertLess(loc2.position_sigma_m, 30.0)

        trk = lsdk.LatticeEntity(
            entity_id="trk-kalibr-01",
            is_live=True,
            created_time_s=10.0,
            expiry_time_s=20.0,
            location=loc2,
            mil_view=lsdk.MilViewComponent(lsdk.Disposition.DISPOSITION_HOSTILE, lsdk.Environment.ENVIRONMENT_AIR),
            ontology=lsdk.OntologyComponent(lsdk.OntologyTemplate.TEMPLATE_TRACK, "CRUISE_MISSILE"),
            tracked_by=lsdk.TrackedByComponent({"sentry-01", "altius-01"}, 10.0),
        )
        cop.publish_entity(trk)
        snap = cop.export_cop_snapshot(15.0)
        self.assertEqual(snap["liveEntityCount"], 1)
        ent_json = snap["entities"][0]
        self.assertEqual(ent_json["ontology"]["template"], "TEMPLATE_TRACK")
        self.assertIn("velocityEnu", ent_json["location"])
