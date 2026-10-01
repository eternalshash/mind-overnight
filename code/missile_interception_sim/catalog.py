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


def load_catalog(
    catalog_path: Optional[Union[str, Path]] = None,
    reload: bool = False
) -> WeaponCatalog:
    """
    Load and parse the verified weapons catalog from JSON into strongly typed Weapon objects.
    Both canonical IDs and common aliases are registered for fast lookup.
    
    Args:
        catalog_path: Custom path to weapons_catalog.json (defaults to standard repo path).
        reload: Force reload from disk, bypassing memory cache.
        
    Returns:
        WeaponCatalog mapping weapon IDs and aliases to Weapon instances.
    """
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None and not reload and catalog_path is None:
        return _CATALOG_CACHE

    target_path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Weapons catalog file not found at: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    catalog = WeaponCatalog()
    for item in data.get("weapons", []):
        cat = item["category"]
        role = item.get("role")
        if not role:
            if cat in ("air_defense", "ciws_gun"):
                role = "defender"
            elif item["id"] == "anduril_roadrunner_m":
                role = "defender"
            elif item["id"] in ("anduril_roadrunner", "anduril_altius_600", "anduril_altius_700", "anduril_bolt"):
                role = "dual_role"
            else:
                role = "attacker"

        w = Weapon(
            id=item["id"],
            name=item["name"],
            category=cat,
            role=role,
            manufacturer=item["manufacturer"],
            country=item["country"],
            range_km=float(item["range_km"]),
            max_speed_mach=float(item["max_speed_mach"]),
            max_speed_kmh=float(item["max_speed_kmh"]),
            apogee_km=float(item["apogee_km"]) if item.get("apogee_km") is not None else None,
            cruise_alt_m=float(item["cruise_alt_m"]) if item.get("cruise_alt_m") is not None else None,
            flight_profile=item["flight_profile"],
            guidance=item["guidance"],
            warhead_type=item["warhead_type"],
            warhead_mass_kg=float(item["warhead_mass_kg"]),
            radar_range_km=float(item["radar_range_km"]) if item.get("radar_range_km") is not None else None,
            min_intercept_alt_km=float(item["min_intercept_alt_km"]) if item.get("min_intercept_alt_km") is not None else None,
            max_intercept_alt_km=float(item["max_intercept_alt_km"]) if item.get("max_intercept_alt_km") is not None else None,
            pk_baseline=float(item["pk_baseline"]),
            sourcing_url=item["sourcing_url"],
            description=item["description"],
            aliases=item.get("aliases", []),
        )
        catalog.register_weapon(w)

    if catalog_path is None:
        _CATALOG_CACHE = catalog

    return catalog


def get_weapon(
    weapon_id: str,
    catalog_path: Optional[Union[str, Path]] = None,
    catalog: Optional[Dict[str, Weapon]] = None
) -> Weapon:
    """
    Retrieve a specific weapon system by its unique ID or registered alias.
    Performs case-insensitive matching and normalization of dashes to underscores.
    
    Args:
        weapon_id: System identifier (e.g., 'patriot_pac3_mse', 'df-17', 'iskander_m', 'atacms').
        catalog_path: Optional path to custom JSON catalog.
        catalog: Optional preloaded catalog dict.
        
    Returns:
        Weapon dataclass instance.
        
    Raises:
        KeyError: If weapon ID is not registered in the catalog.
    """
    if catalog is None:
        cat_obj = load_catalog(catalog_path)
    else:
        cat_obj = catalog

    norm_id = weapon_id.strip().lower().replace("-", "_")

    if norm_id in cat_obj:
        return cat_obj[norm_id]

    # Secondary fuzzy check against weapon names and aliases
    for w in cat_obj.values():
        if norm_id == w.name.lower().replace("-", "_"):
            return w
        for a in w.aliases:
            if norm_id == a.lower().replace("-", "_"):
                return w

    raise KeyError(f"Weapon '{weapon_id}' not found in weapons catalog. Available IDs: {list(cat_obj.keys())}")


def get_weapons_by_category(category: str, catalog_path: Optional[Union[str, Path]] = None) -> List[Weapon]:
    """
    Filter registered unique weapons by operational category.
    
    Args:
        category: One of 'ballistic', 'hypersonic', 'cruise', 'air_defense', 'ciws_gun', 'drone'.
        
    Returns:
        List of matching Weapon objects.
    """
    catalog = load_catalog(catalog_path)
    cat_norm = category.strip().lower()
    unique = catalog.unique_weapons() if hasattr(catalog, "unique_weapons") else list(set(catalog.values()))
    return [w for w in unique if w.category.lower() == cat_norm]


def get_weapons_for_role(role: str = "attacker", catalog_path: Optional[Union[str, Path]] = None) -> List[Weapon]:
    """
    Filter registered unique weapons by combat role.
    
    Args:
        role: 'attacker' (strike/offensive systems), 'defender' (air defense/CIWS/C-UAS), or 'dual_role'.
        
    Returns:
        List of matching Weapon objects.
    """
    catalog = load_catalog(catalog_path)
    role_norm = role.strip().lower()
    unique = catalog.unique_weapons() if hasattr(catalog, "unique_weapons") else list(set(catalog.values()))

    if role_norm == "attacker":
        return [w for w in unique if w.is_attacker()]
    elif role_norm == "defender":
        return [w for w in unique if w.is_defender()]
    elif role_norm == "dual_role":
        return [w for w in unique if w.role == "dual_role"]
    else:
        raise ValueError(f"Unknown role '{role}'. Expected 'attacker', 'defender', or 'dual_role'.")

