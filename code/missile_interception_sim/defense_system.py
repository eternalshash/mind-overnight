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
