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

        # Advance clock past expiry_time_s -> track must automatically drop from COP!
        self.assertEqual(len(cop.get_live_tracks(25.0)), 0)

    def test_02_geodesic_mesh_3d_horizon_and_cascading_infrastructure(self):
        """Verify 32-core 3D terrain horizon raycasting and upstream cascade dependencies."""
        reg = copy.deepcopy(lmesh.GLOBAL_TEST_REGIONS["taiwan_silicon_shield"])
        infra = reg["infrastructure"]
        mesh = lmesh.generate_geodesic_spatial_mesh(infra, sea_azimuth_deg=reg["sea_azimuth_deg"])

        self.assertEqual(mesh.features.shape[1], 12)
        self.assertGreaterEqual(mesh.lats.shape[0], 80)

        # Upstream POWER_GRID must have cascading_value strictly exceeding its intrinsic_value!
        power_node = next(n for n in infra if n.category == "POWER_GRID")
        self.assertGreater(power_node.cascading_value, power_node.intrinsic_value + 50.0)

        # Airborne ALTIUS-600 (2,800m) must achieve far longer 35m sea-skimmer horizon than ground radar!
        mean_ground_hor_norm = float(np.mean(mesh.features[:, 2]))
        mean_air_hor_norm = float(np.mean(mesh.features[:, 3]))
        self.assertGreater(mean_air_hor_norm, mean_ground_hor_norm * 1.4)

    def test_03_trained_mps_models_exist_and_beat_siloed_baseline_in_rk4(self):
        """Verify trained MPS checkpoints load cleanly and outperform Legacy Siloed Defense in true RK4."""
        surr, dep, kw, device = tlm.load_trained_lattice_models()
        self.assertIsNotNone(surr)

        reg = copy.deepcopy(lmesh.GLOBAL_TEST_REGIONS["taiwan_silicon_shield"])
        infra = reg["infrastructure"]
        budget = float(reg["default_budget_musd"])
        mesh = lmesh.generate_geodesic_spatial_mesh(infra, sea_azimuth_deg=reg["sea_azimuth_deg"])
        waves = rlw.build_multi_wave_tot_strike(infra, reg["sea_azimuth_deg"], "combined_tot_saturation")

        cop_n, placements_n, spent_n = lsim.deploy_neural_lattice_mesh(
            copy.deepcopy(infra), mesh, budget, dep, device
        )
        self.assertLessEqual(spent_n, budget + 1e-5)
        self.assertGreaterEqual(len(placements_n), 4)

        res_neural = lsim.execute_true_rk4_raid_simulation(
            cop_n, mesh, waves, "neural_lattice", surr, kw, device, seed=101
        )
        cop_s, _, _ = lsim.deploy_baseline_defense("siloed_legacy", copy.deepcopy(infra), mesh, budget)
        res_siloed = lsim.execute_true_rk4_raid_simulation(cop_s, mesh, waves, "siloed_greedy", seed=101)

        self.assertGreater(
            res_neural["cascading_operational_survival_pct"],
            res_siloed["cascading_operational_survival_pct"],
        )

    def test_04_sead_self_healing_mesh_routing(self):
        """Verify Lattice mesh stays online and re-routes when a forward sensor node is destroyed."""
        reg = copy.deepcopy(lmesh.GLOBAL_TEST_REGIONS["baltic_nordic_shield"])
        infra = reg["infrastructure"]
        mesh = lmesh.generate_geodesic_spatial_mesh(infra, sea_azimuth_deg=reg["sea_azimuth_deg"])
        surr, dep, kw, device = tlm.load_trained_lattice_models()

        cop, _, _ = lsim.deploy_neural_lattice_mesh(copy.deepcopy(infra), mesh, 260.0, dep, device)
        assets = cop.get_live_assets()
        self.assertGreater(len(assets), 2)

        # Simulate SEAD destroying the first deployed node
        assets[0].is_live = False
        stats = lmesh.update_self_healing_mesh_links(cop.get_live_assets(), cop.get_infrastructure_entities())
        self.assertEqual(stats["online_nodes"], stats["total_live_nodes"])


if __name__ == "__main__":
    unittest.main()
