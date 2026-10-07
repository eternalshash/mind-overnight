#!/usr/bin/env python3
"""
================================================================================
FAAC SIMBUILDER™ ARCHITECTURE: DATA-DRIVEN WEAPON SYSTEM & IADS SIMULATOR
File: simbuilder.py
================================================================================
Implements the core design principles of FAAC SimBuilder™:
  1. Data-Driven Weapon Subsystem Modules:
     - Air-to-Air, Surface-to-Air, Surface-to-Surface, and Air-to-Surface profiles.
     - Unclassified parameterized models of known systems (PAC-3 MSE, THAAD,
       SM-3 Block IIA, Iron Dome Tamir, Roadrunner-M, Iskander-M, Kinzhal, etc.).
     - User-configurable custom weapon builder: aerodynamics, propulsion curves,
       seeker FOV, guidance laws (TPN/APN/ZEM), autopilot lag, and lethality.

  2. Integrated Air Defense System (IADS) Network:
     - Networked radar nodes (Early Warning, Fire Control Radar).
     - Aspect-dependent Radar Cross Section (RCS) model (nose, broadside, tail).
     - Spherical Earth radar horizon (4/3 R_E atmospheric refraction index).
     - Electronic warfare & countermeasures: Chaff, Flares, RF Jamming & Burn-Through.

  3. ZAP / WEZ Dynamic Launch Envelopes:
     - Launch Acceptability Region (LAR), R_max, R_ne (no-escape), and R_min.
================================================================================
"""

from __future__ import annotations
import math
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from gnc_engine import (
    G0, R_EARTH, C_SOUND_SL, GuidanceLaw, SeekerType,
    AerodynamicsModel, PropulsionModel, SeekerSensorModel, AutopilotModel,
    CountermeasureState, WeaponSpec, GNCVehicle, WeaponEngagementZone,
    compute_wez_envelope, compute_continuous_substep_cpa
)


# ==============================================================================
# 1. RADAR & IADS SENSOR MODEL (NETWORKED DEFENSE)
# ==============================================================================

@dataclass
class RadarSensorNode:
    """
    IADS ground-based or naval radar sensor node.
    Calculates physical detection ranges based on radar equation, RCS,
    aspect angle, and spherical Earth horizon.
    """
    radar_id: str
    name: str
    radar_type: str                      # 'early_warning', 'fire_control', 'ciws'
    pos_enu: np.ndarray                  # Radar coordinates [x, y, z] (m)
    max_instrumented_range_m: float      # Maximum transmitter range (m)
    reference_rcs_m2: float = 1.0        # Reference RCS calibration standard (m^2)
    nominal_range_at_ref_rcs_m: float = 120000.0 # Range against 1 m^2 RCS
    beamwidth_deg: float = 2.0           # 3dB antenna beamwidth
    elevation_coverage_deg: Tuple[float, float] = (0.5, 85.0) # Min/Max elevation
    frequency_ghz: float = 5.4           # Operating frequency (C-Band / X-Band)
    peak_power_kw: float = 120.0         # Transmitter peak power

    def compute_radar_horizon_m(self, target_alt_m: float) -> float:
        """
        Computes 4/3 Earth radius optical/RF atmospheric refraction line-of-sight horizon:
        d_los = sqrt(2 * (4/3 * R_E) * h_radar) + sqrt(2 * (4/3 * R_E) * h_target)
        """
        r_eff = (4.0 / 3.0) * R_EARTH
        h_rad = max(2.0, float(self.pos_enu[2]))
        h_tgt = max(2.0, float(target_alt_m))
        d_horizon = math.sqrt(2.0 * r_eff * h_rad) + math.sqrt(2.0 * r_eff * h_tgt)
        return d_horizon

    def compute_aspect_rcs(
        self,
        target_pos: np.ndarray,
        target_vel: np.ndarray,
        nominal_rcs: float = 1.0
    ) -> float:
        """
        Calculates aspect-dependent Radar Cross Section (RCS).
        RCS is lowest nose-on, highest broadside, and intermediate from the rear.
        """
        los_vec = target_pos - self.pos_enu
        range_m = float(np.linalg.norm(los_vec))
        if range_m < 1e-3:
            return nominal_rcs

        target_speed = float(np.linalg.norm(target_vel))
        if target_speed < 1.0:
            return nominal_rcs

        # Aspect angle: angle between target velocity vector and radar LOS
        cos_aspect = abs(float(np.dot(target_vel / target_speed, los_vec / range_m)))
        # cos_aspect = 1: nose-on or tail-on -> lower RCS
        # cos_aspect = 0: broadside (beam) -> peak specular RCS
        broadside_factor = 1.0 - cos_aspect
        aspect_rcs = nominal_rcs * (0.35 + 2.8 * (broadside_factor ** 2))
        return aspect_rcs

    def is_target_detected(
        self,
        target_pos: np.ndarray,
        target_vel: np.ndarray,
        nominal_rcs: float = 1.0,
        countermeasures: Optional[CountermeasureState] = None
    ) -> Tuple[bool, float, float]:
        """
        Determines whether the target is detected taking into account:
          - Spherical Earth line-of-sight horizon
          - Radar equation with aspect-dependent RCS
          - RF noise jamming & radar burn-through range
        Returns: (is_detected, detection_range_limit_m, current_distance_m)
        """
        rel_pos = target_pos - self.pos_enu
        dist_m = float(np.linalg.norm(rel_pos))
        target_alt = float(target_pos[2])

        # 1. Check optical/refraction horizon
        horizon_m = self.compute_radar_horizon_m(target_alt)
        if dist_m > horizon_m:
            return False, horizon_m, dist_m

        # 2. Check radar antenna elevation limits
        ground_dist = math.hypot(rel_pos[0], rel_pos[1])
        elev_deg = math.degrees(math.atan2(rel_pos[2], max(1.0, ground_dist)))
        if not (self.elevation_coverage_deg[0] <= elev_deg <= self.elevation_coverage_deg[1]):
            return False, horizon_m, dist_m

        # 3. Radar Equation range scaling: R_det = R_0 * (sigma / sigma_0)^(1/4)
        effective_rcs = self.compute_aspect_rcs(target_pos, target_vel, nominal_rcs)

        # Countermeasure: Chaff increases clutter, reducing SNR
        if countermeasures and countermeasures.chaff_active:
            effective_rcs *= 0.4

        rcs_range_m = self.nominal_range_at_ref_rcs_m * (
            (effective_rcs / max(0.01, self.reference_rcs_m2)) ** 0.25
        )
        max_effective_range = min(self.max_instrumented_range_m, rcs_range_m, horizon_m)

        # Countermeasure: RF Jamming reduces range unless inside burn-through
        if countermeasures and countermeasures.rf_jamming_active:
            # Burn-through range where radar reflected echo overcomes jamming noise
            r_burn_m = max_effective_range * 0.38
            max_effective_range = r_burn_m

        is_detected = (dist_m <= max_effective_range)
        return is_detected, max_effective_range, dist_m


# ==============================================================================
# 2. SIMBUILDER PRESET CATALOG BUILDER
# ==============================================================================

class SimBuilderCatalog:
    """
    FAAC SimBuilder library of verified unclassified missile and interceptor profiles.
    Allows generating realistic, citation-backed weapon models.
    """

    @staticmethod
    def create_patriot_pac3_mse() -> WeaponSpec:
        """MIM-104 Patriot PAC-3 MSE (Hit-to-Kill Endo-Atmospheric Interceptor)."""
        return WeaponSpec(
            weapon_id="patriot_pac3_mse",
            name="Patriot PAC-3 MSE",
            role="interceptor",
            guidance_law=GuidanceLaw.APN,
            nav_ratio_n=4.2,
            aero=AerodynamicsModel(
                ref_area_m2=0.07,
                cd_subsonic=0.19,
                cd_transonic_peak=0.55,
                cd_supersonic=0.32,
                cl_alpha_per_rad=4.2,
                max_alpha_deg=28.0,
            ),
            propulsion=PropulsionModel(
                total_mass_kg=312.0,
                dry_mass_kg=140.0,
                boost_thrust_n=55000.0,
                boost_time_s=4.0,
                sustain_thrust_n=20000.0,
                sustain_time_s=7.0,
                isp_s=270.0,
            ),
            seeker=SeekerSensorModel(
                seeker_type=SeekerType.ACTIVE_RADAR,
                max_range_m=45000.0,
                fov_deg=100.0,
                gimbal_limit_deg=65.0,
                gimbal_rate_limit_deg_s=60.0,
                angular_noise_std_rad=0.0006,
                has_eccm=True,
            ),
            autopilot=AutopilotModel(
                time_constant_tau_s=0.08,
                max_g_load=35.0,
                max_g_rate_per_s=150.0,
                enable_divert_thrusters=False,
            ),
            kill_radius_htk_m=15.0,
            kill_radius_blast_m=28.0,
        )

    @staticmethod
    def create_thaad() -> WeaponSpec:
        """Terminal High Altitude Area Defense (Exo/Endo Interceptor with DACS)."""
        return WeaponSpec(
            weapon_id="thaad_interceptor",
            name="THAAD Interceptor",
            role="interceptor",
            guidance_law=GuidanceLaw.ZEM,
            nav_ratio_n=4.5,
            aero=AerodynamicsModel(
                ref_area_m2=0.12,
                cd_subsonic=0.18,
                cd_transonic_peak=0.52,
                cd_supersonic=0.30,
                cl_alpha_per_rad=3.5,
                max_alpha_deg=22.0,
            ),
            propulsion=PropulsionModel(
                total_mass_kg=900.0,
                dry_mass_kg=350.0,
                boost_thrust_n=85000.0,
                boost_time_s=6.0,
                sustain_thrust_n=22000.0,
                sustain_time_s=10.0,
                isp_s=285.0,
            ),
            seeker=SeekerSensorModel(
                seeker_type=SeekerType.INFRARED,
                max_range_m=90000.0,
                fov_deg=80.0,
                gimbal_limit_deg=60.0,
                gimbal_rate_limit_deg_s=45.0,
                angular_noise_std_rad=0.0004,
                has_eccm=True,
            ),
            autopilot=AutopilotModel(
                time_constant_tau_s=0.06,
                max_g_load=30.0,
                max_g_rate_per_s=120.0,
                enable_divert_thrusters=True, # DACS attitude control in near-vacuum
            ),
            kill_radius_htk_m=15.0,
            kill_radius_blast_m=20.0,
        )

    @staticmethod
    def create_sm3_block_iia() -> WeaponSpec:
        """Standard Missile-3 Block IIA (Exo-Atmospheric Hit-to-Kill Ballistic Interceptor)."""
        return WeaponSpec(
            weapon_id="sm3_block_iia",
            name="SM-3 Block IIA",
            role="interceptor",
            guidance_law=GuidanceLaw.ZEM,
            nav_ratio_n=4.5,
            aero=AerodynamicsModel(
                ref_area_m2=0.23,
                cd_subsonic=0.20,
                cd_transonic_peak=0.50,
                cd_supersonic=0.28,
            ),
            propulsion=PropulsionModel(
                total_mass_kg=1500.0,
                dry_mass_kg=480.0,
                boost_thrust_n=160000.0,
                boost_time_s=8.0,
                sustain_thrust_n=45000.0,
                sustain_time_s=14.0,
                isp_s=295.0,
            ),
            seeker=SeekerSensorModel(
                seeker_type=SeekerType.INFRARED,
                max_range_m=150000.0,
                fov_deg=60.0,
                gimbal_limit_deg=50.0,
                gimbal_rate_limit_deg_s=40.0,
                angular_noise_std_rad=0.0003,
            ),
            autopilot=AutopilotModel(
                time_constant_tau_s=0.05,
                max_g_load=25.0,
                max_g_rate_per_s=100.0,
                enable_divert_thrusters=True,
            ),
            kill_radius_htk_m=15.0,
            kill_radius_blast_m=15.0,
        )

    @staticmethod
    def create_iron_dome_tamir() -> WeaponSpec:
        """Tamir Interceptor (Short-Range C-RAM & Drone Defense)."""
        return WeaponSpec(
            weapon_id="iron_dome_tamir",
            name="Iron Dome Tamir",
            role="interceptor",
            guidance_law=GuidanceLaw.TPN,
            nav_ratio_n=3.8,
            aero=AerodynamicsModel(
                ref_area_m2=0.02,
                cd_subsonic=0.24,
                cd_transonic_peak=0.62,
                cd_supersonic=0.36,
                cl_alpha_per_rad=4.5,
            ),
            propulsion=PropulsionModel(
                total_mass_kg=90.0,
                dry_mass_kg=45.0,
                boost_thrust_n=15000.0,
                boost_time_s=2.8,
                sustain_thrust_n=4200.0,
                sustain_time_s=4.5,
                isp_s=250.0,
            ),
            seeker=SeekerSensorModel(
                seeker_type=SeekerType.ACTIVE_RADAR,
                max_range_m=20000.0,
                fov_deg=110.0,
                gimbal_limit_deg=70.0,
            ),
            autopilot=AutopilotModel(
                time_constant_tau_s=0.07,
                max_g_load=30.0,
                max_g_rate_per_s=140.0,
            ),
            kill_radius_htk_m=8.0,
            kill_radius_blast_m=18.0,
        )

    @staticmethod
    def create_iskander_m() -> WeaponSpec:
        """9K720 Iskander-M (Quasi-Ballistic Missile with High-G Terminal Weave)."""
        return WeaponSpec(
            weapon_id="iskander_m",
            name="9K720 Iskander-M",
            role="threat",
            guidance_law=GuidanceLaw.PURSUIT,
            nav_ratio_n=3.0,
            aero=AerodynamicsModel(
                ref_area_m2=0.65,
                cd_subsonic=0.22,
                cd_transonic_peak=0.58,
                cd_supersonic=0.34,
                cl_alpha_per_rad=3.6,
                max_alpha_deg=30.0,
            ),
            propulsion=PropulsionModel(
                total_mass_kg=3800.0,
                dry_mass_kg=1600.0,
                boost_thrust_n=140000.0,
                boost_time_s=18.0,
                sustain_thrust_n=0.0,
                sustain_time_s=0.0,
                isp_s=260.0,
            ),
            autopilot=AutopilotModel(
                time_constant_tau_s=0.15,
                max_g_load=30.0,
                max_g_rate_per_s=90.0,
            ),
            kill_radius_htk_m=20.0,
            kill_radius_blast_m=50.0,
        )

    @staticmethod
    def create_kinzhal() -> WeaponSpec:
        """Kh-47M2 Kinzhal (Hypersonic Aero-Ballistic Missile, Mach 10)."""
        return WeaponSpec(
            weapon_id="kinzhal_hypersonic",
            name="Kh-47M2 Kinzhal",
            role="threat",
            guidance_law=GuidanceLaw.PURSUIT,
            nav_ratio_n=3.0,
            aero=AerodynamicsModel(
                ref_area_m2=0.55,
                cd_subsonic=0.19,
                cd_transonic_peak=0.52,
                cd_supersonic=0.29,
                cl_alpha_per_rad=3.4,
            ),
            propulsion=PropulsionModel(
                total_mass_kg=4300.0,
                dry_mass_kg=1900.0,
                boost_thrust_n=180000.0,
                boost_time_s=22.0,
                sustain_thrust_n=0.0,
                sustain_time_s=0.0,
                isp_s=275.0,
            ),
            autopilot=AutopilotModel(
                time_constant_tau_s=0.12,
                max_g_load=25.0,
                max_g_rate_per_s=80.0,
            ),
            kill_radius_htk_m=20.0,
            kill_radius_blast_m=60.0,
        )

    @classmethod
    def get_preset(cls, preset_name: str) -> Optional[WeaponSpec]:
        """Looks up a standard weapon specification by preset name."""
        presets = {
            "Patriot PAC-3": cls.create_patriot_pac3_mse(),
            "THAAD": cls.create_thaad(),
            "SM-3": cls.create_sm3_block_iia(),
            "Iron Dome": cls.create_iron_dome_tamir(),
            "Iskander-M": cls.create_iskander_m(),
            "Kinzhal": cls.create_kinzhal(),
        }
        return presets.get(preset_name)

    @classmethod
    def list_all_presets(cls) -> List[str]:
        return ["Patriot PAC-3", "THAAD", "SM-3", "Iron Dome", "Iskander-M", "Kinzhal"]


# ==============================================================================
# 3. IADS THEATER DEFENSE SYSTEM SIMULATOR
# ==============================================================================

@dataclass
class EngagementOutcome:
    """Complete post-flyout engagement record for academic reporting."""
    engagement_id: str
    threat_name: str
    interceptor_name: str
    guidance_law: str
    kill: bool
    hit_type: str                       # 'HTK' (Hit to Kill), 'BLAST', 'MISS'
    cpa_miss_distance_m: float
    intercept_time_s: float
    intercept_altitude_m: float
    closing_velocity_ms: float
    max_g_intercept: float
    chaff_employed: bool
    jamming_employed: bool
    telemetry_frames: int


class IADSSimulator:
    """
    Executes high-fidelity IADS multi-battery and multi-threat simulations
    using the GNC engine and SimBuilder modular models.
    """

    def __init__(self):
        self.radars: List[RadarSensorNode] = []
        self.battery_specs: Dict[str, WeaponSpec] = {}
        self.battery_positions: Dict[str, np.ndarray] = {}
        self.battery_magazines: Dict[str, int] = {}
        self.active_interceptors: List[Tuple[GNCVehicle, GNCVehicle, str]] = [] # (interceptor, target, battery_id)
        self.completed_engagements: List[EngagementOutcome] = []

    def add_radar(self, radar: RadarSensorNode):
        self.radars.append(radar)

    def add_battery(self, battery_id: str, spec: WeaponSpec, pos_enu: np.ndarray, capacity: int = 16):
        self.battery_specs[battery_id] = spec
        self.battery_positions[battery_id] = np.array(pos_enu, dtype=float)
        self.battery_magazines[battery_id] = capacity

    def launch_interceptor(self, battery_id: str, target: GNCVehicle) -> Optional[GNCVehicle]:
        """Launches an interceptor from the designated battery aimed at the incoming threat."""
        if battery_id not in self.battery_specs:
            return None
        if self.battery_magazines.get(battery_id, 0) <= 0:
            return None

        spec = self.battery_specs[battery_id]
        b_pos = self.battery_positions[battery_id]

        # Lead aim compensation for target closing vector
        los = target.pos - b_pos
        los_dist = max(float(np.linalg.norm(los)), 1.0)
        los_hat = los / los_dist

        # Collision triangle lead angle
        v_target_speed = float(np.linalg.norm(target.vel))
        lead_vec = los_hat * max(800.0, v_target_speed) + target.vel * 0.35
        lead_speed = float(np.linalg.norm(lead_vec))
        aim_hat = (lead_vec / lead_speed) if lead_speed > 1e-4 else los_hat
        init_vel = aim_hat * 200.0

        interceptor = GNCVehicle(
            spec=spec,
            initial_pos=b_pos.copy() + np.array([0.0, 0.0, 5.0]),
            initial_vel=init_vel,
            launch_time=target.flight_time,
        )

        self.battery_magazines[battery_id] -= 1
        self.active_interceptors.append((interceptor, target, battery_id))
        return interceptor

    def step_engagement(
        self,
        dt: float,
        countermeasures: Optional[CountermeasureState] = None
    ) -> List[EngagementOutcome]:
        """
        Steps all airborne interceptors, updates guidance & autopilot,
        evaluates continuous sub-timestep CPA, and logs kills.
        """
        new_outcomes = []
        remaining = []

        for interceptor, target, bat_id in self.active_interceptors:
            if not interceptor.active or not target.active:
                continue

            r_i_prev = interceptor.pos.copy()
            v_i_prev = interceptor.vel.copy()
            r_t_prev = target.pos.copy()
            v_t_prev = target.vel.copy()

            # Target acceleration
            target_accel = target.accel_achieved if hasattr(target, "accel_achieved") else np.zeros(3)

            # Step interceptor GNC loop
            interceptor.step(
                dt=dt,
                target_pos=target.pos,
                target_vel=target.vel,
                target_accel=target_accel,
                countermeasures=countermeasures,
            )

            # Check continuous sub-timestep CPA within [t_prev, t_now]
            tau_cpa, d_cpa, pos_t_cpa, pos_i_cpa = compute_continuous_substep_cpa(
                r_t_prev, v_t_prev, r_i_prev, v_i_prev, dt
            )

            v_rel = v_t_prev - v_i_prev
            closing_vel = float(np.linalg.norm(v_rel))

            # Detonation Criteria
            is_htk = (d_cpa <= interceptor.spec.kill_radius_htk_m)
            is_blast = (d_cpa <= interceptor.spec.kill_radius_blast_m)

            # Check if engagement terminated: either lethal kill or vehicles passed CPA within terminal zone
            r_rel_now = target.pos - interceptor.pos
            dist_now = float(np.linalg.norm(r_rel_now))
            passed_cpa = (float(np.dot(r_rel_now, v_rel)) > 0.0 and dist_now < 4000.0 and d_cpa > interceptor.spec.kill_radius_blast_m and interceptor.flight_time > 1.0)

            if is_htk or is_blast or passed_cpa:
                kill = is_htk or is_blast
                hit_type = "HTK" if is_htk else ("BLAST" if is_blast else "MISS")

                outcome = EngagementOutcome(
                    engagement_id=f"ENG_{bat_id}_{len(self.completed_engagements)+1}",
                    threat_name=target.spec.name if hasattr(target, "spec") else "Threat",
                    interceptor_name=interceptor.spec.name,
                    guidance_law=interceptor.spec.guidance_law.value,
                    kill=kill,
                    hit_type=hit_type,
                    cpa_miss_distance_m=round(d_cpa, 2),
                    intercept_time_s=round(interceptor.flight_time, 2),
                    intercept_altitude_m=round(float(pos_t_cpa[2]), 1),
                    closing_velocity_ms=round(closing_vel, 1),
                    max_g_intercept=round(float(np.max([f.g_load for f in interceptor.telemetry_history] or [0.0])), 1),
                    chaff_employed=countermeasures.chaff_active if countermeasures else False,
                    jamming_employed=countermeasures.rf_jamming_active if countermeasures else False,
                    telemetry_frames=len(interceptor.telemetry_history),
                )
                self.completed_engagements.append(outcome)
                new_outcomes.append(outcome)

                interceptor.active = False
                if kill:
                    target.active = False
            else:
                remaining.append((interceptor, target, bat_id))

        self.active_interceptors = remaining
        return new_outcomes
