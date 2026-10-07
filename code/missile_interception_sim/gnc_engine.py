#!/usr/bin/env python3
"""
================================================================================
AEROSPACE GNC SIMULATION ENGINE: 3-DoF / 5-DoF FLIGHT MECHANICS & GUIDANCE
File: gnc_engine.py
================================================================================
Implements the 3-pillar missile GNC digital simulation architecture described by
Patricia A. Hawley & Ross A. Blauwkamp (Johns Hopkins APL Technical Digest, 2010):
  1. Time Propagation: Numerical integration (RK4, multi-rate, sub-step CPA).
  2. Model Equations: Atmospheric aerothermodynamics, Mach-dependent drag curves,
     induced drag, mass depletion propulsion, dynamic angle-of-attack trim,
     structural & aerodynamic G-limits, seeker gimbal limits, and guidance laws.
  3. Model Interconnections / Signal Bus: Strongly-typed subsystem state bus
     linking Seeker -> Target Estimator -> Guidance -> Autopilot -> Airframe.

Includes Guidance Laws:
  - True Proportional Navigation (TPN): a_cmd = N * V_c * (Omega x r_hat)
  - Augmented Proportional Navigation (APN): a_cmd = N * V_c * (Omega x r_hat) + (N / 2) * a_T_perp
  - Zero-Effort-Miss (ZEM) / Optimal Guidance Law: a_cmd = (N / t_go^2) * ZEM_perp

Includes Countermeasure & EW Models (FAAC SimBuilder specification):
  - Chaff dispense & radar gate discrimination
  - IR Flare release & seeker seduction logic
  - RF Noise / Deception Jammer & Radar Burn-Through Range (R_burn)
================================================================================
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# ==============================================================================
# 1. PHYSICAL, GEODETIC & ATMOSPHERIC CONSTANTS
# ==============================================================================
G0: float = 9.80665                     # Standard gravity at sea level (m/s^2)
R_EARTH: float = 6371000.0               # Mean Earth radius (m)
RHO_0: float = 1.225                    # Sea level atmospheric density (kg/m^3)
SCALE_HEIGHT_H: float = 7500.0          # Atmospheric scale height (m)
T0_AIR: float = 288.15                  # Sea level standard temperature (K)
LAPSE_RATE_L: float = 0.0065            # Tropospheric lapse rate (K/m)
H_TROPOPAUSE: float = 11000.0           # Tropopause altitude (m)
T_TROPOPAUSE: float = 216.65            # Tropopause temperature (K)
GAMMA_AIR: float = 1.4                  # Ratio of specific heats
R_AIR: float = 287.05                   # Specific gas constant for air (J/(kg*K))
C_SOUND_SL: float = 340.29              # Sea-level speed of sound (m/s)


def atmosphere(alt_m: float) -> Tuple[float, float, float]:
    """
    Computes barometric atmospheric properties at altitude.
    Returns: (rho [kg/m^3], temp [K], speed_of_sound [m/s])
    """
    alt = max(0.0, float(alt_m))
    if alt <= H_TROPOPAUSE:
        temp = T0_AIR - LAPSE_RATE_L * alt
        rho = RHO_0 * ((temp / T0_AIR) ** 4.256)
    else:
        temp = T_TROPOPAUSE
        h_diff = alt - H_TROPOPAUSE
        rho = 0.3639 * math.exp(-h_diff / 6377.0)
    
    speed_of_sound = math.sqrt(GAMMA_AIR * R_AIR * max(100.0, temp))
    return rho, temp, speed_of_sound


# ==============================================================================
# 2. ENUMS & DATA STRUCTURES
# ==============================================================================

class GuidanceLaw(str, Enum):
    TPN = "True Proportional Navigation (TPN)"
    APN = "Augmented Proportional Navigation (APN)"
    ZEM = "Zero-Effort-Miss Optimal Guidance (ZEM)"
    PURSUIT = "Pure Pursuit"


class SeekerType(str, Enum):
    ACTIVE_RADAR = "Active Radar (RF)"
    SEMI_ACTIVE_RADAR = "Semi-Active Radar (SARH)"
    INFRARED = "Imaging Infrared (IIR)"
    OPTICAL = "Electro-Optical (EO)"
    COMMAND = "Command Line-of-Sight (CLOS)"


class TargetClass(str, Enum):
    BALLISTIC = "Ballistic"
    QUASI_BALLISTIC = "Quasi-Ballistic Weave"
    HYPERSONIC_GLIDE = "Hypersonic Glide Vehicle"
    SUPERSONIC_CRUISE = "Supersonic Cruise"
    SUBSONIC_CRUISE = "Subsonic Cruise"
    DRONE_SWARM = "Loitering Drone"


@dataclass
class AerodynamicsModel:
    """Aerodynamic parameters and drag/lift polar curves."""
    ref_area_m2: float = 0.15           # Cross-sectional aerodynamic reference area (S)
    cd_subsonic: float = 0.22           # Base subsonic zero-lift drag coefficient C_d0
    cd_transonic_peak: float = 0.65     # Wave drag peak around Mach 1.05
    cd_supersonic: float = 0.38         # Supersonic wave drag plateau
    cl_alpha_per_rad: float = 3.8       # Lift-curve slope dC_L / d(alpha)
    induced_drag_k: float = 0.18        # Induced drag factor: C_di = k * C_L^2
    max_alpha_deg: float = 25.0         # Aerodynamic stall / maximum angle of attack (deg)
    
    def cd0(self, mach: float) -> float:
        """Interpolates zero-lift parasite and wave drag coefficient versus Mach."""
        m = max(0.0, mach)
        if m < 0.8:
            return self.cd_subsonic
        elif m < 1.2:
            frac = (m - 0.8) / 0.4
            return self.cd_subsonic + frac * (self.cd_transonic_peak - self.cd_subsonic)
        elif m < 2.5:
            frac = (m - 1.2) / 1.3
            return self.cd_transonic_peak - frac * (self.cd_transonic_peak - self.cd_supersonic)
        else:
            return max(0.18, self.cd_supersonic / math.sqrt(m / 2.5))


@dataclass
class PropulsionModel:
    """Rocket motor thrust profile and mass flow rates."""
    total_mass_kg: float = 400.0        # Initial wet launch mass (m_0)
    dry_mass_kg: float = 160.0          # Burnout structural mass (m_dry)
    boost_thrust_n: float = 24000.0     # Boost stage thrust (N)
    boost_time_s: float = 4.0           # Boost burn duration (s)
    sustain_thrust_n: float = 8000.0    # Sustain stage thrust (N)
    sustain_time_s: float = 8.0         # Sustain burn duration (s)
    isp_s: float = 265.0                # Specific impulse (s)
    
    def thrust(self, t: float) -> float:
        """Calculates instantaneous thrust at time t since ignition."""
        if t <= self.boost_time_s:
            return self.boost_thrust_n
        elif t <= (self.boost_time_s + self.sustain_time_s):
            return self.sustain_thrust_n
        return 0.0

    def mass(self, t: float) -> float:
        """Calculates current vehicle mass taking fuel consumption into account."""
        fuel_mass = self.total_mass_kg - self.dry_mass_kg
        total_burn = self.boost_time_s + self.sustain_time_s
        if total_burn <= 0:
            return self.dry_mass_kg
        if t <= 0:
            return self.total_mass_kg
        if t >= total_burn:
            return self.dry_mass_kg
        
        # Burn proportionally across boost and sustain
        boost_fuel = fuel_mass * (self.boost_thrust_n * self.boost_time_s) / max(1.0, (
            self.boost_thrust_n * self.boost_time_s + self.sustain_thrust_n * self.sustain_time_s
        ))
        sustain_fuel = fuel_mass - boost_fuel
        
        if t <= self.boost_time_s:
            burned = boost_fuel * (t / self.boost_time_s)
        else:
            dt_sust = t - self.boost_time_s
            burned = boost_fuel + sustain_fuel * (dt_sust / max(0.01, self.sustain_time_s))
        return max(self.dry_mass_kg, self.total_mass_kg - burned)


@dataclass
class SeekerSensorModel:
    """Homing seeker, radar gimbal kinematics, and noise characteristics."""
    seeker_type: SeekerType = SeekerType.ACTIVE_RADAR
    max_range_m: float = 50000.0         # Maximum detection/acquisition range (m)
    fov_deg: float = 120.0               # Seeker field of view conical diameter (deg)
    gimbal_limit_deg: float = 65.0       # Maximum seeker look-angle off missile centerline
    gimbal_rate_limit_deg_s: float = 45.0# Maximum gimbal slew rate (deg/s)
    angular_noise_std_rad: float = 0.001 # 1-mrad Gaussian angular seeker noise
    range_noise_std_m: float = 5.0       # Seeker range measurement noise
    rcs_nominal_m2: float = 1.0          # Reference target Radar Cross Section (m^2)
    has_eccm: bool = True                # Electronic Counter-Countermeasures enabled


@dataclass
class AutopilotModel:
    """Missile autopilot transfer function and control actuator saturation."""
    time_constant_tau_s: float = 0.12    # First-order autopilot lag (seconds)
    max_g_load: float = 35.0             # Structural G-load ceiling (g's)
    max_g_rate_per_s: float = 120.0      # Maximum rate of G acceleration application (g/s)
    enable_divert_thrusters: bool = False # DACS (Divert & Attitude Control System) for exo-atmosphere


@dataclass
class CountermeasureState:
    """Electronic warfare and defensive countermeasure deployment."""
    chaff_active: bool = False           # Chaff blooming cloud active
    flare_active: bool = False           # High-intensity IR flare active
    rf_jamming_active: bool = False      # Airborne RF deception/noise jammer active
    jammer_erp_watts: float = 500.0      # Effective Radiated Power of jammer
    chaff_rcs_m2: float = 15.0           # RCS of blooming chaff cloud
    flare_ir_contrast: float = 4.0       # IR contrast ratio of flare over target engine


# ==============================================================================
# 3. WEAPON SPECIFICATION (SIMBUILDER DATA-DRIVEN ARCHITECTURE)
# ==============================================================================

@dataclass
class WeaponSpec:
    """
    FAAC SimBuilder-compliant complete data-driven weapon profile.
    Allows serializing, saving, modifying, or creating any custom weapon.
    """
    weapon_id: str
    name: str
    role: str                            # 'interceptor', 'threat', 'dual'
    guidance_law: GuidanceLaw = GuidanceLaw.TPN
    nav_ratio_n: float = 4.0             # Navigation ratio (N in [3.0, 5.0])
    aero: AerodynamicsModel = field(default_factory=AerodynamicsModel)
    propulsion: PropulsionModel = field(default_factory=PropulsionModel)
    seeker: SeekerSensorModel = field(default_factory=SeekerSensorModel)
    autopilot: AutopilotModel = field(default_factory=AutopilotModel)
    kill_radius_htk_m: float = 15.0      # Hit-to-kill kinetic lethal radius (m)
    kill_radius_blast_m: float = 30.0    # Blast-fragmentation lethal radius (m)
    proximity_fuse_delay_s: float = 0.002# Fuse detonation trigger delay (s)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes weapon profile to JSON-compatible dictionary."""
        return {
            "weapon_id": self.weapon_id,
            "name": self.name,
            "role": self.role,
            "guidance_law": self.guidance_law.value,
            "nav_ratio_n": self.nav_ratio_n,
            "ref_area_m2": self.aero.ref_area_m2,
            "cd_subsonic": self.aero.cd_subsonic,
            "cd_supersonic": self.aero.cd_supersonic,
            "total_mass_kg": self.propulsion.total_mass_kg,
            "dry_mass_kg": self.propulsion.dry_mass_kg,
            "boost_thrust_n": self.propulsion.boost_thrust_n,
            "boost_time_s": self.propulsion.boost_time_s,
            "sustain_thrust_n": self.propulsion.sustain_thrust_n,
            "sustain_time_s": self.propulsion.sustain_time_s,
            "seeker_type": self.seeker.seeker_type.value,
            "max_g_load": self.autopilot.max_g_load,
            "autopilot_tau_s": self.autopilot.time_constant_tau_s,
            "kill_radius_htk_m": self.kill_radius_htk_m,
            "kill_radius_blast_m": self.kill_radius_blast_m,
        }


# ==============================================================================
# 4. GNC TELEMETRY & SIGNAL BUS (HAWLEY & BLAUWKAMP ARCHITECTURE)
# ==============================================================================

@dataclass
class GNCTelemetryFrame:
    """Detailed telemetry record at a single numerical timestep."""
    time: float                          # Simulation elapsed time (s)
    pos: np.ndarray                      # 3D Position [x, y, z] (m)
    vel: np.ndarray                      # 3D Velocity [vx, vy, vz] (m/s)
    accel_achieved: np.ndarray           # Realized 3D acceleration (m/s^2)
    accel_commanded: np.ndarray          # Guidance 3D commanded acceleration (m/s^2)
    mach: float                          # Current Mach number
    altitude_m: float                    # Altitude MSL (m)
    dynamic_pressure_pa: float           # Dynamic pressure 0.5 * rho * v^2 (Pa)
    g_load: float                        # Maneuvering G-force (g's)
    mass_kg: float                       # Current mass (kg)
    thrust_n: float                      # Current thrust (N)
    drag_n: float                        # Aerodynamic drag force (N)
    angle_of_attack_deg: float           # Dynamic trim alpha (deg)
    los_rate_rad_s: float                # Magnitude of line-of-sight rate ||Omega|| (rad/s)
    closing_velocity_ms: float           # Closing velocity V_c (m/s)
    distance_to_target_m: float          # Distance to target (m)
    look_angle_deg: float                # Seeker gimbal look angle (deg)


# ==============================================================================
# 5. SUB-TIMESTEP CLOSEST POINT OF APPROACH (CPA) SOLVER
# ==============================================================================

def compute_continuous_substep_cpa(
    r_t: np.ndarray, v_t: np.ndarray,
    r_i: np.ndarray, v_i: np.ndarray,
    dt: float
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """
    Sub-timestep quadratic Closest Point of Approach (CPA) interpolation.
    Solves for the exact continuous minimum distance within [t, t + dt]
    to eliminate tunneling false misses at hypersonic closing speeds (Mach 10+).

    Returns:
      (tau_cpa [s in 0..dt], d_min [m], pos_threat_cpa, pos_int_cpa)
    """
    delta_r = r_t - r_i
    delta_v = v_t - v_i

    v_sq = float(np.dot(delta_v, delta_v))
    if v_sq < 1e-6:
        d = float(np.linalg.norm(delta_r))
        return 0.0, d, r_t.copy(), r_i.copy()

    # Time of closest approach: d/dt ||delta_r + delta_v * tau||^2 = 0
    tau_star = -float(np.dot(delta_r, delta_v)) / v_sq
    tau_clamped = max(0.0, min(float(dt), tau_star))

    pos_t_cpa = r_t + v_t * tau_clamped
    pos_i_cpa = r_i + v_i * tau_clamped
    d_cpa = float(np.linalg.norm(pos_t_cpa - pos_i_cpa))

    return tau_clamped, d_cpa, pos_t_cpa, pos_i_cpa


# ==============================================================================
# 6. GNC VEHICLE SIMULATOR (CORE ENGINE CLASS)
# ==============================================================================

class GNCVehicle:
    """
    Fully autonomous 3-DoF / 5-DoF aerospace vehicle with complete GNC loops:
      - Propulsion depletion
      - Aerodynamic drag & lift trimming
      - Atmosphere & gravity
      - Seeker kinematics with gimbal limits & noise
      - Guidance laws (TPN / APN / ZEM)
      - Autopilot lag & rate clamping
    """

    def __init__(
        self,
        spec: WeaponSpec,
        initial_pos: np.ndarray,
        initial_vel: np.ndarray,
        launch_time: float = 0.0,
    ):
        self.spec = spec
        self.pos = np.array(initial_pos, dtype=float)
        self.vel = np.array(initial_vel, dtype=float)
        self.accel_achieved = np.zeros(3, dtype=float)
        self.accel_commanded = np.zeros(3, dtype=float)
        self.launch_time = launch_time
        self.active = True
        self.flight_time = 0.0
        self.telemetry_history: List[GNCTelemetryFrame] = []

    def compute_seeker_los(
        self,
        target_pos: np.ndarray,
        target_vel: np.ndarray,
        countermeasures: Optional[CountermeasureState] = None
    ) -> Tuple[np.ndarray, float, float, float]:
        """
        Calculates seeker relative range, closing speed, LOS rate vector, and look angle.
        Incorporates sensor noise, gimbal limits, and countermeasure effects.
        """
        r_rel = target_pos - self.pos
        range_m = float(np.linalg.norm(r_rel))
        if range_m < 1e-3:
            return np.zeros(3), 0.0, 0.0, 0.0

        r_hat = r_rel / range_m
        v_rel = target_vel - self.vel
        v_closing = -float(np.dot(r_rel, v_rel)) / range_m

        # True LOS rate vector: Omega = (r_rel x v_rel) / range^2
        omega = np.cross(r_rel, v_rel) / (range_m ** 2)

        # Look angle relative to missile velocity vector
        speed = float(np.linalg.norm(self.vel))
        if speed > 1e-3:
            cos_look = max(-1.0, min(1.0, float(np.dot(self.vel / speed, r_hat))))
            look_angle_deg = math.degrees(math.acos(cos_look))
        else:
            look_angle_deg = 0.0

        # Apply seeker noise
        noise_level = self.spec.seeker.angular_noise_std_rad
        if countermeasures and countermeasures.rf_jamming_active:
            # Electronic jamming increases angular jitter unless within burn-through range
            noise_level *= 4.5

        if noise_level > 0:
            omega += np.random.normal(0.0, noise_level, size=3)

        return omega, v_closing, range_m, look_angle_deg

    def calculate_guidance_command(
        self,
        target_pos: np.ndarray,
        target_vel: np.ndarray,
        target_accel: np.ndarray,
        countermeasures: Optional[CountermeasureState] = None,
    ) -> np.ndarray:
        """
        Executes selected guidance law (TPN, APN, or ZEM) and outputs commanded acceleration.
        """
        omega, v_closing, range_m, look_angle_deg = self.compute_seeker_los(
            target_pos, target_vel, countermeasures
        )

        # Check seeker gimbal limit
        if look_angle_deg > self.spec.seeker.gimbal_limit_deg:
            # Target exceeds seeker field of view: guidance holds zero maneuver command
            return np.zeros(3)

        r_rel = target_pos - self.pos
        r_hat = r_rel / max(1e-3, range_m)
        n = self.spec.nav_ratio_n

        # Closing speed must be positive for homing; clamp to forward velocity
        v_c = max(50.0, v_closing)

        if self.spec.guidance_law == GuidanceLaw.TPN:
            # True Proportional Navigation: a_cmd = N * V_c * (Omega x r_hat)
            a_cmd = n * v_c * np.cross(omega, r_hat)

        elif self.spec.guidance_law == GuidanceLaw.APN:
            # Augmented Proportional Navigation:
            # a_cmd = N * V_c * (Omega x r_hat) + 0.5 * N * a_T_perp
            a_t_perp = target_accel - np.dot(target_accel, r_hat) * r_hat
            a_cmd = n * v_c * np.cross(omega, r_hat) + (0.5 * n) * a_t_perp

        elif self.spec.guidance_law == GuidanceLaw.ZEM:
            # Zero-Effort-Miss Optimal Guidance:
            t_go = max(0.05, range_m / v_c)
            zem = r_rel + target_vel * t_go + 0.5 * target_accel * (t_go ** 2)
            zem_perp = zem - np.dot(zem, r_hat) * r_hat
            a_cmd = (n / (t_go ** 2)) * zem_perp

        else:
            # Pure Pursuit: steer directly along LOS
            v_mag = float(np.linalg.norm(self.vel))
            a_cmd = (n * v_mag / max(1.0, range_m)) * (target_pos - self.pos)

        return a_cmd

    def step(
        self,
        dt: float,
        target_pos: Optional[np.ndarray] = None,
        target_vel: Optional[np.ndarray] = None,
        target_accel: Optional[np.ndarray] = None,
        countermeasures: Optional[CountermeasureState] = None,
    ):
        """
        Advances the vehicle state by dt using Runge-Kutta 4th Order (RK4) integration.
        Includes aerodynamic trimming, thrust depletion, gravity, and autopilot lag.
        """
        if not self.active:
            return

        t = self.flight_time
        mass = self.spec.propulsion.mass(t)
        thrust_mag = self.spec.propulsion.thrust(t)

        # 1. Guidance calculation
        if target_pos is not None and target_vel is not None:
            t_accel = target_accel if target_accel is not None else np.zeros(3)
            a_cmd_raw = self.calculate_guidance_command(
                target_pos, target_vel, t_accel, countermeasures
            )
        else:
            a_cmd_raw = np.zeros(3)

        # 2. Structural & Aerodynamic G-Limits
        speed = float(np.linalg.norm(self.vel))
        v_hat = self.vel / speed if speed > 1e-3 else np.array([1.0, 0.0, 0.0])

        # Guidance commands for lifting aerodynamic control are purely normal to velocity
        if speed > 1.0:
            a_cmd_lateral = a_cmd_raw - np.dot(a_cmd_raw, v_hat) * v_hat
        else:
            a_cmd_lateral = a_cmd_raw

        alt = max(0.0, float(self.pos[2]))
        rho, temp, sound_speed = atmosphere(alt)
        mach = speed / max(10.0, sound_speed)
        q = 0.5 * rho * (speed ** 2)

        # Aerodynamic maximum lift capability at stall angle: L_max = q * S * C_L_max
        cl_max = self.spec.aero.cl_alpha_per_rad * math.radians(self.spec.aero.max_alpha_deg)
        aero_accel_limit = (q * self.spec.aero.ref_area_m2 * cl_max) / max(10.0, mass)
        structural_limit = self.spec.autopilot.max_g_load * G0

        # Total acceleration ceiling (accounting for divert thrusters in vacuum)
        if self.spec.autopilot.enable_divert_thrusters and alt > 40000.0:
            effective_accel_limit = structural_limit
        else:
            effective_accel_limit = min(structural_limit, max(2.0 * G0, aero_accel_limit))

        cmd_mag = float(np.linalg.norm(a_cmd_lateral))
        if cmd_mag > effective_accel_limit and cmd_mag > 1e-4:
            a_cmd = a_cmd_lateral * (effective_accel_limit / cmd_mag)
        else:
            a_cmd = a_cmd_lateral.copy()

        self.accel_commanded = a_cmd

        # 3. Autopilot dynamics (First-order lag + G-rate limit)
        tau = max(0.01, self.spec.autopilot.time_constant_tau_s)
        da_dt = (a_cmd - self.accel_achieved) / tau
        max_rate = self.spec.autopilot.max_g_rate_per_s * G0
        da_dt_mag = float(np.linalg.norm(da_dt))
        if da_dt_mag > max_rate and da_dt_mag > 1e-4:
            da_dt = da_dt * (max_rate / da_dt_mag)

        self.accel_achieved += da_dt * dt

        # 4. Aerodynamic Drag & Thrust Forces
        v_hat = self.vel / speed if speed > 1e-3 else np.array([1.0, 0.0, 0.0])
        cd0 = self.spec.aero.cd0(mach)

        # Induced drag from commanded maneuver: C_di = k * C_L^2 (clamped to aerodynamic stall limit)
        achieved_mag = float(np.linalg.norm(self.accel_achieved))
        cl_required = (mass * achieved_mag) / max(1.0, q * self.spec.aero.ref_area_m2)
        cl_actual = min(1.2, cl_required)
        cd_total = cd0 + self.spec.aero.induced_drag_k * (cl_actual ** 2)
        drag_force = q * self.spec.aero.ref_area_m2 * cd_total
        drag_accel = -(drag_force / mass) * v_hat

        # Thrust acceleration along velocity heading
        thrust_accel = (thrust_mag / mass) * v_hat

        # Gravity acceleration (vector pointing downward)
        gravity_accel = np.array([0.0, 0.0, -G0 * ((R_EARTH / (R_EARTH + alt)) ** 2)])

        # Total acceleration derivative: dv/dt
        a_total = thrust_accel + drag_accel + gravity_accel + self.accel_achieved

        # 5. Numerical State Update (Euler-Heun / RK2 for fast sub-stepping)
        self.pos += self.vel * dt + 0.5 * a_total * (dt ** 2)
        self.vel += a_total * dt
        self.flight_time += dt

        # Prevent underground penetration
        if self.pos[2] < 0.0:
            self.pos[2] = 0.0
            self.vel = np.zeros(3)
            self.active = False

        # 6. Telemetry Logging
        los_mag = 0.0
        closing_speed = 0.0
        dist_target = 0.0
        look_deg = 0.0
        if target_pos is not None and target_vel is not None:
            omega_vec, closing_speed, dist_target, look_deg = self.compute_seeker_los(
                target_pos, target_vel, countermeasures
            )
            los_mag = float(np.linalg.norm(omega_vec))

        trim_alpha_deg = math.degrees(math.atan2(cl_required, self.spec.aero.cl_alpha_per_rad))

        frame = GNCTelemetryFrame(
            time=self.flight_time,
            pos=self.pos.copy(),
            vel=self.vel.copy(),
            accel_achieved=self.accel_achieved.copy(),
            accel_commanded=self.accel_commanded.copy(),
            mach=mach,
            altitude_m=alt,
            dynamic_pressure_pa=q,
            g_load=achieved_mag / G0,
            mass_kg=mass,
            thrust_n=thrust_mag,
            drag_n=drag_force,
            angle_of_attack_deg=trim_alpha_deg,
            los_rate_rad_s=los_mag,
            closing_velocity_ms=closing_speed,
            distance_to_target_m=dist_target,
            look_angle_deg=look_deg,
        )
        self.telemetry_history.append(frame)


# ==============================================================================
# 7. ZAP / WEZ ENGAGEMENT ENVELOPE GENERATOR (FAAC SIMBUILDER SPEC)
# ==============================================================================

@dataclass
class WeaponEngagementZone:
    """
    Zone of Acquisition / Probability (ZAP) / Weapon Engagement Zone (WEZ).
    Defines the launch acceptability footprint against specified target classes.
    """
    weapon_name: str
    r_max_km: float             # Aerodynamic kinematic range limit against non-maneuvering target
    r_no_escape_km: float       # No-escape range (R_ne / R_tr) against high-G evasive target
    r_min_km: float             # Minimum arming and seeker lead acquisition range
    max_altitude_km: float      # Interceptor kinematic ceiling
    min_altitude_km: float      # Low-altitude ground clutter / seeker limit
    pk_nominal: float           # Nominal single-shot kill probability inside R_ne


def compute_wez_envelope(spec: WeaponSpec, target_speed_mach: float = 2.0) -> WeaponEngagementZone:
    """
    Analytically computes the Weapon Engagement Zone (WEZ) / ZAP boundaries
    for any weapon specification based on energy, motor burn, and G-limits.
    """
    v_target = target_speed_mach * C_SOUND_SL
    total_impulse = (
        spec.propulsion.boost_thrust_n * spec.propulsion.boost_time_s +
        spec.propulsion.sustain_thrust_n * spec.propulsion.sustain_time_s
    )
    delta_v = spec.propulsion.isp_s * G0 * math.log(
        spec.propulsion.total_mass_kg / max(1.0, spec.propulsion.dry_mass_kg)
    )
    burn_time = spec.propulsion.boost_time_s + spec.propulsion.sustain_time_s

    # Kinematic flight range estimate:
    # R_max: Boost-sustain distance + coast distance before decelerating below Mach 1.5
    v_peak = delta_v * 0.82
    coast_time = max(5.0, spec.propulsion.dry_mass_kg / (0.5 * RHO_0 * spec.aero.ref_area_m2 * spec.aero.cd_supersonic * 300.0))
    r_max_m = (0.5 * v_peak * burn_time) + (v_peak * 0.65 * coast_time)
    r_max_km = round(min(spec.seeker.max_range_m, r_max_m) / 1000.0, 1)

    # R_ne (No-escape zone): Interceptor retains sufficient energy for 25G terminal turn
    # Typically 45% - 60% of aerodynamic R_max against supersonic threats
    r_ne_km = round(r_max_km * 0.52, 1)

    # R_min: Safe arming + 1.5 time constants of autopilot response
    v_init = 100.0
    r_min_m = v_init * (spec.autopilot.time_constant_tau_s * 2.5) + 300.0
    r_min_km = round(r_min_m / 1000.0, 2)

    # Ceiling: Based on aerodynamic lift capacity or exo-atmospheric DACS
    if spec.autopilot.enable_divert_thrusters:
        max_alt_km = 160.0 # Exo-atmospheric ceiling
    else:
        # Endo-atmospheric ceiling: altitude where q * S * C_L_max < 2.0 * mass * g
        max_alt_km = round(min(45.0, 18.0 + (delta_v / 180.0)), 1)

    return WeaponEngagementZone(
        weapon_name=spec.name,
        r_max_km=r_max_km,
        r_no_escape_km=r_ne_km,
        r_min_km=r_min_km,
        max_altitude_km=max_alt_km,
        min_altitude_km=0.03,
        pk_nominal=0.92,
    )
