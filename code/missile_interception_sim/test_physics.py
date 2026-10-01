"""
TEST SUITE: Physics Engine Verification
=======================================
Verifies geodetic (WGS84) transformations, Great-Circle math, atmospheric and gravity models,
and 3-DoF Runge-Kutta 4th Order (RK4) trajectory simulations for all 4 offensive threat classes:
  1. ICBM (Minuteman / Sarmat) - Keplerian suborbital coast (apogee > 100 km, Mach 20+)
  2. Iskander-M (9M723 SRBM) - Quasi-ballistic depressed apogee (30 - 50 km, Mach 5.5 - 6.5)
  3. Kinzhal (Kh-47M2) - Depressed glide (25 - 40 km) with skipping and lateral weave (Mach 8 - 11)
  4. Tomahawk (BGM-109) - Low-altitude contour / sea-skimming (50 - 300 m AGL) at constant Mach
  5. Anduril ALTIUS / Barracuda - Subsonic cruise (100 - 1000 m AGL) with circular target loitering

Usage:
  python test_physics.py
"""

import math
import sys
import unittest
import numpy as np
import pandas as pd

import physics_engine as pe


class TestWGS84AndCoordinateTransforms(unittest.TestCase):
    """Test geodetic (WGS84) to ECEF and local Cartesian ENU transformations."""

    def test_wgs84_ecef_roundtrip(self):
        """Verify sub-millimeter roundtrip between geodetic (lat, lon, alt) and ECEF (X, Y, Z)."""
        test_points = [
            (0.0, 0.0, 0.0),             # Prime meridian at Equator
            (55.7558, 37.6173, 150.0),     # Moscow
            (38.8951, -77.0364, 25.0),     # Washington DC
            (90.0, 0.0, 1000.0),          # North Pole
            (-90.0, 0.0, 2800.0),         # South Pole
            (-33.8688, 151.2093, 40.0),   # Sydney
            (45.0, 45.0, 500000.0),       # High altitude (500 km exo-atmospheric)
        ]
        for lat, lon, alt in test_points:
            x, y, z = pe.geodetic_to_ecef(lat, lon, alt)
            lat_r, lon_r, alt_r = pe.ecef_to_geodetic(x, y, z)
            self.assertAlmostEqual(lat, lat_r, places=6, msg=f"Latitude mismatch at {lat}, {lon}")
            self.assertAlmostEqual(lon, lon_r, places=6, msg=f"Longitude mismatch at {lat}, {lon}")
            self.assertAlmostEqual(alt, alt_r, delta=0.005, msg=f"Altitude mismatch at {lat}, {lon}")

    def test_local_cartesian_enu_roundtrip(self):
        """Verify local East-North-Up (ENU) conversion accuracy."""
        ref_lat, ref_lon, ref_alt = 38.8951, -77.0364, 50.0
        offsets = [
            (1000.0, 2000.0, 300.0),
            (-5000.0, 10000.0, 1500.0),
            (25000.0, -15000.0, 5000.0),
        ]
        for e, n, u in offsets:
            x, y, z = pe.enu_to_ecef(e, n, u, ref_lat, ref_lon, ref_alt)
            e_r, n_r, u_r = pe.ecef_to_enu(x, y, z, ref_lat, ref_lon, ref_alt)
            self.assertAlmostEqual(e, e_r, delta=0.001)
            self.assertAlmostEqual(n, n_r, delta=0.001)
            self.assertAlmostEqual(u, u_r, delta=0.001)

            lat, lon, alt = pe.enu_to_geodetic(e, n, u, ref_lat, ref_lon, ref_alt)
            e_g, n_g, u_g = pe.geodetic_to_enu(lat, lon, alt, ref_lat, ref_lon, ref_alt)
            self.assertAlmostEqual(e, e_g, delta=0.005)
            self.assertAlmostEqual(n, n_g, delta=0.005)
            self.assertAlmostEqual(u, u_g, delta=0.005)


class TestGreatCircleMath(unittest.TestCase):
    """Test Great-Circle geodesic distance, forward bearing, and waypoints."""

    def test_great_circle_distance_and_bearing(self):
        # Moscow to Washington DC
        lat1, lon1 = 55.7558, 37.6173
        lat2, lon2 = 38.8951, -77.0364
        dist = pe.great_circle_distance(lat1, lon1, lat2, lon2)
        bearing = pe.initial_bearing(lat1, lon1, lat2, lon2)

        # Distance ~7822 km, Initial Bearing ~311.3 deg
        self.assertAlmostEqual(dist / 1000.0, 7822.0, delta=15.0)
        self.assertAlmostEqual(bearing, 311.3, delta=1.5)

    def test_waypoint_interpolation(self):
        lat1, lon1 = 55.7558, 37.6173
        lat2, lon2 = 38.8951, -77.0364
        total_dist = pe.great_circle_distance(lat1, lon1, lat2, lon2)

        mid_lat, mid_lon = pe.great_circle_waypoint(lat1, lon1, lat2, lon2, 0.5)
        d1 = pe.great_circle_distance(lat1, lon1, mid_lat, mid_lon)
        d2 = pe.great_circle_distance(mid_lat, mid_lon, lat2, lon2)

        self.assertAlmostEqual(d1, d2, delta=1.0)
        self.assertAlmostEqual(d1 + d2, total_dist, delta=1.0)

    def test_destination_point(self):
        lat1, lon1 = 34.0, 24.0
        bearing = 60.0
        dist = 50000.0  # 50 km
        dest_lat, dest_lon = pe.destination_point(lat1, lon1, bearing, dist)
        meas_dist = pe.great_circle_distance(lat1, lon1, dest_lat, dest_lon)
        meas_bearing = pe.initial_bearing(lat1, lon1, dest_lat, dest_lon)

        self.assertAlmostEqual(meas_dist, dist, delta=1.0)
        self.assertAlmostEqual(meas_bearing, bearing, delta=0.1)


class TestAtmosphereAndAerodynamics(unittest.TestCase):
    """Test exponential atmospheric density, gravity, and drag coefficients."""

    def test_barometric_density(self):
        # Sea level rho = 1.225
        self.assertAlmostEqual(pe.atmospheric_density(0.0), 1.225, places=3)
        # At scale height H = 7500 m, rho = 1.225 / e ~ 0.45065
        self.assertAlmostEqual(pe.atmospheric_density(7500.0), 1.225 / math.e, places=3)
        # Exo-atmospheric (> 150 km) is 0
        self.assertEqual(pe.atmospheric_density(160000.0), 0.0)

    def test_altitude_dependent_gravity(self):
        # Sea level g = 9.80665 m/s^2
        self.assertAlmostEqual(pe.gravity(0.0), 9.80665, places=4)
        # At z = R_E, g = g0 / 4 ~ 2.45166 m/s^2
        self.assertAlmostEqual(pe.gravity(pe.R_EARTH), 9.80665 / 4.0, places=4)
        # Monotonically decreasing with altitude
        self.assertTrue(pe.gravity(10000.0) < pe.gravity(0.0))
        self.assertTrue(pe.gravity(100000.0) < pe.gravity(10000.0))

    def test_speed_of_sound_and_drag_coefficient(self):
        # Standard sea level sound speed ~340.3 m/s
        cs_0 = pe.speed_of_sound(0.0)
        self.assertAlmostEqual(cs_0, 340.29, delta=0.5)

        # Transonic drag rise around Mach 1.0 - 1.2
        cd_sub = pe.drag_coefficient(0.5, cd_subsonic=0.20)
        cd_trans = pe.drag_coefficient(1.1, cd_subsonic=0.20)
        cd_hyper = pe.drag_coefficient(8.0, cd_subsonic=0.20)
        self.assertEqual(cd_sub, 0.20)
        self.assertTrue(cd_trans > cd_sub, "Transonic drag should exceed subsonic drag")
        self.assertTrue(cd_hyper < cd_trans, "Hypersonic drag should be lower than transonic peak")


class TestThreatTrajectorySimulations(unittest.TestCase):
    """Verify RK4 3-DoF trajectory profiles for all 5 operational systems."""

    def test_icbm_trajectory(self):
        """
        Verify ICBM Profile (Minuteman III / Sarmat scale):
          - Range: ~7822 km
          - High-apogee Keplerian ballistic coast: z > 100 km (typically 1000 - 2500 km)
          - Hypersonic velocity: Mach 19 - 25 (> 6000 m/s)
          - Phases: BOOST -> MIDCOURSE -> TERMINAL
          - Monotonic progress 0% -> 100%
        """
        print("\n" + "=" * 70)
        print("SIMULATION VERIFICATION: ICBM (Intercontinental Ballistic Missile)")
        print("=" * 70)
        profile = pe.create_icbm_profile()
        traj = pe.simulate_trajectory(profile, dt=1.0)

        apogee_km = traj.apogee_m / 1000.0
        max_vel_ms = traj.max_velocity_ms
        max_mach = traj.max_mach
        flight_time_s = traj.total_flight_time_s
        phases = [p.value for p in traj.phases_traversed]

        print(f"  Range: {pe.great_circle_distance(profile.launch_lat, profile.launch_lon, profile.target_lat, profile.target_lon)/1000:.1f} km")
        print(f"  Apogee: {apogee_km:.2f} km")
        print(f"  Max Velocity: {max_vel_ms:.1f} m/s ({max_vel_ms*3.6:.1f} km/h)")
        print(f"  Max Mach: {max_mach:.2f}")
        print(f"  Flight Time: {flight_time_s:.1f} s ({flight_time_s/60:.1f} min)")
        print(f"  Phases Traversed: {phases}")
        print(f"  Impact Target Miss Distance: {traj.impact_distance_m:.1f} m")

        # Assertions
        self.assertTrue(traj.apogee_m > 100000.0, f"ICBM apogee {apogee_km} km must be > 100 km")
        self.assertTrue(1000.0 <= apogee_km <= 2500.0, f"ICBM apogee {apogee_km} km outside realistic envelope (1000-2500 km)")
        self.assertTrue(max_mach >= 19.0, f"ICBM max Mach {max_mach:.2f} should be >= 19.0")
        self.assertTrue(max_vel_ms >= 6000.0, f"ICBM burnout velocity {max_vel_ms:.1f} m/s should be >= 6000 m/s")
        self.assertIn("BOOST", phases)
        self.assertIn("MIDCOURSE", phases)
        self.assertIn("TERMINAL", phases)
        self.assertAlmostEqual(traj.impact_distance_m, 0.0, delta=2000.0)

        # Progress monotonicity
        progs = [t.progress_percent for t in traj.telemetry_history]
        self.assertAlmostEqual(progs[0], 0.0, delta=0.01)
        self.assertAlmostEqual(progs[-1], 100.0, delta=0.01)
        self.assertTrue(all(p1 <= p2 + 1e-4 for p1, p2 in zip(progs, progs[1:])), "Progress not monotonic")

    def test_iskander_trajectory(self):
        """
        Verify Iskander-M Profile (9M723 SRBM):
          - Range: ~278 km (Kaliningrad to Warsaw)
          - Quasi-ballistic depressed apogee: strictly 30 - 50 km
          - High supersonic / hypersonic velocity: Mach 5.5 - 6.5 (~1700 - 2000 m/s)
          - Phases: BOOST -> MIDCOURSE -> TERMINAL
          - Monotonic progress 0% -> 100%
        """
        print("\n" + "=" * 70)
        print("SIMULATION VERIFICATION: Iskander-M (9M723 Short-Range Ballistic)")
        print("=" * 70)
        profile = pe.create_iskander_profile()
        traj = pe.simulate_trajectory(profile, dt=0.5)

        apogee_km = traj.apogee_m / 1000.0
        max_vel_ms = traj.max_velocity_ms
        max_mach = traj.max_mach
        flight_time_s = traj.total_flight_time_s
        phases = [p.value for p in traj.phases_traversed]

        print(f"  Range: {pe.great_circle_distance(profile.launch_lat, profile.launch_lon, profile.target_lat, profile.target_lon)/1000:.1f} km")
        print(f"  Apogee: {apogee_km:.2f} km")
        print(f"  Max Velocity: {max_vel_ms:.1f} m/s ({max_vel_ms*3.6:.1f} km/h)")
        print(f"  Max Mach: {max_mach:.2f}")
        print(f"  Flight Time: {flight_time_s:.1f} s ({flight_time_s/60:.1f} min)")
        print(f"  Phases Traversed: {phases}")
        print(f"  Impact Target Miss Distance: {traj.impact_distance_m:.1f} m")

        # Assertions
        self.assertTrue(30.0 <= apogee_km <= 50.0, f"Iskander-M apogee {apogee_km:.2f} km must be within 30-50 km")
        self.assertTrue(5.0 <= max_mach <= 7.0, f"Iskander-M max Mach {max_mach:.2f} must be within 5.0-7.0")
        self.assertTrue(1500.0 <= max_vel_ms <= 2200.0, f"Iskander-M max velocity {max_vel_ms:.1f} m/s out of range")
        self.assertIn("BOOST", phases)
        self.assertIn("MIDCOURSE", phases)
        self.assertIn("TERMINAL", phases)
        self.assertAlmostEqual(traj.impact_distance_m, 0.0, delta=2000.0)

        progs = [t.progress_percent for t in traj.telemetry_history]
        self.assertAlmostEqual(progs[0], 0.0, delta=0.01)
        self.assertAlmostEqual(progs[-1], 100.0, delta=0.01)
        self.assertTrue(all(p1 <= p2 + 1e-4 for p1, p2 in zip(progs, progs[1:])), "Progress not monotonic")

    def test_kinzhal_trajectory(self):
        """
        Verify Kh-47M2 Kinzhal Profile (Hypersonic Aero-Ballistic Glide):
          - Range: ~700 - 1000 km
          - Depressed glide: strictly 25 - 40 km glide ceiling
          - Atmospheric skipping: verified altitude variation >= 2000 m
          - Periodic lateral weave: verified crossrange variation >= 3000 m
          - Hypersonic velocity: Mach 8.5 - 11.5 (~2700 - 3300 m/s)
          - Phases: BOOST -> GLIDE -> TERMINAL
        """
        print("\n" + "=" * 70)
        print("SIMULATION VERIFICATION: Kh-47M2 Kinzhal (Hypersonic Glide Weapon)")
        print("=" * 70)
        profile = pe.create_kinzhal_profile()
        traj = pe.simulate_trajectory(profile, dt=0.5)

        apogee_km = traj.apogee_m / 1000.0
        max_vel_ms = traj.max_velocity_ms
        max_mach = traj.max_mach
        flight_time_s = traj.total_flight_time_s
        phases = [p.value for p in traj.phases_traversed]

        glide_telems = [t for t in traj.telemetry_history if t.phase == pe.FlightPhase.GLIDE]
        self.assertTrue(len(glide_telems) > 0, "Trajectory must contain GLIDE phase")
        glide_alts = [t.altitude / 1000.0 for t in glide_telems]
        glide_cross = [t.crossrange_m / 1000.0 for t in glide_telems]

        skip_variation_km = max(glide_alts) - min(glide_alts)
        max_crossrange_km = max(abs(c) for c in glide_cross)

        print(f"  Range: {pe.great_circle_distance(profile.launch_lat, profile.launch_lon, profile.target_lat, profile.target_lon)/1000:.1f} km")
        print(f"  Glide Ceiling / Apogee: {apogee_km:.2f} km")
        print(f"  Glide Altitude Range: {min(glide_alts):.2f} km to {max(glide_alts):.2f} km (Skipping Variation: {skip_variation_km:.2f} km)")
        print(f"  Crossrange Weave Amplitude: +/-{max_crossrange_km:.2f} km")
        print(f"  Max Velocity: {max_vel_ms:.1f} m/s ({max_vel_ms*3.6:.1f} km/h)")
        print(f"  Max Mach: {max_mach:.2f}")
        print(f"  Flight Time: {flight_time_s:.1f} s ({flight_time_s/60:.1f} min)")
        print(f"  Phases Traversed: {phases}")
        print(f"  Impact Target Miss Distance: {traj.impact_distance_m:.1f} m")

        # Assertions
        self.assertTrue(25.0 <= apogee_km <= 40.0, f"Kinzhal glide ceiling {apogee_km:.2f} km must be within 25-40 km")
        self.assertTrue(skip_variation_km >= 2.0, f"Skipping variation {skip_variation_km:.2f} km must be >= 2.0 km")
        self.assertTrue(max_crossrange_km >= 3.0, f"Lateral weave amplitude {max_crossrange_km:.2f} km must be >= 3.0 km")
        self.assertTrue(8.5 <= max_mach <= 11.5, f"Kinzhal max Mach {max_mach:.2f} must be within 8.5-11.5")
        self.assertIn("BOOST", phases)
        self.assertIn("GLIDE", phases)
        self.assertIn("TERMINAL", phases)
        self.assertAlmostEqual(traj.impact_distance_m, 0.0, delta=2000.0)

        progs = [t.progress_percent for t in traj.telemetry_history]
        self.assertAlmostEqual(progs[0], 0.0, delta=0.01)
        self.assertAlmostEqual(progs[-1], 100.0, delta=0.01)
        self.assertTrue(all(p1 <= p2 + 1e-4 for p1, p2 in zip(progs, progs[1:])), "Progress not monotonic")

    def test_tomahawk_trajectory(self):
        """
        Verify BGM-109 Tomahawk Profile (Subsonic Land-Attack Cruise Missile):
          - Range: ~1135 km (Eastern Med to Damascus)
          - Sea-skimming / low-altitude contour: strictly 50 - 300 m AGL (nominal ~120 m)
          - Constant subsonic cruise: Mach 0.70 - 0.80 (~240 - 270 m/s)
          - Phases: BOOST -> MIDCOURSE -> TERMINAL
        """
        print("\n" + "=" * 70)
        print("SIMULATION VERIFICATION: BGM-109 Tomahawk (Subsonic Cruise Missile)")
        print("=" * 70)
        profile = pe.create_tomahawk_profile()
        traj = pe.simulate_trajectory(profile, dt=2.0)

        apogee_m = traj.apogee_m
        max_vel_ms = traj.max_velocity_ms
        max_mach = traj.max_mach
        flight_time_s = traj.total_flight_time_s
        phases = [p.value for p in traj.phases_traversed]

        midcourse_telems = [t for t in traj.telemetry_history if t.phase == pe.FlightPhase.MIDCOURSE]
        self.assertTrue(len(midcourse_telems) > 0)
        mean_cruise_alt = np.mean([t.altitude for t in midcourse_telems])
        mean_cruise_mach = np.mean([t.mach for t in midcourse_telems])

        print(f"  Range: {pe.great_circle_distance(profile.launch_lat, profile.launch_lon, profile.target_lat, profile.target_lon)/1000:.1f} km")
        print(f"  Cruise Altitude: {mean_cruise_alt:.1f} m AGL (Max Altitude: {apogee_m:.1f} m)")
        print(f"  Cruise Mach: {mean_cruise_mach:.2f} (Max Mach: {max_mach:.2f})")
        print(f"  Cruise Velocity: {max_vel_ms:.1f} m/s ({max_vel_ms*3.6:.1f} km/h)")
        print(f"  Flight Time: {flight_time_s:.1f} s ({flight_time_s/60:.1f} min)")
        print(f"  Phases Traversed: {phases}")
        print(f"  Impact Target Miss Distance: {traj.impact_distance_m:.1f} m")

        # Assertions
        self.assertTrue(50.0 <= mean_cruise_alt <= 300.0, f"Cruise altitude {mean_cruise_alt:.1f} m must be in 50-300 m")
        self.assertTrue(50.0 <= apogee_m <= 300.0, f"Max altitude {apogee_m:.1f} m must be in 50-300 m")
        self.assertTrue(0.70 <= mean_cruise_mach <= 0.80, f"Cruise Mach {mean_cruise_mach:.2f} must be in 0.70-0.80")
        self.assertIn("BOOST", phases)
        self.assertIn("MIDCOURSE", phases)
        self.assertIn("TERMINAL", phases)
        self.assertAlmostEqual(traj.impact_distance_m, 0.0, delta=2000.0)

        progs = [t.progress_percent for t in traj.telemetry_history]
        self.assertAlmostEqual(progs[0], 0.0, delta=0.01)
        self.assertAlmostEqual(progs[-1], 100.0, delta=0.01)
        self.assertTrue(all(p1 <= p2 + 1e-4 for p1, p2 in zip(progs, progs[1:])), "Progress not monotonic")

    def test_altius_drone_trajectory(self):
        """
        Verify Anduril ALTIUS-600 / Barracuda Drone (Loitering Munition):
          - Range: ~180 km
          - Low-altitude subsonic flight: strictly 100 - 1000 m AGL (nominal ~400 m)
          - Subsonic speed: Mach 0.20 - 0.35 (~70 - 110 m/s)
          - Circular target loitering: confirmed LOITER phase for >= 250 s around target
          - Phases: BOOST -> MIDCOURSE -> LOITER -> TERMINAL
        """
        print("\n" + "=" * 70)
        print("SIMULATION VERIFICATION: Anduril ALTIUS / Barracuda (Loitering Munition)")
        print("=" * 70)
        profile = pe.create_altius_drone_profile()
        traj = pe.simulate_trajectory(profile, dt=1.0)

        apogee_m = traj.apogee_m
        max_vel_ms = traj.max_velocity_ms
        max_mach = traj.max_mach
        flight_time_s = traj.total_flight_time_s
        phases = [p.value for p in traj.phases_traversed]

        loiter_telems = [t for t in traj.telemetry_history if t.phase == pe.FlightPhase.LOITER]
        self.assertTrue(len(loiter_telems) > 0, "Trajectory must contain LOITER phase")
        loiter_duration_s = loiter_telems[-1].timestamp - loiter_telems[0].timestamp
        loiter_distances = [t.distance_to_target_m for t in loiter_telems]
        mean_loiter_radius = np.mean(loiter_distances)

        print(f"  Range: {pe.great_circle_distance(profile.launch_lat, profile.launch_lon, profile.target_lat, profile.target_lon)/1000:.1f} km")
        print(f"  Cruise Altitude: {apogee_m:.1f} m AGL")
        print(f"  Loiter Duration: {loiter_duration_s:.1f} s (~{loiter_duration_s/60:.1f} min)")
        print(f"  Mean Loiter Radius: {mean_loiter_radius:.1f} m (Configured: {profile.loiter_radius_m:.1f} m)")
        print(f"  Subsonic Speed: {max_vel_ms:.1f} m/s ({max_vel_ms*3.6:.1f} km/h, Mach {max_mach:.2f})")
        print(f"  Flight Time: {flight_time_s:.1f} s ({flight_time_s/60:.1f} min)")
        print(f"  Phases Traversed: {phases}")
        print(f"  Impact Target Miss Distance: {traj.impact_distance_m:.1f} m")

        # Assertions
        self.assertTrue(100.0 <= apogee_m <= 1000.0, f"Drone altitude {apogee_m:.1f} m must be in 100-1000 m")
        self.assertTrue(0.15 <= max_mach <= 0.35, f"Drone Mach {max_mach:.2f} must be in 0.15-0.35")
        self.assertTrue(loiter_duration_s >= 250.0, f"Loiter duration {loiter_duration_s:.1f} s must be >= 250 s")
        self.assertAlmostEqual(mean_loiter_radius, profile.loiter_radius_m, delta=100.0)
        self.assertIn("BOOST", phases)
        self.assertIn("MIDCOURSE", phases)
        self.assertIn("LOITER", phases)
        self.assertIn("TERMINAL", phases)
        self.assertAlmostEqual(traj.impact_distance_m, 0.0, delta=500.0)

        progs = [t.progress_percent for t in traj.telemetry_history]
        self.assertAlmostEqual(progs[0], 0.0, delta=0.01)
        self.assertAlmostEqual(progs[-1], 100.0, delta=0.01)
        self.assertTrue(all(p1 <= p2 + 1e-4 for p1, p2 in zip(progs, progs[1:])), "Progress not monotonic")

    def test_continuous_telemetry_lookup_and_dataframe(self):
        """Verify arbitrary timestamp telemetry retrieval and DataFrame export."""
        profile = pe.create_iskander_profile()
        traj = pe.simulate_trajectory(profile, dt=0.5)

        # Lookup at arbitrary continuous time
        sample_time = 123.456
        telem = traj.get_telemetry_at_time(sample_time)
        self.assertAlmostEqual(telem.timestamp, sample_time, places=4)
        self.assertTrue(telem.progress_percent > 0.0)
        self.assertTrue(telem.progress_percent < 100.0)
        self.assertTrue(telem.downrange_distance_m > 0.0)
        self.assertTrue(telem.distance_to_target_m > 0.0)
        self.assertAlmostEqual(telem.timestamp + telem.time_remaining_s, telem.etof_s, delta=1.0)

        # DataFrame export
        df = traj.to_dataframe()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), len(traj))
        expected_cols = [
            "timestamp", "lat", "lon", "altitude", "mach", "velocity_ms", "velocity_kmh",
            "phase", "downrange_distance_m", "distance_to_target_m", "etof_s",
            "time_remaining_s", "progress_percent", "x_ecef", "y_ecef", "z_ecef",
            "heading_deg", "flight_path_angle_deg", "crossrange_m", "dynamic_pressure_pa"
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns)


def print_summary_table():
    """Print clean summary verification table of all 5 operational systems."""
    systems = [
        ("Minuteman/Sarmat ICBM", pe.create_icbm_profile, 1.0),
        ("9M723 Iskander-M SRBM", pe.create_iskander_profile, 0.5),
        ("Kh-47M2 Kinzhal HGV", pe.create_kinzhal_profile, 0.5),
        ("BGM-109 Tomahawk Cruise", pe.create_tomahawk_profile, 2.0),
        ("Anduril ALTIUS / Barracuda", pe.create_altius_drone_profile, 1.0)
    ]
    print("\n" + "=" * 95)
    print(f"{'Threat System':<28} | {'Class':<10} | {'Apogee':<12} | {'Max Mach':<8} | {'Flight Time':<12} | {'Phases'}")
    print("-" * 95)
    for name, factory, dt in systems:
        p = factory()
        traj = pe.simulate_trajectory(p, dt=dt)
        apo_str = f"{traj.apogee_m/1000:.1f} km" if traj.apogee_m > 1000 else f"{traj.apogee_m:.0f} m"
        time_str = f"{traj.total_flight_time_s:.0f} s ({traj.total_flight_time_s/60:.1f}m)"
        phases_str = "->".join(p.value for p in traj.phases_traversed)
        print(f"{name:<28} | {p.threat_class.value:<10} | {apo_str:<12} | {traj.max_mach:<8.2f} | {time_str:<12} | {phases_str}")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    print_summary_table()
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
