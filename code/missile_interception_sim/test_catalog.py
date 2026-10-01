#!/usr/bin/env python3
"""
================================================================================
VERIFICATION TEST SUITE: WEAPONS CATALOG & PRESET TEMPLATES
Missile Interception Simulation Architecture
================================================================================
Runs comprehensive assertions across:
1. Valid loading of weapons_catalog.json
2. Catalog size assertion (assert >= 22 weapon systems, actual: 34 systems)
3. Schema and physical bounds validation (ranges, speeds, altitudes, warheads, Pk)
4. Presence of all mandatory requested systems (ATACMS, Iskander, Minuteman, Sarmat,
   DF-21D, DF-17, Kinzhal, Zircon, ARRW, Tomahawk, Kalibr, Storm Shadow, BrahMos,
   Patriot PAC-3 MSE, THAAD, SM-3 Block IIA, Iron Dome, S-400, Phalanx, Gepard, Skynex,
   Anduril Roadrunner/Roadrunner-M, ALTIUS-600/700/700M, Barracuda-100/250/500,
   Bolt/Bolt-M, Shahed-136, Lancet-3, Switchblade 600)
5. Air defense & CIWS radar and engagement envelope consistency
6. Unit preset site templates validation and cross-referencing
7. Catalog helper API function verification
================================================================================
"""

import sys
import unittest
from pathlib import Path
import json

from catalog import (
    Weapon,
    SiteTemplate,
    load_catalog,
    get_weapon,
    get_weapons_by_category,
    get_weapons_for_role,
    get_site_templates,
    get_site_template,
    get_all_categories,
    DEFAULT_CATALOG_PATH,
)


class TestWeaponsCatalog(unittest.TestCase):
    """Test suite for weapons catalog and preset templates."""

    @classmethod
    def setUpClass(cls):
        """Load catalog once for all test assertions."""
        cls.catalog = load_catalog(reload=True)
        cls.site_templates = get_site_templates()

    def test_01_catalog_size_minimum(self):
        """Assert that catalog contains at least 22 weapon systems."""
        num_weapons = len(self.catalog)
        print(f"\n[TEST 01] Total registered weapon systems: {num_weapons}")
        self.assertGreaterEqual(
            num_weapons,
            22,
            f"Expected at least 22 weapon systems in catalog, but found {num_weapons}."
        )

    def test_02_json_file_validity(self):
        """Assert that weapons_catalog.json is valid, well-formed JSON on disk."""
        self.assertTrue(DEFAULT_CATALOG_PATH.exists(), f"Missing catalog file at: {DEFAULT_CATALOG_PATH}")
        with open(DEFAULT_CATALOG_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        self.assertIn("weapons", raw_data)
        self.assertIsInstance(raw_data["weapons"], list)
        unique_weapons = self.catalog.unique_weapons() if hasattr(self.catalog, "unique_weapons") else list(set(self.catalog.values()))
        self.assertEqual(len(raw_data["weapons"]), len(unique_weapons))

    def test_03_all_mandatory_weapons_present(self):
        """Assert that all specific systems requested in the specification are present."""
        mandatory_weapon_ids = [
            # Ballistic Missiles
            "mgm140_atacms",
            "iskander_m",
            "df_21d",
            "minuteman_iii",
            "rs_28_sarmat",
            # Hypersonic Weapons
            "df_17",
            "kh_47m2_kinzhal",
            "3m22_zircon",
            "agm_183a_arrw",
            # Cruise Missiles
            "bgm_109_tomahawk",
            "kalibr_3m54",
            "storm_shadow",
            "brahmos",
            # Air Defense Missiles
            "patriot_pac3_mse",
            "thaad",
            "sm3_block_iia",
            "iron_dome_tamir",
            "s400_48n6dm",
            # Anti-Air Guns / CIWS
            "phalanx_lpws",
            "flakpanzer_gepard",
            "skynex_35mm",
            # Drones / Loitering Munitions
            "anduril_roadrunner",
            "anduril_roadrunner_m",
            "anduril_altius_600",
            "anduril_altius_700",
            "anduril_altius_700m",
            "anduril_barracuda_100",
            "anduril_barracuda_250",
            "anduril_barracuda_500",
            "anduril_bolt",
            "anduril_bolt_m",
            "shahed_136",
            "lancet_3",
            "switchblade_600",
        ]

        missing_weapons = []
        for wid in mandatory_weapon_ids:
            if wid not in self.catalog:
                missing_weapons.append(wid)

        self.assertEqual(
            missing_weapons,
            [],
            f"Missing required weapons from catalog: {missing_weapons}"
        )
        print(f"[TEST 03] All {len(mandatory_weapon_ids)} required weapon systems verified present.")

    def test_04_schema_and_physical_bounds(self):
        """Assert that every weapon record has physically sound parameters."""
        valid_categories = {"ballistic", "hypersonic", "cruise", "air_defense", "ciws_gun", "drone"}
        valid_roles = {"attacker", "defender", "dual_role"}

        for wid, w in self.catalog.items():
            with self.subTest(weapon_id=wid):
                # ID and name
                self.assertTrue(isinstance(w.id, str) and len(w.id) > 0)
                self.assertTrue(isinstance(w.name, str) and len(w.name) > 0)
                self.assertIn(w.category, valid_categories, f"{wid}: invalid category {w.category}")
                self.assertIn(w.role, valid_roles, f"{wid}: invalid role {w.role}")

                # Manufacturer & Country
                self.assertTrue(len(w.manufacturer.strip()) > 0)
                self.assertTrue(len(w.country.strip()) > 0)

                # Physical range and speeds
                self.assertGreater(w.range_km, 0.0, f"{wid}: range_km must be > 0")
                self.assertGreater(w.max_speed_mach, 0.0, f"{wid}: max_speed_mach must be > 0")
                self.assertGreater(w.max_speed_kmh, 0.0, f"{wid}: max_speed_kmh must be > 0")

                # Altitude bounds: must have either apogee_km or cruise_alt_m defined
                has_altitude = (w.apogee_km is not None) or (w.cruise_alt_m is not None)
                self.assertTrue(has_altitude, f"{wid}: must have either apogee_km or cruise_alt_m defined")

                if w.apogee_km is not None:
                    self.assertGreater(w.apogee_km, 0.0, f"{wid}: apogee_km must be > 0")
                if w.cruise_alt_m is not None:
                    self.assertGreater(w.cruise_alt_m, 0.0, f"{wid}: cruise_alt_m must be > 0")

                # Flight profile and guidance
                self.assertGreaterEqual(len(w.flight_profile.strip()), 5)
                self.assertGreaterEqual(len(w.guidance.strip()), 3)
                self.assertGreaterEqual(len(w.warhead_type.strip()), 3)
                self.assertGreaterEqual(w.warhead_mass_kg, 0.0, f"{wid}: warhead_mass_kg cannot be negative")

                # Probability of kill baseline (Pk)
                self.assertGreaterEqual(w.pk_baseline, 0.0, f"{wid}: pk_baseline cannot be < 0")
                self.assertLessEqual(w.pk_baseline, 1.0, f"{wid}: pk_baseline cannot be > 1.0")

                # Authoritative URL verification
                self.assertTrue(
                    w.sourcing_url.startswith("http://") or w.sourcing_url.startswith("https://"),
                    f"{wid}: sourcing_url must start with http:// or https://"
                )
                self.assertTrue(len(w.sourcing_url.strip()) >= 12)

                # Description
                self.assertGreaterEqual(len(w.description.strip()), 20, f"{wid}: description too brief")

    def test_05_air_defense_and_ciws_envelopes(self):
        """Assert radar and intercept altitude bounds for air defense and CIWS systems."""
        defense_systems = [w for w in self.catalog.values() if w.category in ("air_defense", "ciws_gun")]
        self.assertGreaterEqual(len(defense_systems), 8)

        for d in defense_systems:
            with self.subTest(defender_id=d.id):
                self.assertIsNotNone(d.radar_range_km, f"{d.id}: radar_range_km must be defined")
                self.assertGreater(d.radar_range_km, 0.0, f"{d.id}: radar_range_km must be > 0")

                self.assertIsNotNone(d.min_intercept_alt_km, f"{d.id}: min_intercept_alt_km must be defined")
                self.assertIsNotNone(d.max_intercept_alt_km, f"{d.id}: max_intercept_alt_km must be defined")
                self.assertGreaterEqual(d.min_intercept_alt_km, 0.0)
                self.assertGreater(d.max_intercept_alt_km, d.min_intercept_alt_km)

    def test_06_helper_get_weapon(self):
        """Verify get_weapon retrieves by ID and tolerates case and dashes."""
        patriot = get_weapon("patriot_pac3_mse")
        self.assertEqual(patriot.id, "patriot_pac3_mse")
        self.assertEqual(patriot.category, "air_defense")

        # Dash normalization test
        atacms = get_weapon("mgm140-atacms")
        self.assertEqual(atacms.id, "mgm140_atacms")

        # Nonexistent weapon raises KeyError
        with self.assertRaises(KeyError):
            get_weapon("nonexistent_death_star_laser")

    def test_07_helper_get_weapons_by_category(self):
        """Verify get_weapons_by_category correctly filters weapons."""
        categories = ["ballistic", "hypersonic", "cruise", "air_defense", "ciws_gun", "drone"]
        for cat in categories:
            weapons = get_weapons_by_category(cat)
            self.assertGreater(len(weapons), 0, f"No weapons found in category '{cat}'")
            for w in weapons:
                self.assertEqual(w.category, cat)

    def test_08_helper_get_weapons_for_role(self):
        """Verify get_weapons_for_role partitions attackers and defenders."""
        attackers = get_weapons_for_role("attacker")
        defenders = get_weapons_for_role("defender")

        self.assertGreater(len(attackers), 10)
        self.assertGreater(len(defenders), 8)

        for a in attackers:
            self.assertTrue(a.is_attacker())
        for d in defenders:
            self.assertTrue(d.is_defender())

        with self.assertRaises(ValueError):
            get_weapons_for_role("invalid_role")

    def test_09_site_templates_validation(self):
        """Verify that all predefined site presets link to valid catalog weapons."""
        self.assertGreaterEqual(len(self.site_templates), 6)

        # Check required site presets mentioned in specifications
        required_preset_names = [
            "Patriot PAC-3 Battery",
            "Iskander-M TEL",
            "Anduril Roadrunner Nest",
            "Shahed-136 Swarm Unit",
            "Phalanx CIWS Point Defense",
            "S-400 Triumf Battery",
        ]

        for p_name in required_preset_names:
            self.assertIn(p_name, self.site_templates, f"Site template preset '{p_name}' not found")

        for name, site in self.site_templates.items():
            with self.subTest(site_name=name):
                # Verify primary weapon
                primary_w = site.get_primary_weapon(self.catalog)
                self.assertIsNotNone(primary_w)
                self.assertEqual(primary_w.id, site.primary_weapon_id)

                # Verify secondary weapon if defined
                if site.secondary_weapon_id:
                    secondary_w = site.get_secondary_weapon(self.catalog)
                    self.assertIsNotNone(secondary_w)
                    self.assertEqual(secondary_w.id, site.secondary_weapon_id)

                self.assertGreater(site.launcher_count, 0)
                self.assertGreater(site.ready_capacity, 0)
                self.assertGreater(site.footprint_radius_km, 0.0)
                self.assertGreaterEqual(len(site.tactical_doctrine), 10)

    def test_10_weapon_behavior_methods(self):
        """Verify methods on the Weapon dataclass (flight time, hypersonic classification)."""
        kinzhal = get_weapon("kh_47m2_kinzhal")
        self.assertTrue(kinzhal.is_hypersonic())

        tomahawk = get_weapon("bgm_109_tomahawk")
        self.assertFalse(tomahawk.is_hypersonic())

        # Flight time for 500 km
        t_sec = tomahawk.flight_time_estimate_sec(500.0)
        self.assertGreater(t_sec, 1000.0)  # ~2300 seconds for subsonic cruise
        self.assertLess(t_sec, 5000.0)

        # Dictionary serialization
        d = tomahawk.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["id"], "bgm_109_tomahawk")


def run_tests():
    """Execute test suite and report results."""
    print("=" * 80)
    print("RUNNING WEAPONS CATALOG VERIFICATION TEST SUITE (test_catalog.py)")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWeaponsCatalog)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 80)
    if result.wasSuccessful():
        print(f"VERIFICATION SUCCESSFUL: All {result.testsRun} tests passed without errors.")
        return 0
    else:
        print(f"VERIFICATION FAILED: {len(result.failures)} failures, {len(result.errors)} errors.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
