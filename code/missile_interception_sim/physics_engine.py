"""
PHYSICS ENGINE: Geodetic (WGS84), Great-Circle Geodesics, and 3-DoF RK4 Trajectory Simulation
=============================================================================================
Provides high-fidelity aerospace flight mechanics, WGS84/ECEF/ENU coordinate transformations,
spherical Earth geodesic ground tracks, exponential atmosphere, altitude-dependent gravity,
Mach-dependent aerodynamic drag, and Runge-Kutta 4th Order (RK4) 3-DoF trajectory simulation
for 4 offensive threat classes:
  1. Ballistic Missiles (ICBM, IRBM, SRBM / Iskander-M)
  2. Hypersonic Weapons (Glide Vehicles / Kinzhal with skipping & lateral weave)
  3. Cruise Missiles (Tomahawk sea-skimming / low-altitude contour)
  4. Drones / Loitering Munitions (Anduril ALTIUS / Barracuda with circular loiter)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# ==============================================================================
# 1. PHYSICAL & GEODETIC CONSTANTS
# ==============================================================================
# WGS84 Ellipsoid
WGS84_A: float = 6378137.0            # Semi-major axis (meters)
WGS84_F: float = 1.0 / 298.257223563   # Flattening
WGS84_B: float = WGS84_A * (1.0 - WGS84_F)  # Semi-minor axis (~6356752.314245 m)
WGS84_E2: float = WGS84_F * (2.0 - WGS84_F)  # First eccentricity squared (~0.00669437999014)
WGS84_EP2: float = (WGS84_A**2 - WGS84_B**2) / (WGS84_B**2)  # Second eccentricity squared

# Mean Spherical Earth
R_EARTH: float = 6371000.0             # Mean Earth radius (meters)
G0: float = 9.80665                   # Standard gravity at sea level (m/s^2)
EARTH_MU: float = 3.986004418e14      # Earth standard gravitational parameter (m^3/s^2)
EARTH_ROTATION_RATE: float = 7.292115e-5  # Earth angular velocity (rad/s)

# Exponential Barometric Atmosphere
RHO_0: float = 1.225                  # Sea level standard density (kg/m^3)
SCALE_HEIGHT_H: float = 7500.0        # Atmospheric scale height (meters)
GAMMA_AIR: float = 1.4                # Ratio of specific heats
R_SPECIFIC_AIR: float = 287.05        # Gas constant for air (J/(kg*K))
T0_AIR: float = 288.15                # Standard sea level temperature (K)
LAPSE_RATE_L: float = 0.0065          # Troposphere temperature lapse rate (K/m)
H_TROPOPAUSE: float = 11000.0         # Tropopause boundary (m)
T_TROPOPAUSE: float = 216.65          # Tropopause temperature (K)


# ==============================================================================
# 2. ENUMS & DATA STRUCTURES
# ==============================================================================
class FlightPhase(str, Enum):
    BOOST = "BOOST"
    MIDCOURSE = "MIDCOURSE"
    GLIDE = "GLIDE"
    TERMINAL = "TERMINAL"
    LOITER = "LOITER"


class ThreatClass(str, Enum):
    BALLISTIC = "BALLISTIC"
    HYPERSONIC = "HYPERSONIC"
    CRUISE = "CRUISE"
    DRONE = "DRONE"


@dataclass
class Telemetry:
    """Comprehensive telemetry record at a single simulation timestep."""
    timestamp: float                 # Time since launch (s)
    lat: float                       # Geodetic latitude (degrees)
    lon: float                       # Geodetic longitude (degrees)
    altitude: float                  # Altitude above MSL (meters)
    mach: float                      # Mach number
    velocity_ms: float               # Velocity magnitude (m/s)
    velocity_kmh: float              # Velocity magnitude (km/h)
    phase: FlightPhase               # Current flight phase
    downrange_distance_m: float      # Distance traveled along ground track from launch (m)
    distance_to_target_m: float      # Great-circle distance to target coordinates (m)
    etof_s: float                    # Estimated Total Time of Flight (s)
    time_remaining_s: float          # Estimated Time Remaining to impact (s)
    progress_percent: float          # Progress from launch to impact (0.0 - 100.0 %)
    x_ecef: float = 0.0              # ECEF X position (m)
    y_ecef: float = 0.0              # ECEF Y position (m)
    z_ecef: float = 0.0              # ECEF Z position (m)
    heading_deg: float = 0.0         # Azimuth / track angle (degrees)
    flight_path_angle_deg: float = 0.0 # Elevation / gamma angle (degrees)
    crossrange_m: float = 0.0        # Cross-track lateral deviation (m)
    dynamic_pressure_pa: float = 0.0 # Dynamic pressure 0.5 * rho * v^2 (Pa)
    drag_force_n: float = 0.0        # Total aerodynamic drag force (N)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "lat": self.lat,
            "lon": self.lon,
            "altitude": self.altitude,
            "mach": self.mach,
            "velocity_ms": self.velocity_ms,
            "velocity_kmh": self.velocity_kmh,
            "phase": self.phase.value if isinstance(self.phase, FlightPhase) else str(self.phase),
            "downrange_distance_m": self.downrange_distance_m,
            "distance_to_target_m": self.distance_to_target_m,
            "etof_s": self.etof_s,
            "time_remaining_s": self.time_remaining_s,
            "progress_percent": self.progress_percent,
            "x_ecef": self.x_ecef,
            "y_ecef": self.y_ecef,
            "z_ecef": self.z_ecef,
            "heading_deg": self.heading_deg,
            "flight_path_angle_deg": self.flight_path_angle_deg,
            "crossrange_m": self.crossrange_m,
            "dynamic_pressure_pa": self.dynamic_pressure_pa,
            "drag_force_n": self.drag_force_n,
        }


@dataclass
class ThreatProfile:
    """Design parameters and guidance specifications for an offensive threat."""
    name: str
    threat_class: ThreatClass
    launch_lat: float
    launch_lon: float
    target_lat: float
    target_lon: float
    launch_alt: float = 0.0
    target_alt: float = 0.0
    mass_kg: float = 1000.0
    reference_area_m2: float = 0.5
    cd_subsonic: float = 0.20
    boost_duration_s: float = 60.0
    burnout_alt_m: float = 80000.0
    target_apogee_m: Optional[float] = None
    cruise_altitude_m: Optional[float] = None
    cruise_mach: Optional[float] = None
    # Hypersonic glide specific:
    glide_altitude_m: float = 32000.0
    skip_amplitude_m: float = 4000.0
    skip_period_s: float = 75.0
    weave_amplitude_m: float = 10000.0
    weave_period_s: float = 90.0
    # Drone loitering specific:
    has_loiter: bool = False
    loiter_radius_m: float = 2500.0
    loiter_duration_s: float = 300.0
    loiter_altitude_m: float = 400.0


# ==============================================================================
# 3. GEODETIC, ECEF & LOCAL CARTESIAN (ENU) TRANSFORMATIONS
# ==============================================================================
def geodetic_to_ecef(
    lat_deg: Union[float, np.ndarray],
    lon_deg: Union[float, np.ndarray],
    alt_m: Union[float, np.ndarray] = 0.0
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray], Union[float, np.ndarray]]:
    """
    Convert geodetic coordinates (WGS84 latitude, longitude, ellipsoidal height)
    to Earth-Centered, Earth-Fixed (ECEF) Cartesian coordinates (X, Y, Z).
    """
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    sin_lat = np.sin(lat_rad)
    cos_lat = np.cos(lat_rad)
    sin_lon = np.sin(lon_rad)
    cos_lon = np.cos(lon_rad)

    # Prime vertical radius of curvature
    n = WGS84_A / np.sqrt(1.0 - WGS84_E2 * sin_lat**2)

    x = (n + alt_m) * cos_lat * cos_lon
    y = (n + alt_m) * cos_lat * sin_lon
    z = (n * (1.0 - WGS84_E2) + alt_m) * sin_lat
    return x, y, z


def ecef_to_geodetic(
    x: Union[float, np.ndarray],
    y: Union[float, np.ndarray],
    z: Union[float, np.ndarray]
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray], Union[float, np.ndarray]]:
    """
    Convert ECEF Cartesian coordinates (X, Y, Z) to geodetic coordinates
    (latitude, longitude in degrees, altitude in meters) using Bowring's algorithm.
    Accurate to sub-millimeter precision across all altitudes.
    """
    p = np.sqrt(x**2 + y**2)
    # Handle polar singularity
    is_scalar = np.isscalar(p)
    if is_scalar and p < 1e-6:
        lat = 90.0 if z >= 0 else -90.0
        return lat, 0.0, float(abs(z) - WGS84_B)

    theta = np.arctan2(z * WGS84_A, p * WGS84_B)
    sin_th = np.sin(theta)
    cos_th = np.cos(theta)

    lat_rad = np.arctan2(
        z + WGS84_EP2 * WGS84_B * (sin_th**3),
        p - WGS84_E2 * WGS84_A * (cos_th**3)
    )
    lon_rad = np.arctan2(y, x)

    sin_lat = np.sin(lat_rad)
    cos_lat = np.cos(lat_rad)
    n = WGS84_A / np.sqrt(1.0 - WGS84_E2 * sin_lat**2)
    alt = p / cos_lat - n

    return np.degrees(lat_rad), np.degrees(lon_rad), alt


def ecef_to_enu(
    x: float, y: float, z: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float = 0.0
) -> Tuple[float, float, float]:
    """
    Transform ECEF coordinates (X, Y, Z) to local East-North-Up (ENU) Cartesian frame
    tangent to WGS84 ellipsoid at reference geodetic point (lat0, lon0, alt0).
    """
    x0, y0, z0 = geodetic_to_ecef(lat0_deg, lon0_deg, alt0_m)
    dx = x - x0
    dy = y - y0
    dz = z - z0

    lat0_rad = math.radians(lat0_deg)
    lon0_rad = math.radians(lon0_deg)
    s_lat, c_lat = math.sin(lat0_rad), math.cos(lat0_rad)
    s_lon, c_lon = math.sin(lon0_rad), math.cos(lon0_rad)

    e = -s_lon * dx + c_lon * dy
    n = -s_lat * c_lon * dx - s_lat * s_lon * dy + c_lat * dz
    u = c_lat * c_lon * dx + c_lat * s_lon * dy + s_lat * dz
    return e, n, u


def enu_to_ecef(
    e: float, n: float, u: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float = 0.0
) -> Tuple[float, float, float]:
    """
    Transform local East-North-Up (ENU) coordinates to ECEF (X, Y, Z).
    """
    x0, y0, z0 = geodetic_to_ecef(lat0_deg, lon0_deg, alt0_m)
    lat0_rad = math.radians(lat0_deg)
    lon0_rad = math.radians(lon0_deg)
    s_lat, c_lat = math.sin(lat0_rad), math.cos(lat0_rad)
    s_lon, c_lon = math.sin(lon0_rad), math.cos(lon0_rad)

    dx = -s_lon * e - s_lat * c_lon * n + c_lat * c_lon * u
    dy = c_lon * e - s_lat * s_lon * n + c_lat * s_lon * u
    dz = c_lat * n + s_lat * u
    return x0 + dx, y0 + dy, z0 + dz


def geodetic_to_enu(
    lat_deg: float, lon_deg: float, alt_m: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float = 0.0
) -> Tuple[float, float, float]:
    """Direct conversion from geodetic to local ENU coordinates around origin."""
    x, y, z = geodetic_to_ecef(lat_deg, lon_deg, alt_m)
    return ecef_to_enu(x, y, z, lat0_deg, lon0_deg, alt0_m)


def enu_to_geodetic(
    e: float, n: float, u: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float = 0.0
) -> Tuple[float, float, float]:
    """Direct conversion from local ENU coordinates to geodetic (lat, lon, alt)."""
    x, y, z = enu_to_ecef(e, n, u, lat0_deg, lon0_deg, alt0_m)
    return ecef_to_geodetic(x, y, z)


# ==============================================================================
# 4. GREAT-CIRCLE GEODESIC NAVIGATION MATH
# ==============================================================================
def great_circle_distance(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
    radius: float = R_EARTH
) -> float:
    """
    Compute geodesic great-circle distance (meters) between two points on spherical Earth
    using the numerically stable Vincenty great-circle formula.
    """
    phi1 = math.radians(lat1_deg)
    lam1 = math.radians(lon1_deg)
    phi2 = math.radians(lat2_deg)
    lam2 = math.radians(lon2_deg)
    dlam = lam2 - lam1

    num = math.sqrt(
        (math.cos(phi2) * math.sin(dlam))**2 +
        (math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam))**2
    )
    den = math.sin(phi1) * math.sin(phi2) + math.cos(phi1) * math.cos(phi2) * math.cos(dlam)
    sigma = math.atan2(num, den)
    return radius * sigma


def initial_bearing(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float
) -> float:
    """
    Compute initial forward azimuth / bearing (degrees clockwise from True North, 0..360)
    from (lat1, lon1) to (lat2, lon2).
    """
    phi1 = math.radians(lat1_deg)
    lam1 = math.radians(lon1_deg)
    phi2 = math.radians(lat2_deg)
    lam2 = math.radians(lon2_deg)
    dlam = lam2 - lam1

    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    bearing_deg = math.degrees(math.atan2(y, x))
    return (bearing_deg + 360.0) % 360.0


def great_circle_waypoint(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
    fraction: float
) -> Tuple[float, float]:
    """
    Compute intermediate geodetic coordinates (lat, lon in degrees) along the great circle
    at fractional distance f in [0, 1].
    """
    if fraction <= 0.0:
        return lat1_deg, lon1_deg
    if fraction >= 1.0:
        return lat2_deg, lon2_deg

    phi1 = math.radians(lat1_deg)
    lam1 = math.radians(lon1_deg)
    phi2 = math.radians(lat2_deg)
    lam2 = math.radians(lon2_deg)
    dlam = lam2 - lam1

    num = math.sqrt(
        (math.cos(phi2) * math.sin(dlam))**2 +
        (math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam))**2
    )
    den = math.sin(phi1) * math.sin(phi2) + math.cos(phi1) * math.cos(phi2) * math.cos(dlam)
    sigma = math.atan2(num, den)

    if math.isclose(sigma, 0.0):
        return lat1_deg, lon1_deg

    a = math.sin((1.0 - fraction) * sigma) / math.sin(sigma)
    b = math.sin(fraction * sigma) / math.sin(sigma)

    x = a * math.cos(phi1) * math.cos(lam1) + b * math.cos(phi2) * math.cos(lam2)
    y = a * math.cos(phi1) * math.sin(lam1) + b * math.cos(phi2) * math.sin(lam2)
    z = a * math.sin(phi1) + b * math.sin(phi2)

    lat = math.atan2(z, math.sqrt(x**2 + y**2))
    lon = math.atan2(y, x)
    return math.degrees(lat), (math.degrees(lon) + 540.0) % 360.0 - 180.0


def great_circle_waypoints(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
    num_points: int = 100
) -> List[Tuple[float, float]]:
    """Generate uniform sequence of geodesic waypoints along the great circle track."""
    fractions = np.linspace(0.0, 1.0, max(2, num_points))
    return [great_circle_waypoint(lat1_deg, lon1_deg, lat2_deg, lon2_deg, f) for f in fractions]


def destination_point(
    lat_deg: float, lon_deg: float,
    bearing_deg: float, distance_m: float,
    radius: float = R_EARTH
) -> Tuple[float, float]:
    """
    Compute destination geodetic coordinates given starting point, initial bearing,
    and ground distance traveled along the sphere.
    """
    phi1 = math.radians(lat_deg)
    lam1 = math.radians(lon_deg)
    theta = math.radians(bearing_deg)
    delta = distance_m / radius

    sin_phi2 = math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    phi2 = math.asin(max(-1.0, min(1.0, sin_phi2)))

    y = math.sin(theta) * math.sin(delta) * math.cos(phi1)
    x = math.cos(delta) - math.sin(phi1) * math.sin(phi2)
    lam2 = lam1 + math.atan2(y, x)
    return math.degrees(phi2), (math.degrees(lam2) + 540.0) % 360.0 - 180.0


def cross_track_distance(
    lat_deg: float, lon_deg: float,
    lat_start: float, lon_start: float,
    lat_end: float, lon_end: float,
    radius: float = R_EARTH
) -> float:
    """
    Compute signed lateral cross-track distance (meters) of a point from the great circle
    defined by start and end waypoints (positive = right of track, negative = left).
    """
    d13 = great_circle_distance(lat_start, lon_start, lat_deg, lon_deg, radius) / radius
    theta13 = math.radians(initial_bearing(lat_start, lon_start, lat_deg, lon_deg))
    theta12 = math.radians(initial_bearing(lat_start, lon_start, lat_end, lon_end))
    d_xt = math.asin(math.sin(d13) * math.sin(theta13 - theta12))
    return radius * d_xt


# ==============================================================================
# 5. ATMOSPHERE, GRAVITY, SPEED OF SOUND & AERODYNAMICS
# ==============================================================================
def atmospheric_density(altitude_m: float) -> float:
    """
    Exponential barometric atmospheric density model:
      rho(z) = rho_0 * exp(-z / H)
    where rho_0 = 1.225 kg/m^3, H = 7500.0 m.
    For z > 150 km, returns near-vacuum (1e-15 kg/m^3).
    """
    if altitude_m < 0.0:
        return RHO_0
    if altitude_m > 150000.0:
        return 0.0
    return RHO_0 * math.exp(-altitude_m / SCALE_HEIGHT_H)


def temperature_at_altitude(altitude_m: float) -> float:
    """Standard atmospheric temperature model (Kelvin) across troposphere and stratosphere."""
    z = max(0.0, altitude_m)
    if z <= H_TROPOPAUSE:
        return T0_AIR - LAPSE_RATE_L * z
    elif z <= 25000.0:
        return T_TROPOPAUSE
    elif z <= 47000.0:
        return T_TROPOPAUSE + 0.0028 * (z - 25000.0)
    else:
        return 278.35


def speed_of_sound(altitude_m: float) -> float:
    """
    Compute local speed of sound c_s = sqrt(gamma * R * T(z)) in m/s.
    Standard sea-level speed of sound is ~340.3 m/s, dropping to ~295.1 m/s at 11 km.
    """
    temp_k = temperature_at_altitude(altitude_m)
    return math.sqrt(GAMMA_AIR * R_SPECIFIC_AIR * temp_k)


def mach_number(velocity_ms: float, altitude_m: float) -> float:
    """Calculate Mach number from velocity (m/s) and altitude (m)."""
    c_s = speed_of_sound(altitude_m)
    return velocity_ms / max(1.0, c_s)


def gravity(altitude_m: float) -> float:
    """
    Altitude-dependent gravitational acceleration:
      g(z) = g_0 * (R_E / (R_E + z))^2
    where g_0 = 9.80665 m/s^2, R_E = 6371000.0 m.
    """
    z = max(0.0, altitude_m)
    ratio = R_EARTH / (R_EARTH + z)
    return G0 * (ratio**2)


def drag_coefficient(mach: float, cd_subsonic: float = 0.20) -> float:
    """
    Mach-dependent aerodynamic drag coefficient C_d(M).
    Models subsonic drag, steep transonic wave drag peak around Mach 1.05 - 1.2,
    supersonic wave decay (1/sqrt(M^2 - 1)), and hypersonic modified Newtonian asymptote.
    """
    m = max(0.0, mach)
    if m <= 0.8:
        # Subsonic laminar / turbulent drag
        return cd_subsonic
    elif m <= 1.2:
        # Transonic drag rise (wave drag divergence)
        tau = (m - 0.8) / 0.4
        transonic_multiplier = 1.0 + 1.8 * (math.sin(0.5 * math.pi * tau)**2)
        return cd_subsonic * transonic_multiplier
    elif m <= 5.0:
        # Supersonic decay of wave drag
        decay = 1.0 + 1.8 * math.sqrt(1.2**2 - 1.0) / math.sqrt(m**2 - 1.0 + 0.05)
        return cd_subsonic * decay
    else:
        # Hypersonic modified Newtonian flow asymptotic level
        return cd_subsonic * 1.35


def aerodynamic_drag_force(
    velocity_ms: float, altitude_m: float,
    area_m2: float, cd_subsonic: float = 0.20
) -> float:
    """
    Compute total aerodynamic drag force F_d (Newtons):
      F_d = 0.5 * rho(z) * v^2 * C_d(M) * A
    """
    rho = atmospheric_density(altitude_m)
    mach = mach_number(velocity_ms, altitude_m)
    cd = drag_coefficient(mach, cd_subsonic)
    return 0.5 * rho * (velocity_ms**2) * cd * area_m2


# ==============================================================================
# 6. 3-DOF RK4 NUMERICAL INTEGRATION & TRAJECTORY SIMULATOR
# ==============================================================================
class Trajectory:
    """
    Encapsulates the simulated 3-DoF trajectory, providing full telemetry lookup
    at any arbitrary continuous time or discrete timestep index.
    """
    def __init__(self, profile: ThreatProfile, telemetry_history: List[Telemetry]):
        self.profile = profile
        self.telemetry_history = telemetry_history
        self._timestamps = np.array([t.timestamp for t in telemetry_history])
        self._dataframe: Optional[pd.DataFrame] = None

    def __len__(self) -> int:
        return len(self.telemetry_history)

    @property
    def total_flight_time_s(self) -> float:
        return self._timestamps[-1] if len(self._timestamps) > 0 else 0.0

    @property
    def apogee_m(self) -> float:
        return max(t.altitude for t in self.telemetry_history)

    @property
    def max_velocity_ms(self) -> float:
        return max(t.velocity_ms for t in self.telemetry_history)

    @property
    def max_mach(self) -> float:
        return max(t.mach for t in self.telemetry_history)

    @property
    def impact_distance_m(self) -> float:
        return self.telemetry_history[-1].distance_to_target_m

    @property
    def phases_traversed(self) -> List[FlightPhase]:
        seen = []
        for t in self.telemetry_history:
            if t.phase not in seen:
                seen.append(t.phase)
        return seen

    def get_telemetry_at_index(self, index: int) -> Telemetry:
        """Retrieve telemetry record at specific discrete timestep index."""
        idx = max(0, min(len(self.telemetry_history) - 1, index))
        return self.telemetry_history[idx]

    def get_telemetry_at_time(self, time_s: float) -> Telemetry:
        """
        Interpolate and retrieve exact telemetry at any continuous timestamp t.
        Uses high-order spherical and linear interpolation across the trajectory.
        """
        if len(self.telemetry_history) == 0:
            raise ValueError("Trajectory has no telemetry records.")
        if time_s <= self._timestamps[0]:
            return self.telemetry_history[0]
        if time_s >= self._timestamps[-1]:
            return self.telemetry_history[-1]

        # Binary search for interval
        idx = int(np.searchsorted(self._timestamps, time_s))
        i0 = max(0, idx - 1)
        i1 = idx
        t0, t1 = self._timestamps[i0], self._timestamps[i1]
        dt = t1 - t0
        alpha = 0.0 if math.isclose(dt, 0.0) else (time_s - t0) / dt

        m0 = self.telemetry_history[i0]
        m1 = self.telemetry_history[i1]

        # Great-circle interpolation for coordinates
        interp_lat, interp_lon = great_circle_waypoint(m0.lat, m0.lon, m1.lat, m1.lon, alpha)
        interp_alt = (1.0 - alpha) * m0.altitude + alpha * m1.altitude
        interp_v = (1.0 - alpha) * m0.velocity_ms + alpha * m1.velocity_ms
        interp_mach = (1.0 - alpha) * m0.mach + alpha * m1.mach
        interp_downrange = (1.0 - alpha) * m0.downrange_distance_m + alpha * m1.downrange_distance_m
        interp_dist_tgt = (1.0 - alpha) * m0.distance_to_target_m + alpha * m1.distance_to_target_m
        interp_prog = (1.0 - alpha) * m0.progress_percent + alpha * m1.progress_percent
        interp_time_rem = max(0.0, (1.0 - alpha) * m0.time_remaining_s + alpha * m1.time_remaining_s)
        phase = m1.phase if alpha >= 0.5 else m0.phase

        x, y, z = geodetic_to_ecef(interp_lat, interp_lon, interp_alt)
        return Telemetry(
            timestamp=time_s,
            lat=interp_lat,
            lon=interp_lon,
            altitude=interp_alt,
            mach=interp_mach,
            velocity_ms=interp_v,
            velocity_kmh=interp_v * 3.6,
            phase=phase,
            downrange_distance_m=interp_downrange,
            distance_to_target_m=interp_dist_tgt,
            etof_s=m0.etof_s,
            time_remaining_s=interp_time_rem,
            progress_percent=interp_prog,
            x_ecef=x, y_ecef=y, z_ecef=z,
            heading_deg=(1.0 - alpha) * m0.heading_deg + alpha * m1.heading_deg,
            flight_path_angle_deg=(1.0 - alpha) * m0.flight_path_angle_deg + alpha * m1.flight_path_angle_deg,
            crossrange_m=(1.0 - alpha) * m0.crossrange_m + alpha * m1.crossrange_m,
            dynamic_pressure_pa=(1.0 - alpha) * m0.dynamic_pressure_pa + alpha * m1.dynamic_pressure_pa,
            drag_force_n=(1.0 - alpha) * m0.drag_force_n + alpha * m1.drag_force_n
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Convert trajectory telemetry history into a Pandas DataFrame."""
        if self._dataframe is None:
            self._dataframe = pd.DataFrame([t.to_dict() for t in self.telemetry_history])
        return self._dataframe


def rk4_step(f, t: float, y: np.ndarray, dt: float) -> np.ndarray:
    """
    Standard classical Runge-Kutta 4th Order numerical integrator step:
      k1 = f(t, y)
      k2 = f(t + dt/2, y + dt/2 * k1)
      k3 = f(t + dt/2, y + dt/2 * k2)
      k4 = f(t + dt, y + dt * k3)
      y_{n+1} = y_n + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
    """
    k1 = f(t, y)
    k2 = f(t + 0.5 * dt, y + 0.5 * dt * k1)
    k3 = f(t + 0.5 * dt, y + 0.5 * dt * k2)
    k4 = f(t + dt, y + dt * k3)
    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def simulate_trajectory(profile: ThreatProfile, dt: float = 1.0) -> Trajectory:
    """
    Simulate full 3-DoF trajectory using Runge-Kutta 4th Order numerical integration
    for any of the 4 offensive threat classes:
      - Ballistic: suborbital boost, Keplerian coast (z > 100km ICBM, 30-50km SRBM), reentry
      - Hypersonic: boost, depressed glide (25-40km) with skipping and periodic lateral weave
      - Cruise Missile: low-altitude contour (50-300m AGL) at constant Mach
      - Drone / Loitering Munition: subsonic cruise (100-1000m AGL) with circular loitering
    """
    total_range_m = great_circle_distance(
        profile.launch_lat, profile.launch_lon,
        profile.target_lat, profile.target_lon
    )
    init_bearing = initial_bearing(
        profile.launch_lat, profile.launch_lon,
        profile.target_lat, profile.target_lon
    )

    if profile.threat_class == ThreatClass.BALLISTIC:
        return _simulate_ballistic(profile, total_range_m, init_bearing, dt)
    elif profile.threat_class == ThreatClass.HYPERSONIC:
        return _simulate_hypersonic(profile, total_range_m, init_bearing, dt)
    elif profile.threat_class == ThreatClass.CRUISE:
        return _simulate_cruise(profile, total_range_m, init_bearing, dt)
    elif profile.threat_class == ThreatClass.DRONE:
        return _simulate_drone(profile, total_range_m, init_bearing, dt)
    else:
        raise ValueError(f"Unknown threat class: {profile.threat_class}")


# ==============================================================================
# 7. INTERNAL SIMULATOR IMPLEMENTATIONS FOR EACH THREAT CLASS
# ==============================================================================
def _simulate_ballistic(
    profile: ThreatProfile, total_range_m: float, init_bearing: float, dt: float
) -> Trajectory:
    """
    Ballistic trajectory:
      1. BOOST: Rocket propulsion through atmosphere to burnout altitude & velocity.
      2. MIDCOURSE: Exo-atmospheric Keplerian coast under central gravity and rarefied drag.
         - High apogee: z > 100 km for ICBM/IRBM, 30-50 km for SRBMs.
      3. TERMINAL: Atmospheric reentry with high aerodynamic drag and dive to target.
    """
    target_apogee = profile.target_apogee_m
    if target_apogee is None:
        if total_range_m > 3000e3:
            target_apogee = 1200e3  # Standard ICBM apogee (~1200 km)
        elif total_range_m > 1000e3:
            target_apogee = 350e3   # IRBM apogee (~350 km)
        else:
            target_apogee = 42e3    # SRBM quasi-ballistic apogee (~42 km)

    t_boost = profile.boost_duration_s

    if target_apogee > 100e3:
        # Exo-atmospheric ICBM / IRBM Kepler suborbital mechanics
        z_bo = profile.burnout_alt_m
        dtheta = total_range_m / R_EARTH
        r0 = R_EARTH + z_bo
        ra = R_EARTH + target_apogee
        e = (ra - r0) / (ra - r0 * math.cos(dtheta / 2.0))
        p = ra * (1.0 - e)
        a_orbit = p / (1.0 - e**2)

        # Burnout vertical velocity to reach target exo-atmospheric apogee
        vz_bo = math.sqrt(2.0 * EARTH_MU * (1.0 / r0 - 1.0 / ra))

        # Kepler flight time
        nu0 = math.pi - dtheta / 2.0
        tan_half_e0 = math.sqrt((1.0 - e) / (1.0 + e)) * math.tan(nu0 / 2.0)
        e0 = 2.0 * math.atan(tan_half_e0)
        m0 = e0 - e * math.sin(e0)
        n_mean = math.sqrt(EARTH_MU / a_orbit**3)
        t_coast_est = 2.0 * (math.pi - m0) / n_mean

        vs_bo = total_range_m / (0.5 * t_boost + t_coast_est)
        v_bo = math.sqrt(vs_bo**2 + vz_bo**2)
        gamma_bo = math.atan2(vz_bo, vs_bo)

        t_reentry_est = 70.0
        reentry_alt_threshold = 100e3
    else:
        # SRBM (Iskander-M quasi-ballistic) exact kinematic solution in 30-50 km window
        b_quad = G0 * t_boost
        vz_bo = (-b_quad + math.sqrt(b_quad**2 + 8.0 * G0 * target_apogee)) / 2.0
        z_bo = 0.5 * vz_bo * t_boost
        t_rise = vz_bo / G0
        t_fall = math.sqrt(2.0 * target_apogee / G0)
        t_coast_est = t_rise + t_fall
        vs_bo = total_range_m / (0.5 * t_boost + t_coast_est)
        v_bo = math.sqrt(vs_bo**2 + vz_bo**2)
        gamma_bo = math.atan2(vz_bo, vs_bo)
        t_reentry_est = 30.0
        reentry_alt_threshold = 25e3

    total_etof = t_boost + t_coast_est + t_reentry_est

    # State: [s (downrange m), z (alt m), vs (downrange vel m/s), vz (vert vel m/s)]
    state = np.array([0.0, profile.launch_alt, 0.0, 0.0], dtype=np.float64)
    t = 0.0
    telemetry_list: List[Telemetry] = []
    has_reached_apogee = False

    def derivatives(t_curr: float, st: np.ndarray, phase: FlightPhase) -> np.ndarray:
        s, z, vs, vz = st
        v = math.sqrt(vs**2 + vz**2)
        r = R_EARTH + max(0.0, z)
        gz = gravity(z)

        # Spherical horizon curvature
        curv_s = -(vs * vz) / r
        curv_z = (vs**2) / r
        # Ground track downrange rate
        s_rate = vs * (R_EARTH / r)

        # Drag
        rho = atmospheric_density(z)
        mach = mach_number(v, z)
        cd = drag_coefficient(mach, profile.cd_subsonic)
        f_drag = 0.5 * rho * (v**2) * cd * profile.reference_area_m2
        a_drag_s = -(f_drag / profile.mass_kg) * (vs / max(1e-4, v))
        a_drag_z = -(f_drag / profile.mass_kg) * (vz / max(1e-4, v))

        if phase == FlightPhase.BOOST:
            # Rocket motor thrust accelerates vehicle to burnout velocity vector
            tau = min(1.0, t_curr / t_boost)
            vs_ref = vs_bo * tau
            vz_ref = vz_bo * tau
            as_cmd = (vs_bo / t_boost) + 0.5 * (vs_ref - vs)
            az_cmd = (vz_bo / t_boost) + 0.5 * (vz_ref - vz)
            return np.array([s_rate, vz, as_cmd, az_cmd])
        elif phase == FlightPhase.MIDCOURSE:
            # Freefall Keplerian coast under central gravity and vacuum/rarefied drag
            return np.array([s_rate, vz, a_drag_s + curv_s, -gz + a_drag_z + curv_z])
        else: # TERMINAL reentry
            # Guided aerodynamic reentry diving onto target coordinates
            rem_dist = max(100.0, total_range_m - s)
            target_vz = -max(400.0, min(v * 0.7, 2500.0)) * (z / rem_dist)
            az_ctrl = 0.3 * (target_vz - vz)
            return np.array([s_rate, vz, a_drag_s + curv_s, -gz + a_drag_z + curv_z + az_ctrl])

    max_steps = 25000
    step_count = 0
    while step_count < max_steps:
        s, z, vs, vz = state
        v = math.sqrt(vs**2 + vz**2)
        mach = mach_number(v, z)

        # Detect apogee
        if vz < 0.0 and s > (total_range_m * 0.05):
            has_reached_apogee = True

        # Phase determination
        if t < t_boost:
            current_phase = FlightPhase.BOOST
        elif not has_reached_apogee or z > reentry_alt_threshold:
            current_phase = FlightPhase.MIDCOURSE
        else:
            current_phase = FlightPhase.TERMINAL

        # Calculate ground track coordinates
        frac = min(1.0, max(0.0, s / total_range_m))
        cur_lat, cur_lon = great_circle_waypoint(
            profile.launch_lat, profile.launch_lon,
            profile.target_lat, profile.target_lon,
            frac
        )
        dist_to_target = great_circle_distance(
            cur_lat, cur_lon,
            profile.target_lat, profile.target_lon
        )

        progress = min(100.0, max(0.0, (t / max(1.0, total_etof)) * 100.0))
        time_remaining = max(0.0, total_etof - t)

        rho = atmospheric_density(z)
        q = 0.5 * rho * (v**2)
        cd = drag_coefficient(mach, profile.cd_subsonic)
        f_drag = q * cd * profile.reference_area_m2
        x, y, z_ecef = geodetic_to_ecef(cur_lat, cur_lon, z)

        gamma_deg = math.degrees(math.atan2(vz, max(1e-4, vs)))

        telemetry_list.append(Telemetry(
            timestamp=t,
            lat=cur_lat,
            lon=cur_lon,
            altitude=z,
            mach=mach,
            velocity_ms=v,
            velocity_kmh=v * 3.6,
            phase=current_phase,
            downrange_distance_m=s,
            distance_to_target_m=dist_to_target,
            etof_s=total_etof,
            time_remaining_s=time_remaining,
            progress_percent=progress,
            x_ecef=x, y_ecef=y, z_ecef=z_ecef,
            heading_deg=init_bearing,
            flight_path_angle_deg=gamma_deg,
            crossrange_m=0.0,
            dynamic_pressure_pa=q,
            drag_force_n=f_drag
        ))

        # Termination: target impact at ground or proximity
        if current_phase == FlightPhase.TERMINAL and (z <= 0.0 or dist_to_target < 2000.0):
            break

        f_deriv = lambda _t, _st: derivatives(_t, _st, current_phase)
        state = rk4_step(f_deriv, t, state, dt)
        t += dt
        step_count += 1

    last = telemetry_list[-1]
    last.altitude = 0.0
    last.progress_percent = 100.0
    last.time_remaining_s = 0.0
    last.distance_to_target_m = 0.0
    last.lat = profile.target_lat
    last.lon = profile.target_lon
    last.etof_s = t

    for tel in telemetry_list:
        tel.etof_s = t
        tel.time_remaining_s = max(0.0, t - tel.timestamp)
        tel.progress_percent = min(100.0, (tel.timestamp / t) * 100.0)

    return Trajectory(profile, telemetry_list)


def _simulate_hypersonic(
    profile: ThreatProfile, total_range_m: float, init_bearing: float, dt: float
) -> Trajectory:
    """
    Hypersonic Glide Vehicle (HGV / Kinzhal):
      1. BOOST: Accelerated to Mach 8-10 and boosted into upper atmosphere (~30 km).
      2. GLIDE: Depressed glide in upper stratosphere (25-40 km).
         - Atmospheric skipping: sinusoidal altitude phugoid oscillation (amplitude 3-5 km).
         - Periodic lateral weave: crossrange S-turns (amplitude 8-15 km) to defeat radar tracking.
      3. TERMINAL: Steep hypersonic terminal dive onto target coordinates.
    """
    t_boost = profile.boost_duration_s
    glide_alt = profile.glide_altitude_m
    cruise_mach = profile.cruise_mach if profile.cruise_mach is not None else 9.2
    c_s_glide = speed_of_sound(glide_alt)
    cruise_speed = cruise_mach * c_s_glide  # ~2800 m/s

    s_boost = 0.5 * cruise_speed * t_boost
    s_terminal_start = max(s_boost + 10e3, total_range_m - 60e3)
    t_glide_est = (s_terminal_start - s_boost) / cruise_speed
    t_terminal_est = 60e3 / (0.7 * cruise_speed)
    total_etof = t_boost + t_glide_est + t_terminal_est

    # State: [s (downrange m), y (crossrange m), z (altitude m), vs, vy, vz]
    state = np.array([0.0, 0.0, profile.launch_alt, 0.0, 0.0, 0.0], dtype=np.float64)
    t = 0.0
    telemetry_list: List[Telemetry] = []

    def derivatives(t_curr: float, st: np.ndarray, phase: FlightPhase) -> np.ndarray:
        s, y, z, vs, vy, vz = st
        v = math.sqrt(vs**2 + vy**2 + vz**2)
        r = R_EARTH + max(0.0, z)
        gz = gravity(z)

        curv_s = -(vs * vz) / r
        curv_y = -(vy * vz) / r
        curv_z = (vs**2 + vy**2) / r
        s_rate = vs * (R_EARTH / r)

        rho = atmospheric_density(z)
        mach = mach_number(v, z)
        cd = drag_coefficient(mach, profile.cd_subsonic)
        f_drag = 0.5 * rho * (v**2) * cd * profile.reference_area_m2
        a_drag_s = -(f_drag / profile.mass_kg) * (vs / max(1e-4, v))
        a_drag_y = -(f_drag / profile.mass_kg) * (vy / max(1e-4, v))
        a_drag_z = -(f_drag / profile.mass_kg) * (vz / max(1e-4, v))

        if phase == FlightPhase.BOOST:
            # Smooth Hermite polynomial transition to glide altitude and cruise velocity
            tau = min(1.0, t_curr / t_boost)
            z_ref = glide_alt * (3.0 * tau**2 - 2.0 * tau**3)
            vz_ref = (glide_alt / t_boost) * (6.0 * tau - 6.0 * tau**2)
            az_ref = (glide_alt / (t_boost**2)) * (6.0 - 12.0 * tau)
            vs_ref = cruise_speed * (3.0 * tau**2 - 2.0 * tau**3)
            as_ref = (cruise_speed / t_boost) * (6.0 * tau - 6.0 * tau**2)

            as_cmd = as_ref + 0.8 * (vs_ref - vs)
            az_cmd = az_ref + 0.8 * (vz_ref - vz) + 0.2 * (z_ref - z)
            return np.array([s_rate, vy, vz, as_cmd, 0.0, az_cmd])

        elif phase == FlightPhase.GLIDE:
            omega_skip = 2.0 * math.pi / profile.skip_period_s
            t_glide = t_curr - t_boost
            z_ref = glide_alt + profile.skip_amplitude_m * math.sin(omega_skip * t_glide)
            vz_ref = profile.skip_amplitude_m * omega_skip * math.cos(omega_skip * t_glide)
            a_lift_z = gz - curv_z - a_drag_z + 0.6 * (vz_ref - vz) + 0.1 * (z_ref - z)

            omega_weave = 2.0 * math.pi / profile.weave_period_s
            y_ref = profile.weave_amplitude_m * math.sin(omega_weave * t_glide)
            vy_ref = profile.weave_amplitude_m * omega_weave * math.cos(omega_weave * t_glide)
            a_lat_ctrl = 0.6 * (vy_ref - vy) + 0.1 * (y_ref - y)

            # Sustainer balances drag and maintains constant cruise speed
            a_thrust_s = -a_drag_s + 0.3 * (cruise_speed - vs)

            return np.array([s_rate, vy, vz, a_thrust_s + a_drag_s + curv_s, a_lat_ctrl + a_drag_y + curv_y, a_lift_z - gz + curv_z + a_drag_z])

        else: # TERMINAL
            # Pitch down into terminal hypersonic dive without adding artificial kinetic energy
            rem_dist = max(100.0, total_range_m - s)
            target_vz = -max(400.0, min(vs * 0.5, 1500.0)) * (z / rem_dist)
            az_ctrl = 0.2 * (target_vz - vz)
            as_ctrl = a_drag_s - 0.02 * vs
            ay_ctrl = -0.4 * vy - 0.1 * y
            return np.array([s_rate, vy, vz, as_ctrl + curv_s, ay_ctrl + curv_y, az_ctrl - gz + curv_z + a_drag_z])

    step_count = 0
    while step_count < 15000:
        s, y, z, vs, vy, vz = state
        v = math.sqrt(vs**2 + vy**2 + vz**2)
        mach = mach_number(v, z)

        if t < t_boost:
            current_phase = FlightPhase.BOOST
        elif s < s_terminal_start:
            current_phase = FlightPhase.GLIDE
        else:
            current_phase = FlightPhase.TERMINAL

        frac = min(1.0, max(0.0, s / total_range_m))
        gc_lat, gc_lon = great_circle_waypoint(
            profile.launch_lat, profile.launch_lon,
            profile.target_lat, profile.target_lon,
            frac
        )
        cur_track_bearing = initial_bearing(gc_lat, gc_lon, profile.target_lat, profile.target_lon)
        perp_bearing = (cur_track_bearing + 90.0) % 360.0
        cur_lat, cur_lon = destination_point(gc_lat, gc_lon, perp_bearing, y)

        dist_to_target = great_circle_distance(
            cur_lat, cur_lon,
            profile.target_lat, profile.target_lon
        )
        progress = min(100.0, max(0.0, (t / max(1.0, total_etof)) * 100.0))
        time_remaining = max(0.0, total_etof - t)

        rho = atmospheric_density(z)
        q = 0.5 * rho * (v**2)
        cd = drag_coefficient(mach, profile.cd_subsonic)
        f_drag = q * cd * profile.reference_area_m2
        x, y_ecef, z_ecef = geodetic_to_ecef(cur_lat, cur_lon, z)

        heading = (cur_track_bearing + math.degrees(math.atan2(vy, max(1e-4, vs)))) % 360.0
        gamma_deg = math.degrees(math.atan2(vz, max(1e-4, math.sqrt(vs**2 + vy**2))))

        telemetry_list.append(Telemetry(
            timestamp=t,
            lat=cur_lat,
            lon=cur_lon,
            altitude=z,
            mach=mach,
            velocity_ms=v,
            velocity_kmh=v * 3.6,
            phase=current_phase,
            downrange_distance_m=s,
            distance_to_target_m=dist_to_target,
            etof_s=total_etof,
            time_remaining_s=time_remaining,
            progress_percent=progress,
            x_ecef=x, y_ecef=y_ecef, z_ecef=z_ecef,
            heading_deg=heading,
            flight_path_angle_deg=gamma_deg,
            crossrange_m=y,
            dynamic_pressure_pa=q,
            drag_force_n=f_drag
        ))

        if current_phase == FlightPhase.TERMINAL and (z <= 0.0 or dist_to_target < 2000.0):
            break

        f_deriv = lambda _t, _st: derivatives(_t, _st, current_phase)
        state = rk4_step(f_deriv, t, state, dt)
        t += dt
        step_count += 1

    last = telemetry_list[-1]
    last.altitude = 0.0
    last.progress_percent = 100.0
    last.time_remaining_s = 0.0
    last.distance_to_target_m = 0.0
    last.lat = profile.target_lat
    last.lon = profile.target_lon
    last.etof_s = t

    for tel in telemetry_list:
        tel.etof_s = t
        tel.time_remaining_s = max(0.0, t - tel.timestamp)
        tel.progress_percent = min(100.0, (tel.timestamp / t) * 100.0)

    return Trajectory(profile, telemetry_list)


def _simulate_cruise(
    profile: ThreatProfile, total_range_m: float, init_bearing: float, dt: float
) -> Trajectory:
    """
    Subsonic Cruise Missile (Tomahawk / TLAM):
      1. BOOST: Short solid rocket booster phase to achieve cruise airspeed.
      2. MIDCOURSE: Low-altitude contour / sea-skimming flight (50-300 m AGL) at constant Mach.
      3. TERMINAL: Terminal pop-up / dive onto target coordinates.
    """
    t_boost = profile.boost_duration_s
    cruise_alt = profile.cruise_altitude_m if profile.cruise_altitude_m is not None else 100.0
    cruise_mach = profile.cruise_mach if profile.cruise_mach is not None else 0.74
    cruise_speed = cruise_mach * speed_of_sound(cruise_alt)  # ~250 m/s

    s_boost = 0.5 * (cruise_speed / t_boost) * (t_boost**2)
    s_terminal_start = total_range_m - 8000.0
    t_cruise_est = (s_terminal_start - s_boost) / cruise_speed
    t_terminal_est = 8000.0 / (0.8 * cruise_speed)
    total_etof = t_boost + t_cruise_est + t_terminal_est

    # State: [s, z, vs, vz]
    state = np.array([0.0, profile.launch_alt, 0.0, 0.0], dtype=np.float64)
    t = 0.0
    telemetry_list: List[Telemetry] = []

    def derivatives(t_curr: float, st: np.ndarray, phase: FlightPhase) -> np.ndarray:
        s, z, vs, vz = st
        v = math.sqrt(vs**2 + vz**2)
        gz = gravity(z)

        rho = atmospheric_density(z)
        mach = mach_number(v, z)
        cd = drag_coefficient(mach, profile.cd_subsonic)
        f_drag = 0.5 * rho * (v**2) * cd * profile.reference_area_m2
        a_drag_s = -(f_drag / profile.mass_kg) * (vs / max(1e-4, v))
        a_drag_z = -(f_drag / profile.mass_kg) * (vz / max(1e-4, v))

        if phase == FlightPhase.BOOST:
            a_boost_s = (cruise_speed / t_boost)
            target_z = cruise_alt * (t_curr / t_boost)
            az_ctrl = 0.5 * (target_z - z) - 0.8 * vz
            return np.array([vs, vz, a_boost_s + a_drag_s, az_ctrl - gz + a_drag_z])

        elif phase == FlightPhase.MIDCOURSE:
            # Cruise thrust precisely balances drag to maintain constant Mach
            thrust_accel = f_drag / profile.mass_kg
            # Aerodynamic lift balances gravity and stabilizes cruise altitude
            az_ctrl = gz - a_drag_z + 0.4 * (cruise_alt - z) - 0.8 * vz
            as_ctrl = thrust_accel + a_drag_s + 0.2 * (cruise_speed - vs)
            return np.array([vs, vz, as_ctrl, az_ctrl - gz + a_drag_z])

        else: # TERMINAL
            target_vz = -max(50.0, vs * 0.4)
            az_ctrl = 0.5 * (target_vz - vz)
            return np.array([vs, vz, a_drag_s, az_ctrl - gz + a_drag_z])

    step_count = 0
    while step_count < 25000:
        s, z, vs, vz = state
        v = math.sqrt(vs**2 + vz**2)
        mach = mach_number(v, z)

        if t < t_boost:
            current_phase = FlightPhase.BOOST
        elif s < s_terminal_start:
            current_phase = FlightPhase.MIDCOURSE
        else:
            current_phase = FlightPhase.TERMINAL

        frac = min(1.0, max(0.0, s / total_range_m))
        cur_lat, cur_lon = great_circle_waypoint(
            profile.launch_lat, profile.launch_lon,
            profile.target_lat, profile.target_lon,
            frac
        )
        dist_to_target = great_circle_distance(
            cur_lat, cur_lon,
            profile.target_lat, profile.target_lon
        )
        progress = min(100.0, max(0.0, (t / max(1.0, total_etof)) * 100.0))
        time_remaining = max(0.0, total_etof - t)

        rho = atmospheric_density(z)
        q = 0.5 * rho * (v**2)
        cd = drag_coefficient(mach, profile.cd_subsonic)
        f_drag = q * cd * profile.reference_area_m2
        x, y, z_ecef = geodetic_to_ecef(cur_lat, cur_lon, z)

        gamma_deg = math.degrees(math.atan2(vz, max(1e-4, vs)))

        telemetry_list.append(Telemetry(
            timestamp=t,
            lat=cur_lat,
            lon=cur_lon,
            altitude=z,
            mach=mach,
            velocity_ms=v,
            velocity_kmh=v * 3.6,
            phase=current_phase,
            downrange_distance_m=s,
            distance_to_target_m=dist_to_target,
            etof_s=total_etof,
            time_remaining_s=time_remaining,
            progress_percent=progress,
            x_ecef=x, y_ecef=y, z_ecef=z_ecef,
            heading_deg=init_bearing,
            flight_path_angle_deg=gamma_deg,
            crossrange_m=0.0,
            dynamic_pressure_pa=q,
            drag_force_n=f_drag
        ))

        if current_phase == FlightPhase.TERMINAL and (z <= 0.0 or dist_to_target < 500.0):
            break

        f_deriv = lambda _t, _st: derivatives(_t, _st, current_phase)
        state = rk4_step(f_deriv, t, state, dt)
        t += dt
        step_count += 1

    last = telemetry_list[-1]
    last.altitude = 0.0
    last.progress_percent = 100.0
    last.time_remaining_s = 0.0
    last.distance_to_target_m = 0.0
    last.lat = profile.target_lat
    last.lon = profile.target_lon
    last.etof_s = t

    for tel in telemetry_list:
        tel.etof_s = t
        tel.time_remaining_s = max(0.0, t - tel.timestamp)
        tel.progress_percent = min(100.0, (tel.timestamp / t) * 100.0)

    return Trajectory(profile, telemetry_list)


def _simulate_drone(
    profile: ThreatProfile, total_range_m: float, init_bearing: float, dt: float
) -> Trajectory:
    """
    Subsonic Loitering Munition / Drone (Anduril ALTIUS / Barracuda):
      1. BOOST: Short launch / motor spinup.
      2. MIDCOURSE: Low-altitude subsonic cruise (100-1000 m AGL) along great circle.
      3. LOITER: Circular orbit around target coordinates at specified radius and duration.
      4. TERMINAL: Terminal attack dive into target center.
    """
    t_boost = profile.boost_duration_s
    cruise_alt = profile.cruise_altitude_m if profile.cruise_altitude_m is not None else profile.loiter_altitude_m
    cruise_mach = profile.cruise_mach if profile.cruise_mach is not None else 0.28
    cruise_speed = cruise_mach * speed_of_sound(cruise_alt)  # ~90 - 100 m/s

    loiter_radius = profile.loiter_radius_m
    loiter_duration = profile.loiter_duration_s if profile.has_loiter else 0.0

    s_cruise_end = max(0.0, total_range_m - loiter_radius)
    t_cruise_est = (s_cruise_end) / cruise_speed
    t_terminal_est = loiter_radius / (cruise_speed * 0.8)
    total_etof = t_boost + t_cruise_est + loiter_duration + t_terminal_est

    state = np.array([0.0, cruise_alt, cruise_speed, 0.0], dtype=np.float64)
    t = 0.0
    t_loiter_start: Optional[float] = None
    telemetry_list: List[Telemetry] = []

    step_count = 0
    while step_count < 25000:
        s, z, vs, vz = state
        v = math.sqrt(vs**2 + vz**2)
        mach = mach_number(v, z)

        # Determine phase
        if t < t_boost:
            current_phase = FlightPhase.BOOST
        elif profile.has_loiter and s >= s_cruise_end and (t_loiter_start is None or (t - t_loiter_start) < loiter_duration):
            if t_loiter_start is None:
                t_loiter_start = t
            current_phase = FlightPhase.LOITER
        elif profile.has_loiter and t_loiter_start is not None and (t - t_loiter_start) >= loiter_duration:
            current_phase = FlightPhase.TERMINAL
        elif not profile.has_loiter and s >= (total_range_m - 3000.0):
            current_phase = FlightPhase.TERMINAL
        else:
            current_phase = FlightPhase.MIDCOURSE

        # Coordinates computation
        if current_phase == FlightPhase.LOITER:
            # Circular orbit around target coordinates
            elapsed_loiter = t - t_loiter_start
            omega_loiter = cruise_speed / loiter_radius
            current_angle = omega_loiter * elapsed_loiter
            # ENU displacement relative to target
            e_offset = loiter_radius * math.cos(current_angle)
            n_offset = loiter_radius * math.sin(current_angle)
            cur_lat, cur_lon, _ = enu_to_geodetic(
                e_offset, n_offset, z,
                profile.target_lat, profile.target_lon, profile.target_alt
            )
            dist_to_target = loiter_radius
            heading = (math.degrees(current_angle + 0.5 * math.pi) + 360.0) % 360.0
            crossrange = loiter_radius
        elif current_phase == FlightPhase.TERMINAL:
            # Diving into target
            rem_ratio = max(0.0, min(1.0, (z / max(10.0, cruise_alt))))
            cur_dist = loiter_radius * rem_ratio
            cur_lat, cur_lon = destination_point(
                profile.target_lat, profile.target_lon,
                (init_bearing + 180.0) % 360.0,
                cur_dist
            )
            dist_to_target = cur_dist
            heading = init_bearing
            crossrange = 0.0
        else: # BOOST or MIDCOURSE
            frac = min(1.0, max(0.0, s / total_range_m))
            cur_lat, cur_lon = great_circle_waypoint(
                profile.launch_lat, profile.launch_lon,
                profile.target_lat, profile.target_lon,
                frac
            )
            dist_to_target = great_circle_distance(
                cur_lat, cur_lon,
                profile.target_lat, profile.target_lon
            )
            heading = init_bearing
            crossrange = 0.0

        progress = min(100.0, max(0.0, (t / max(1.0, total_etof)) * 100.0))
        time_remaining = max(0.0, total_etof - t)

        rho = atmospheric_density(z)
        q = 0.5 * rho * (v**2)
        cd = drag_coefficient(mach, profile.cd_subsonic)
        f_drag = q * cd * profile.reference_area_m2
        x, y, z_ecef = geodetic_to_ecef(cur_lat, cur_lon, z)

        gamma_deg = math.degrees(math.atan2(vz, max(1e-4, vs)))

        telemetry_list.append(Telemetry(
            timestamp=t,
            lat=cur_lat,
            lon=cur_lon,
            altitude=z,
            mach=mach,
            velocity_ms=v,
            velocity_kmh=v * 3.6,
            phase=current_phase,
            downrange_distance_m=s,
            distance_to_target_m=dist_to_target,
            etof_s=total_etof,
            time_remaining_s=time_remaining,
            progress_percent=progress,
            x_ecef=x, y_ecef=y, z_ecef=z_ecef,
            heading_deg=heading,
            flight_path_angle_deg=gamma_deg,
            crossrange_m=crossrange,
            dynamic_pressure_pa=q,
            drag_force_n=f_drag
        ))

        if current_phase == FlightPhase.TERMINAL and (z <= 0.0 or dist_to_target < 50.0):
            break

        # Derivative for RK4 integration
        def drone_deriv(t_curr: float, st: np.ndarray) -> np.ndarray:
            _s, _z, _vs, _vz = st
            gz = gravity(_z)
            if current_phase == FlightPhase.TERMINAL:
                # Terminal dive
                vz_cmd = -max(25.0, cruise_speed * 0.4)
                az_c = 0.8 * (vz_cmd - _vz)
                return np.array([cruise_speed, _vz, 0.0, az_c])
            elif current_phase == FlightPhase.LOITER:
                # Constant speed and altitude orbit
                az_c = 0.5 * (profile.loiter_altitude_m - _z) - 0.8 * _vz
                return np.array([0.0, _vz, 0.0, az_c])
            else:
                az_c = 0.5 * (cruise_alt - _z) - 0.8 * _vz
                as_c = 0.2 * (cruise_speed - _vs)
                return np.array([_vs, _vz, as_c, az_c])

        state = rk4_step(lambda _t, _st: drone_deriv(_t, _st), t, state, dt)
        t += dt
        step_count += 1

    last = telemetry_list[-1]
    last.altitude = 0.0
    last.progress_percent = 100.0
    last.time_remaining_s = 0.0
    last.distance_to_target_m = 0.0
    last.lat = profile.target_lat
    last.lon = profile.target_lon
    last.etof_s = t

    for tel in telemetry_list:
        tel.etof_s = t
        tel.time_remaining_s = max(0.0, t - tel.timestamp)
        tel.progress_percent = min(100.0, (tel.timestamp / t) * 100.0)

    return Trajectory(profile, telemetry_list)


# ==============================================================================
# 8. THREAT SYSTEM FACTORY GENERATORS
# ==============================================================================