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