#!/usr/bin/env python3
"""
================================================================================
INTEGRATED AIR AND MISSILE DEFENSE (IAMD) SIMULATION FRAMEWORK
File: defense_system.py

Core Components:
1. 3D True Proportional Navigation (TPN) Guidance:
   a_cmd = N * ||v_rel|| * (Omega x r_hat_rel)
   - Navigation gain N in [3.5, 4.5]
   - Dynamic structural G-limits (30G for PAC-3/SM-3, 15G for Roadrunner-M)
   - Sensor noise and atmospheric wind vector integration

2. Sub-timestep Closest Point of Approach (CPA) Interpolation:
   Continuous quadratic minimum distance calculation within [t, t + dt]
   to eliminate discrete tunneling / false misses when closing velocity
   exceeds Mach 10+ (Vc > 3,400 m/s).

3. Lethal Kill Radius & Detonation Logic:
   - Kinetic Hit-to-Kill (15 m)
   - Blast Fragmentation (30 m)
   - CIWS Burst (5 m)

4. Multi-Tier Layered IAMD Fire Control Doctrine:
   - Tier 1: Exo-atmospheric / High Ballistic (THAAD / SM-3 Block IIA) [alt > 40 km]
   - Tier 2: Mid-altitude / Endo-atmospheric Ballistic & Hypersonic (PAC-3 MSE / S-400) [alt 5-35 km]
   - Tier 3: Low/Medium Altitude Cruise & Drones (Roadrunner-M / Tamir / NASAMS) [alt 0.1-10 km]
   - Tier 4: Close-in Terminal Point Defense (Phalanx 20mm LPWS / Gepard / Skynex) [range < 3.5 km]

5. Operational Firing Doctrines:
   - Shoot-Look-Shoot (SLS) with Battle Damage Assessment (BDA) & automated handoff
   - Salvo of 2 (staggered dual-launch for high-consequence hypersonic/ballistic threats)
   - Automatic Engagement vs. Manual Fire Authorization

6. Monte Carlo Batch Runner:
   - run_monte_carlo(scenario, num_runs=100) with randomized headings, winds,
     seeker errors, and statistical aggregation of Pk, miss distances, and flight times.
================================================================================
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Physical Constants
G0 = 9.80665              # Standard gravitational acceleration (m/s^2)
SPEED_OF_SOUND_SL = 340.29 # Sea-level speed of sound (m/s)


# ==============================================================================
# 1. ENUMS & DATA STRUCTURES
# ==============================================================================

class ThreatType(Enum):
    """Classification of airborne and ballistic threats."""
    BALLISTIC_HIGH = "Ballistic (Exo-atmospheric)"
    ISKANDER_QUASI_BALLISTIC = "9K720 Iskander-M (Quasi-Ballistic)"
    KINZHAL_HYPERSONIC = "Kh-47M2 Kinzhal (Hypersonic Aero-Ballistic)"
    CRUISE_MISSILE = "Subsonic/Supersonic Cruise Missile"
    SHAHED_DRONE = "Shahed-136 / Geran-2 (One-Way Attack UAV)"


class DefenseTier(Enum):
    """Layered defense tiers in modern IAMD architecture."""
    TIER_1_EXO = 1        # THAAD / SM-3 Block IIA
    TIER_2_ENDO = 2       # Patriot PAC-3 MSE / S-400
    TIER_3_SHORAD = 3     # Roadrunner-M / Iron Dome Tamir / NASAMS
    TIER_4_CIWS = 4       # Phalanx 20mm LPWS / Gepard / Skynex


class FiringDoctrine(Enum):
    """Fire control operational engagement doctrine."""
    SHOOT_LOOK_SHOOT = "Shoot-Look-Shoot"
    SALVO_OF_2 = "Salvo of 2"


class FireAuthorizationMode(Enum):
    """Authorization mode for weapon release."""
    AUTOMATIC = "Automatic (Weapons Free)"
    MANUAL = "Manual (Weapons Tight / Operator Auth)"


class InterceptorType(Enum):
    """Specific interceptor weapon systems."""
    SM3_BLOCK_IIA = "SM-3 Block IIA / THAAD"
    PAC3_MSE = "Patriot PAC-3 MSE"
    ROADRUNNER_M = "Anduril Roadrunner-M"
    TAMIR = "Iron Dome Tamir / NASAMS"
    PHALANX_CIWS = "Phalanx 20mm LPWS / Skynex"


class EngagementStatus(Enum):
    """Lifecycle status of a threat engagement."""
    DETECTED = "Detected"
    ASSIGNED = "Assigned"
    AWAITING_AUTH = "Awaiting Fire Authorization"
    IN_FLIGHT = "Interceptor In Flight"
    INTERCEPTED = "Intercepted (Lethal Kill)"
    MISSED = "Missed (Survivable Leaker)"
    HANDED_OFF = "Handed Off to Lower Tier"
    TARGET_IMPACT = "Target Impacted Asset"


@dataclass
class InterceptorConfig:
    """Aerodynamic, guidance, and lethal specifications for an interceptor system."""
    interceptor_type: InterceptorType
    tier: DefenseTier
    name: str
    nominal_speed: float         # Target sprint speed (m/s)
    g_limit: float               # Maximum lateral structural acceleration limit (Gs)
    n_nav: float                 # TPN navigation constant (3.5 - 4.5)
    kill_radius: float           # Proximity lethal detonation radius (meters)
    max_range: float             # Maximum effective engagement range (meters)
    min_altitude: float          # Minimum operational engagement altitude (meters)
    max_altitude: float          # Maximum operational engagement altitude (meters)
    salvo_interval: float = 1.2  # Time separation between salvo rounds (seconds)
    description: str = ""

    @property
    def a_max(self) -> float:
        """Maximum lateral acceleration in m/s^2."""
        return self.g_limit * G0


# Standard Interceptor Catalog
DEFAULT_INTERCEPTOR_CONFIGS: Dict[InterceptorType, InterceptorConfig] = {
    InterceptorType.SM3_BLOCK_IIA: InterceptorConfig(
        interceptor_type=InterceptorType.SM3_BLOCK_IIA,
        tier=DefenseTier.TIER_1_EXO,
        name="SM-3 Block IIA / THAAD",
        nominal_speed=2800.0,       # ~Mach 8.2
        g_limit=30.0,               # 30G exo-atmospheric divert thruster limit
        n_nav=4.2,                  # TPN constant
        kill_radius=15.0,           # Kinetic Hit-to-Kill (15 m)
        max_range=250000.0,         # 250 km
        min_altitude=40000.0,       # 40 km (Exo-atmospheric / upper stratosphere)
        max_altitude=200000.0,      # 200 km
        salvo_interval=1.5,
        description="Tier 1 Exo-atmospheric kinetic kill vehicle against high ballistic threats."
    ),
    InterceptorType.PAC3_MSE: InterceptorConfig(
        interceptor_type=InterceptorType.PAC3_MSE,
        tier=DefenseTier.TIER_2_ENDO,
        name="Patriot PAC-3 MSE",
        nominal_speed=1870.0,       # ~Mach 5.5
        g_limit=30.0,               # 30G agile attitude-control thrusters (ACM)
        n_nav=4.0,                  # TPN constant
        kill_radius=15.0,           # Kinetic Hit-to-Kill with lethality enhancer
        max_range=120000.0,         # 120 km
        min_altitude=5000.0,        # 5 km
        max_altitude=38000.0,       # 38 km
        salvo_interval=1.2,
        description="Tier 2 Endo-atmospheric missile against aero-ballistic and hypersonic threats."
    ),
    InterceptorType.ROADRUNNER_M: InterceptorConfig(
        interceptor_type=InterceptorType.ROADRUNNER_M,
        tier=DefenseTier.TIER_3_SHORAD,
        name="Anduril Roadrunner-M",
        nominal_speed=300.0,        # High-subsonic sprint (~Mach 0.9)
        g_limit=15.0,               # 15G structural limit for modular twin-turbojet UAV
        n_nav=3.8,                  # TPN constant
        kill_radius=30.0,           # Blast fragmentation (30 m)
        max_range=35000.0,          # 35 km
        min_altitude=50.0,          # 50 m
        max_altitude=10000.0,       # 10 km
        salvo_interval=1.0,
        description="Tier 3 Modular VTOL high-acceleration turbojet interceptor for drones & cruise missiles."
    ),
    InterceptorType.TAMIR: InterceptorConfig(
        interceptor_type=InterceptorType.TAMIR,
        tier=DefenseTier.TIER_3_SHORAD,
        name="Iron Dome Tamir / NASAMS",
        nominal_speed=750.0,        # ~Mach 2.2
        g_limit=25.0,               # 25G agile aerodynamic fins
        n_nav=4.0,                  # TPN constant
        kill_radius=30.0,           # Blast fragmentation (30 m)
        max_range=40000.0,          # 40 km
        min_altitude=80.0,          # 80 m
        max_altitude=12000.0,       # 12 km
        salvo_interval=1.0,
        description="Tier 3 Rocket interceptor with active proximity laser fuze."
    ),
    InterceptorType.PHALANX_CIWS: InterceptorConfig(
        interceptor_type=InterceptorType.PHALANX_CIWS,
        tier=DefenseTier.TIER_4_CIWS,
        name="Phalanx 20mm LPWS / Skynex",
        nominal_speed=1150.0,       # Muzzle velocity of high-velocity projectile stream
        g_limit=40.0,               # High-speed lead angle pursuit / burst coverage
        n_nav=3.5,                  # Lead navigation gain
        kill_radius=5.0,            # Dense tungsten fragment cloud / direct kinetic burst (5 m)
        max_range=3500.0,           # 3.5 km
        min_altitude=10.0,          # 10 m
        max_altitude=2500.0,        # 2.5 km
        salvo_interval=0.5,
        description="Tier 4 Close-in weapon system for terminal point defense against leakers."
    ),
}


# ==============================================================================
# 2. GUIDANCE & CLOSEST POINT OF APPROACH (CPA) ENGINE
# ==============================================================================

def compute_substep_cpa(
    r_target: np.ndarray,
    v_target: np.ndarray,
    r_int: np.ndarray,
    v_int: np.ndarray,
    dt: float,
    a_target: Optional[np.ndarray] = None,
    a_int: Optional[np.ndarray] = None,
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """
    Computes continuous-time Closest Point of Approach (CPA) within the interval [0, dt].

    Eliminates discrete tunneling / false misses when closing velocity exceeds Mach 10+
    (e.g., closing speeds > 3,400 m/s moving over 170 meters per 0.05s timestep).

    Physics:
    r_rel(tau) = r0 + v0*tau + 0.5*a0*tau^2
    Continuous squared separation distance:
    D^2(tau) = ||r_rel(tau)||^2

    For linear velocity approximation:
    tau* = - (r0 . v0) / (||v0||^2 + eps), clamped to [0, dt].
    With acceleration refinement, solves derivative roots over [0, dt].

    Returns:
        tau_cpa: Sub-timestep offset in [0, dt] at minimum approach.
        d_cpa: Minimum separation distance (meters) at CPA.
        pos_target_cpa: 3D position of target at CPA.
        pos_int_cpa: 3D position of interceptor at CPA.
    """
    r0 = r_target - r_int
    v0 = v_target - v_int
    v_sq = float(np.dot(v0, v0))

    if v_sq < 1e-10:
        d0 = float(np.linalg.norm(r0))
        return 0.0, d0, r_target.copy(), r_int.copy()

    # Linear unconstrained minimum of quadratic D^2(tau)
    tau_lin = -float(np.dot(r0, v0)) / v_sq
    tau_clamped = float(np.clip(tau_lin, 0.0, dt))

    a0 = (a_target - a_int) if (a_target is not None and a_int is not None) else np.zeros(3)
    a_sq = float(np.dot(a0, a0))

    best_tau = tau_clamped

    if a_sq > 1e-4:
        # Full cubic derivative: d/dtau ||r0 + v0*tau + 0.5*a0*tau^2||^2 = 0
        c3 = a_sq
        c2 = 3.0 * float(np.dot(v0, a0))
        c1 = 2.0 * v_sq + 2.0 * float(np.dot(r0, a0))
        c0 = 2.0 * float(np.dot(r0, v0))

        candidates = [0.0, dt, tau_clamped]
        try:
            poly_roots = np.roots([c3, c2, c1, c0])
            for r in poly_roots:
                if np.isreal(r) and 0.0 <= r.real <= dt:
                    candidates.append(float(r.real))
        except Exception:
            pass

        min_d_sq = float("inf")
        for tau_cand in candidates:
            r_tau = r0 + v0 * tau_cand + 0.5 * a0 * (tau_cand ** 2)
            d_sq = float(np.dot(r_tau, r_tau))
            if d_sq < min_d_sq:
                min_d_sq = d_sq
                best_tau = tau_cand
    else:
        best_tau = tau_clamped

    # Compute positions at best_tau
    p_t_cpa = r_target + v_target * best_tau + 0.5 * (a_target if a_target is not None else np.zeros(3)) * (best_tau ** 2)
    p_i_cpa = r_int + v_int * best_tau + 0.5 * (a_int if a_int is not None else np.zeros(3)) * (best_tau ** 2)
    d_cpa = float(np.linalg.norm(p_t_cpa - p_i_cpa))

    return best_tau, d_cpa, p_t_cpa, p_i_cpa


def calculate_tpn_acceleration(
    r_target: np.ndarray,
    v_target: np.ndarray,
    r_int: np.ndarray,
    v_int: np.ndarray,
    n_nav: float = 4.0,
    g_limit: float = 30.0,
    seeker_noise_std: float = 0.0,
    wind_vector: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, float]:
    """
    Computes commanded lateral acceleration via 3D True Proportional Navigation (TPN).

    Equation:
    a_cmd = N * ||v_rel|| * (Omega x r_hat_rel)

    Where:
    r_rel = r_target - r_int
    v_rel = v_target - v_int
    r_hat_rel = r_rel / ||r_rel||
    Omega = (r_rel x v_rel) / ||r_rel||^2
    subject to structural lateral G-limit: ||a_cmd|| <= g_limit * g0

    Parameters:
        r_target, v_target: Target state vectors (m, m/s).
        r_int, v_int: Interceptor state vectors (m, m/s).
        n_nav: Navigation gain N in [3.5, 4.5].
        g_limit: Structural acceleration limit in Gs.
        seeker_noise_std: Angular rate measurement error (rad/s) added to Omega.
        wind_vector: Optional ambient atmospheric wind velocity vector (m/s).

    Returns:
        a_cmd: Saturated 3D commanded acceleration vector (m/s^2).
        a_mag: Magnitude of commanded acceleration before saturation (m/s^2).
    """
    v_rel = (v_target - v_int)
    if wind_vector is not None:
        # Wind affects relative aerodynamic sensing
        v_rel = v_rel + wind_vector * 0.05

    r_rel = r_target - r_int
    r_mag = float(np.linalg.norm(r_rel))
    if r_mag < 1.0:
        return np.zeros(3), 0.0

    r_hat = r_rel / r_mag
    v_rel_mag = float(np.linalg.norm(v_rel))

    # Line-of-sight angular rate vector: Omega = (r_rel x v_rel) / ||r_rel||^2
    omega = np.cross(r_rel, v_rel) / (r_mag * r_mag)

    if seeker_noise_std > 0.0:
        noise = np.random.normal(0.0, seeker_noise_std, size=3)
        # Project noise orthogonal to LOS
        noise_perp = noise - np.dot(noise, r_hat) * r_hat
        omega = omega + noise_perp

    # 3D True Proportional Navigation Law: a_cmd = N * ||v_rel|| * (Omega x r_hat)
    a_cmd_raw = n_nav * v_rel_mag * np.cross(omega, r_hat)
    a_mag = float(np.linalg.norm(a_cmd_raw))

    # Apply dynamic structural G-limits
    a_max = g_limit * G0
    if a_mag > a_max and a_mag > 1e-6:
        a_cmd = a_cmd_raw * (a_max / a_mag)
    else:
        a_cmd = a_cmd_raw

    return a_cmd, a_mag


def check_lethal_detonation(d_cpa: float, kill_radius: float) -> bool:
    """
    Evaluates whether Closest Point of Approach achieves lethal interception.
    - Hit-to-kill: d_cpa <= 15.0 m
    - Blast fragmentation: d_cpa <= 30.0 m
    - CIWS burst: d_cpa <= 5.0 m
    """
    return d_cpa <= kill_radius


# ==============================================================================
# 3. THREAT REPRESENTATION & KINEMATICS
# ==============================================================================

class Threat:
    """
    Represents an inbound airborne or ballistic threat trajectory.
    Supports high ballistic arcs, quasi-ballistic weaving, hypersonic dives,
    cruise waypoint paths, and low-altitude one-way drone flight.
    """

    def __init__(
        self,
        threat_id: int,
        threat_type: ThreatType,
        name: str,
        launch_pos: np.ndarray,
        target_asset_pos: np.ndarray,
        cruise_speed: float,
        cruise_altitude: float = 0.0,
        weave_amp_g: float = 0.0,
        weave_freq_rad: float = 0.0,
        launch_time: float = 0.0,
    ):
        self.threat_id = threat_id
        self.threat_type = threat_type
        self.name = name
        self.launch_pos = np.array(launch_pos, dtype=np.float64)
        self.target_asset_pos = np.array(target_asset_pos, dtype=np.float64)
        self.cruise_speed = cruise_speed
        self.cruise_altitude = cruise_altitude
        self.weave_amp_g = weave_amp_g
        self.weave_freq_rad = weave_freq_rad
        self.launch_time = launch_time

        # Kinematic state
        self.pos = self.launch_pos.copy()
        self.vel = np.zeros(3, dtype=np.float64)
        self.acc = np.zeros(3, dtype=np.float64)
        self.is_alive = True
        self.is_intercepted = False
        self.interception_time: Optional[float] = None
        self.intercept_pos: Optional[np.ndarray] = None
        self.min_cpa_observed = float("inf")
        self.assigned_battery_id: Optional[str] = None
        self.assigned_tier: Optional[DefenseTier] = None

        self._init_velocity()

    def _init_velocity(self):
        """Initializes 3D velocity vector based on threat type and trajectory geometry."""
        dx = self.target_asset_pos[0] - self.launch_pos[0]
        dy = self.target_asset_pos[1] - self.launch_pos[1]
        dist_xy = max(math.hypot(dx, dy), 1.0)
        dir_x = dx / dist_xy
        dir_y = dy / dist_xy

        if self.threat_type == ThreatType.BALLISTIC_HIGH:
            # Exo-atmospheric ballistic: parabolic trajectory with high apogee
            apogee = max(self.cruise_altitude, 60000.0)
            vz0 = math.sqrt(2.0 * G0 * apogee)
            t_flight = 2.0 * vz0 / G0
            v_xy = dist_xy / max(t_flight, 1.0)
            self.vel = np.array([v_xy * dir_x, v_xy * dir_y, vz0], dtype=np.float64)

        elif self.threat_type == ThreatType.ISKANDER_QUASI_BALLISTIC:
            # Quasi-ballistic: Mach 6-7, depressed aero-ballistic arc with terminal dive
            vz0 = min(850.0, math.sqrt(2.0 * G0 * min(self.cruise_altitude, 32000.0)))
            v_rem_sq = max(self.cruise_speed**2 - vz0**2, 100.0)
            v_xy = math.sqrt(v_rem_sq)
            self.vel = np.array([v_xy * dir_x, v_xy * dir_y, vz0], dtype=np.float64)

        elif self.threat_type == ThreatType.KINZHAL_HYPERSONIC:
            # Hypersonic aero-ballistic: Mach 10+, high-altitude dive
            alt_diff = self.target_asset_pos[2] - self.launch_pos[2]
            pitch = math.atan2(alt_diff, dist_xy)
            # Maintain shallow dive until terminal phase
            pitch = max(pitch, math.radians(-25.0))
            self.vel = np.array([
                self.cruise_speed * math.cos(pitch) * dir_x,
                self.cruise_speed * math.cos(pitch) * dir_y,
                self.cruise_speed * math.sin(pitch)
            ], dtype=np.float64)

        elif self.threat_type == ThreatType.CRUISE_MISSILE:
            # Low altitude terrain follower
            self.pos[2] = self.cruise_altitude
            self.vel = np.array([self.cruise_speed * dir_x, self.cruise_speed * dir_y, 0.0], dtype=np.float64)

        elif self.threat_type == ThreatType.SHAHED_DRONE:
            # Low and slow attack UAV
            self.pos[2] = self.cruise_altitude
            self.vel = np.array([self.cruise_speed * dir_x, self.cruise_speed * dir_y, 0.0], dtype=np.float64)

    def step(self, t: float, dt: float):
        """Advances threat kinematics by time step dt."""
        if not self.is_alive or t < self.launch_time:
            return

        dx = self.target_asset_pos[0] - self.pos[0]
        dy = self.target_asset_pos[1] - self.pos[1]
        dist_xy = max(math.hypot(dx, dy), 1.0)
        dir_x = dx / dist_xy
        dir_y = dy / dist_xy

        a_guidance = np.zeros(3, dtype=np.float64)

        if self.threat_type == ThreatType.BALLISTIC_HIGH:
            a_guidance[2] -= G0

        elif self.threat_type == ThreatType.ISKANDER_QUASI_BALLISTIC:
            # Quasi-ballistic aerodynamic steering toward target
            target_vx = dir_x * self.cruise_speed * 0.9
            target_vy = dir_y * self.cruise_speed * 0.9
            a_guidance[0] += (target_vx - self.vel[0]) * 0.4
            a_guidance[1] += (target_vy - self.vel[1]) * 0.4

            # Vertical trajectory: gravity with re-entry dive inside 35 km
            a_guidance[2] -= G0
            if dist_xy < 35000.0:
                alt_err = self.target_asset_pos[2] - self.pos[2]
                v_z_des = max(-1400.0, min(alt_err * 0.35, 0.0))
                a_guidance[2] += (v_z_des - self.vel[2]) * 0.6

            # Active terminal evasive maneuvers inside 25 km
            if dist_xy < 25000.0 and self.weave_amp_g > 0.0:
                perp_x = -dir_y
                perp_y = dir_x
                w_acc = self.weave_amp_g * G0 * math.sin(self.weave_freq_rad * t)
                a_guidance[0] += w_acc * perp_x
                a_guidance[1] += w_acc * perp_y
                if self.pos[2] < 12000.0:
                    a_guidance[2] += 3.0 * G0 * math.cos(self.weave_freq_rad * t)

        elif self.threat_type == ThreatType.KINZHAL_HYPERSONIC:
            # Hypersonic guidance toward target with terminal weave
            v_xy_cur = math.hypot(self.vel[0], self.vel[1])
            target_vx = dir_x * self.cruise_speed * 0.9
            target_vy = dir_y * self.cruise_speed * 0.9
            a_guidance[0] += (target_vx - self.vel[0]) * 0.5
            a_guidance[1] += (target_vy - self.vel[1]) * 0.5

            # Steep dive toward ground target
            alt_err = self.target_asset_pos[2] - self.pos[2]
            v_z_des = max(-1800.0, min(alt_err * 0.4, 0.0))
            a_guidance[2] += (v_z_des - self.vel[2]) * 0.8

            # Evasive jinking
            if dist_xy < 35000.0 and self.weave_amp_g > 0.0:
                perp_x = -dir_y
                perp_y = dir_x
                w_acc = self.weave_amp_g * G0 * math.sin(self.weave_freq_rad * t)
                a_guidance[0] += w_acc * perp_x
                a_guidance[1] += w_acc * perp_y

        else: # CRUISE_MISSILE or SHAHED_DRONE
            # Waypoint guidance toward asset
            target_vx = dir_x * self.cruise_speed
            target_vy = dir_y * self.cruise_speed
            a_guidance[0] += (target_vx - self.vel[0]) * 0.4
            a_guidance[1] += (target_vy - self.vel[1]) * 0.4

            # Cruise altitude hold
            alt_err = self.cruise_altitude - self.pos[2]
            a_guidance[2] += alt_err * 0.5 - self.vel[2] * 0.3

            # Light jinking for cruise missiles
            if self.weave_amp_g > 0.0 and dist_xy < 15000.0:
                perp_x = -dir_y
                perp_y = dir_x
                a_guidance[0] += self.weave_amp_g * G0 * math.sin(self.weave_freq_rad * t) * perp_x
                a_guidance[1] += self.weave_amp_g * G0 * math.sin(self.weave_freq_rad * t) * perp_y

        self.acc = a_guidance
        self.vel += self.acc * dt
        self.pos += self.vel * dt

        # Ground impact check
        if self.pos[2] <= 0.0:
            self.pos[2] = 0.0
            self.is_alive = False


# Factory helper to construct realistic threat raid scenarios
def create_threat(
    threat_type: ThreatType,
    threat_id: int,
    launch_x: float,
    launch_y: float,
    launch_z: float,
    target_pos: np.ndarray,
    launch_time: float = 0.0,
    heading_noise_deg: float = 0.0,
    speed_factor: float = 1.0,
) -> Threat:
    """Instantiates a threat with realistic real-world tactical performance parameters."""
    l_pos = np.array([launch_x, launch_y, launch_z], dtype=np.float64)

    # Apply optional launch heading perturbation
    if abs(heading_noise_deg) > 1e-4:
        angle_rad = math.radians(heading_noise_deg)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        dx = l_pos[0] - target_pos[0]
        dy = l_pos[1] - target_pos[1]
        l_pos[0] = target_pos[0] + dx * cos_a - dy * sin_a
        l_pos[1] = target_pos[1] + dx * sin_a + dy * cos_a

    if threat_type == ThreatType.ISKANDER_QUASI_BALLISTIC:
        return Threat(
            threat_id=threat_id,
            threat_type=threat_type,
            name=f"Iskander-M #{threat_id}",
            launch_pos=l_pos,
            target_asset_pos=target_pos,
            cruise_speed=2100.0 * speed_factor,   # ~Mach 6.2 (2,100 m/s)
            cruise_altitude=45000.0,             # 45 km apogee ceiling
            weave_amp_g=12.0,                    # 12G terminal weave maneuvers
            weave_freq_rad=1.8,                  # Weave oscillation frequency
            launch_time=launch_time,
        )

    elif threat_type == ThreatType.KINZHAL_HYPERSONIC:
        return Threat(
            threat_id=threat_id,
            threat_type=threat_type,
            name=f"Kinzhal Hypersonic #{threat_id}",
            launch_pos=l_pos,
            target_asset_pos=target_pos,
            cruise_speed=3400.0 * speed_factor,   # ~Mach 10.0 (3,400 m/s)
            cruise_altitude=32000.0,             # High-altitude aeroballistic entry
            weave_amp_g=8.0,                     # Hypersonic pull-ups and lateral bank
            weave_freq_rad=1.2,
            launch_time=launch_time,
        )

    elif threat_type == ThreatType.SHAHED_DRONE:
        return Threat(
            threat_id=threat_id,
            threat_type=threat_type,
            name=f"Shahed-136 Drone #{threat_id}",
            launch_pos=l_pos,
            target_asset_pos=target_pos,
            cruise_speed=48.0 * speed_factor,     # ~173 km/h (48 m/s)
            cruise_altitude=150.0,               # Low altitude terrain hugging
            weave_amp_g=0.5,                     # Gentle waypoint wandering
            weave_freq_rad=0.4,
            launch_time=launch_time,
        )

    elif threat_type == ThreatType.CRUISE_MISSILE:
        return Threat(
            threat_id=threat_id,
            threat_type=threat_type,
            name=f"Cruise Missile #{threat_id}",
            launch_pos=l_pos,
            target_asset_pos=target_pos,
            cruise_speed=260.0 * speed_factor,    # ~Mach 0.76 (260 m/s)
            cruise_altitude=80.0,                # 80 m radar-evading cruise
            weave_amp_g=2.5,
            weave_freq_rad=0.8,
            launch_time=launch_time,
        )

    else: # BALLISTIC_HIGH
        return Threat(
            threat_id=threat_id,
            threat_type=threat_type,
            name=f"Ballistic IRBM #{threat_id}",
            launch_pos=l_pos,
            target_asset_pos=target_pos,
            cruise_speed=3100.0 * speed_factor,   # ~Mach 9.1
            cruise_altitude=75000.0,             # 75 km exo-atmospheric arc
            weave_amp_g=0.0,
            weave_freq_rad=0.0,
            launch_time=launch_time,
        )


# ==============================================================================
# 4. INTERCEPTOR MODEL & FLYOUT DYNAMICS
# ==============================================================================

class Interceptor:
    """
    Simulates a guided interceptor missile executing closed-loop 3D True Proportional
    Navigation (TPN) with sub-timestep continuous Closest Point of Approach (CPA).
    """

    def __init__(
        self,
        interceptor_id: int,
        config: InterceptorConfig,
        launch_site: np.ndarray,
        target: Threat,
        launch_time: float,
        seeker_noise_std: float = 0.0,
        wind_vector: Optional[np.ndarray] = None,
    ):
        self.interceptor_id = interceptor_id
        self.config = config
        self.launch_site = np.array(launch_site, dtype=np.float64)
        self.target = target
        self.launch_time = launch_time
        self.seeker_noise_std = seeker_noise_std
        self.wind_vector = wind_vector

        # Interceptor kinematics
        self.pos = self.launch_site.copy()
        self.vel = np.zeros(3, dtype=np.float64)
        self.acc = np.zeros(3, dtype=np.float64)
        self.is_active = True
        self.is_launched = False
        self.has_intercepted = False
        self.has_missed = False
        self.flight_time = 0.0
        self.min_cpa_observed = float("inf")
        self.best_cpa_time: Optional[float] = None
        self.cpa_pos_int: Optional[np.ndarray] = None
        self.cpa_pos_tgt: Optional[np.ndarray] = None
        self.telemetry: List[dict] = []

        if launch_time <= 0.0:
            self.is_launched = True
            self._aim_and_launch()

    def _aim_and_launch(self):
        """Computes initial lead aim vector toward target predicted trajectory."""
        los = self.target.pos - self.pos
        los_dist = max(float(np.linalg.norm(los)), 1.0)
        los_hat = los / los_dist

        # Lead aim compensation for target velocity
        v_t = self.target.vel
        v_speed = self.config.nominal_speed
        
        # Approximate lead angle
        lead_vec = los_hat * v_speed + v_t * 0.4
        lead_speed = float(np.linalg.norm(lead_vec))
        if lead_speed > 1e-4:
            self.vel = (lead_vec / lead_speed) * v_speed
        else:
            self.vel = los_hat * v_speed

    def step(self, t: float, dt: float) -> Optional[Tuple[bool, float, float]]:
        """
        Advances interceptor flight step by dt.
        Returns:
            Tuple (is_kill, d_cpa, t_event) if engagement reaches CPA or end-of-flight,
            None if still in flight.
        """
        if not self.is_active or t < self.launch_time:
            return None

        if not self.is_launched:
            self.is_launched = True
            self._aim_and_launch()

        self.flight_time += dt

        # Evaluate sub-timestep CPA within [t - dt, t]
        tau_cpa, d_cpa, p_tgt_cpa, p_int_cpa = compute_substep_cpa(
            r_target=self.target.pos,
            v_target=self.target.vel,
            r_int=self.pos,
            v_int=self.vel,
            dt=dt,
            a_target=self.target.acc,
            a_int=self.acc,
        )

        r_rel = self.target.pos - self.pos
        dist_now = float(np.linalg.norm(r_rel))
        v_rel = self.target.vel - self.vel
        dot_rv = float(np.dot(r_rel, v_rel))

        # Update observed CPA
        if d_cpa < self.min_cpa_observed:
            self.min_cpa_observed = d_cpa
            self.best_cpa_time = t + tau_cpa
            self.cpa_pos_int = p_int_cpa
            self.cpa_pos_tgt = p_tgt_cpa

        # 1. Proximity Detonation Check
        if check_lethal_detonation(d_cpa, self.config.kill_radius):
            self.is_active = False
            self.has_intercepted = True
            t_kill = t + tau_cpa
            return True, d_cpa, t_kill

        # 2. Geometry check: passed point of closest approach (opening distance)
        # dot_rv > 0 means relative position and relative velocity are opening up (range increasing)
        if dot_rv > 0.0 and dist_now < 4000.0 and self.flight_time > 0.5:
            # Target missed by this interceptor
            self.is_active = False
            self.has_missed = True
            return False, self.min_cpa_observed, (self.best_cpa_time or t)

        # 3. Maximum flight time / range timeout
        max_flight_time = (self.config.max_range * 1.3) / self.config.nominal_speed
        if self.flight_time > max_flight_time:
            self.is_active = False
            self.has_missed = True
            return False, self.min_cpa_observed, t

        # Calculate 3D True Proportional Navigation (TPN) Guidance
        a_cmd, a_mag = calculate_tpn_acceleration(
            r_target=self.target.pos,
            v_target=self.target.vel,
            r_int=self.pos,
            v_int=self.vel,
            n_nav=self.config.n_nav,
            g_limit=self.config.g_limit,
            seeker_noise_std=self.seeker_noise_std,
            wind_vector=self.wind_vector,
        )

        self.acc = a_cmd

        # Apply lateral acceleration to turn velocity vector while maintaining cruise speed
        v_next = self.vel + self.acc * dt
        v_next_mag = float(np.linalg.norm(v_next))
        if v_next_mag > 1e-4:
            self.vel = (v_next / v_next_mag) * self.config.nominal_speed

        self.pos += self.vel * dt

        # Record telemetry sample for analysis
        if len(self.telemetry) < 500:
            self.telemetry.append({
                "t": t,
                "dist": dist_now,
                "a_cmd_g": a_mag / G0,
                "int_alt": self.pos[2],
                "tgt_alt": self.target.pos[2],
            })

        return None


# ==============================================================================
# 5. MULTI-TIER IAMD FIRE CONTROL DOCTRINE & BATTERY MANAGER
# ==============================================================================

@dataclass
class DefenderBattery:
    """Represents a deployed surface-to-air defense battery or CIWS mount."""
    battery_id: str
    name: str
    tier: DefenseTier
    config: InterceptorConfig
    pos: np.ndarray
    magazine_capacity: int = 16
    missiles_remaining: int = 16
    missiles_fired: int = 0

    def can_engage(self, threat: Threat) -> bool:
        """Evaluates whether threat satisfies battery tier kinematic and range constraints."""
        if self.missiles_remaining <= 0:
            return False

        r_vec = threat.pos - self.pos
        range_m = float(np.linalg.norm(r_vec[:2])) # Horizontal range
        alt_m = threat.pos[2]

        # Range check
        if range_m > self.config.max_range:
            return False

        # Altitude check
        if alt_m < self.config.min_altitude or alt_m > self.config.max_altitude:
            # Special case: Tier 2 can engage high diving threats passing down through Tier 2 ceiling
            if self.tier == DefenseTier.TIER_2_ENDO and alt_m <= 42000.0:
                pass
            else:
                return False

        return True

