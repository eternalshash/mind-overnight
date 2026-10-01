#!/usr/bin/env python3
"""
================================================================================
WEAPONS CATALOG AND THEATER FORCE PRESET MODULE
Missile Interception Simulation Architecture
================================================================================
Provides parsed real-world technical specifications, operational envelopes,
radar suites, hit-to-kill kinetic parameters, baseline single-shot kill
probabilities (Pk), and validated site presets for:
- Ballistic Missiles (ATACMS, Iskander-M, DF-21D, Minuteman III, RS-28 Sarmat)
- Hypersonic Weapons (DF-17 HGV, Kinzhal, 3M22 Zircon, AGM-183A ARRW)
- Cruise Missiles (Tomahawk, Kalibr, Storm Shadow, BrahMos)
- Air Defense Systems (Patriot PAC-3 MSE, THAAD, SM-3 Block IIA, Iron Dome, S-400)
- Anti-Air Guns / CIWS (Phalanx 20mm LPWS, Flakpanzer Gepard, Skynex 35mm AHEAD)
- Drones & Loitering Munitions (Anduril Roadrunner/Roadrunner-M, ALTIUS-600/700/700M,
  Barracuda-100/250/500, Bolt/Bolt-M, Shahed-136, Lancet-3, Switchblade 600)
================================================================================
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Union, Set
from pathlib import Path
import json
import os

# Default catalog path relative to this script
DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent / "weapons_catalog.json"


@dataclass
class Weapon:
    """Represents a verified weapon system and its complete physical/operational envelope."""
    id: str
    name: str
    category: str  # "ballistic", "hypersonic", "cruise", "air_defense", "ciws_gun", "drone"
    role: str      # "attacker", "defender", "dual_role"
    manufacturer: str
    country: str
    range_km: float
    max_speed_mach: float
    max_speed_kmh: float
    apogee_km: Optional[float]
    cruise_alt_m: Optional[float]
    flight_profile: str
    guidance: str
    warhead_type: str
    warhead_mass_kg: float
    radar_range_km: Optional[float]
    min_intercept_alt_km: Optional[float]
    max_intercept_alt_km: Optional[float]
    pk_baseline: float
    sourcing_url: str
    description: str
    aliases: List[str] = field(default_factory=list)

    def is_attacker(self) -> bool:
        """Check if weapon is an offensive strike munition or multi-mission asset."""
        return self.role in ("attacker", "dual_role")

    def is_defender(self) -> bool:
        """Check if weapon is an air defense interceptor, CIWS gun, or C-UAS platform."""
        return self.role in ("defender", "dual_role") or self.category in ("air_defense", "ciws_gun")

    def is_hypersonic(self) -> bool:
        """Check if weapon operates at hypersonic velocities (Mach >= 5.0)."""
        return self.max_speed_mach >= 5.0 or self.category == "hypersonic"

    def flight_time_estimate_sec(self, distance_km: float) -> float:
        """
        Estimate mean transit time in seconds assuming average cruise velocity
        at 85% of peak mach speed.
        """
        avg_speed_km_s = (self.max_speed_kmh * 0.85) / 3600.0
        return distance_km / max(avg_speed_km_s, 0.01)

    def to_dict(self) -> Dict[str, Any]:
        """Convert weapon instance to Python dictionary."""
        return asdict(self)


@dataclass
class SiteTemplate:
    """Preconfigured battery, TEL, station, or swarm unit preset."""
    name: str
    preset_id: str
    role: str  # "attacker" or "defender"
    category: str
    primary_weapon_id: str
    secondary_weapon_id: Optional[str]
    launcher_count: int
    ready_capacity: int
    radar_system: Optional[str]
    c2_system: Optional[str]
    footprint_radius_km: float
    description: str
    tactical_doctrine: str

    def get_primary_weapon(self, catalog: Optional[Dict[str, Weapon]] = None) -> Weapon:
        """Retrieve the primary weapon object associated with this site template."""
        if catalog is None:
            catalog = load_catalog()
        return get_weapon(self.primary_weapon_id, catalog=catalog)

    def get_secondary_weapon(self, catalog: Optional[Dict[str, Weapon]] = None) -> Optional[Weapon]:
        """Retrieve secondary weapon object if assigned."""
        if not self.secondary_weapon_id:
            return None
        if catalog is None:
            catalog = load_catalog()
        return get_weapon(self.secondary_weapon_id, catalog=catalog)

    def to_dict(self) -> Dict[str, Any]:
        """Convert site template instance to dictionary."""
        return asdict(self)


class WeaponCatalog(dict):
    """
    Enhanced dictionary container for weapon systems supporting alias lookup,
    case normalization, and unique system iteration.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._primary_map: Dict[str, Weapon] = {}
        self._alias_map: Dict[str, str] = {}

    def register_weapon(self, weapon: Weapon) -> None:
        """Register weapon under primary ID and all aliases."""
        norm_id = weapon.id.strip().lower().replace("-", "_")
        self[norm_id] = weapon
        self._primary_map[norm_id] = weapon

        for alias in weapon.aliases:
            norm_alias = alias.strip().lower().replace("-", "_")
            self[norm_alias] = weapon
            self._alias_map[norm_alias] = norm_id

    def unique_weapons(self) -> List[Weapon]:
        """Returns list of distinct Weapon objects (excluding duplicate alias keys)."""
        return list(self._primary_map.values())

    def get_unique_count(self) -> int:
        """Returns count of unique weapon systems."""
        return len(self._primary_map)


# Module-level cache for loaded catalog
_CATALOG_CACHE: Optional[WeaponCatalog] = None

