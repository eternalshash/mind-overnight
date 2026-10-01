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


def get_site_templates() -> Dict[str, SiteTemplate]:
    """
    Returns verified unit preset templates for theater air defense batteries,
    ballistic launcher batteries, loitering drone swarms, and CIWS point defense stations.
    
    Returns:
        Dict mapping template name to SiteTemplate dataclass.
    """
    templates = [
        SiteTemplate(
            name="Patriot PAC-3 Battery",
            preset_id="patriot_pac3_battery",
            role="defender",
            category="air_defense",
            primary_weapon_id="patriot_pac3_mse",
            secondary_weapon_id="phalanx_lpws",
            launcher_count=6,
            ready_capacity=96,  # 6 launchers x 16 PAC-3 MSE missiles
            radar_system="AN/MPQ-65A / LTAMDS 360-degree AESA Phased Array Radar",
            c2_system="AN/MSQ-104 Engagement Control Station (ECS)",
            footprint_radius_km=15.0,
            description="U.S. Army theater lower-tier IAMD battery providing hit-to-kill terminal defense against ballistic missiles, cruise missiles, and combat aircraft.",
            tactical_doctrine="Shoot-Look-Shoot or 2-interceptor salvo per inbound high-threat ballistic track with integrated Phalanx CIWS point-defense escort."
        ),
        SiteTemplate(
            name="Iskander-M TEL",
            preset_id="iskander_m_tel_division",
            role="attacker",
            category="ballistic",
            primary_weapon_id="iskander_m",
            secondary_weapon_id=None,
            launcher_count=4,
            ready_capacity=8,  # 4 TELs x 2 ready missiles each
            radar_system=None,
            c2_system="9S552 Command and Staff Vehicle with GLONASS datalink",
            footprint_radius_km=8.0,
            description="Road-mobile 9P78-1 Transporter-Erector-Launcher (TEL) battery firing 9M723 quasi-ballistic missiles with high-G terminal evasion and active decoys.",
            tactical_doctrine="Rapid deploy-shoot-scoot maneuver: release dual-missile salvo within 4 minutes and relocate to concealed reload coordinates."
        ),
        SiteTemplate(
            name="Anduril Roadrunner Nest",
            preset_id="anduril_roadrunner_nest",
            role="defender",
            category="drone",
            primary_weapon_id="anduril_roadrunner_m",
            secondary_weapon_id="anduril_roadrunner",
            launcher_count=12,
            ready_capacity=12,
            radar_system="Lattice Multi-Sensor Edge Fusion (integrated optical, RF, and 3D radar feed)",
            c2_system="Anduril Lattice OS Autonomous Command & Control",
            footprint_radius_km=5.0,
            description="Automated Nest hangar complex housing high-G twin-turbojet VTOL Roadrunner-M interceptors for autonomous point and base defense against drone swarms and cruise missiles.",
            tactical_doctrine="Autonomous rapid scramble on radar detection; high-speed intercept and engagement; autonomous return-to-base and vertical landing if target neutralized by other tiers."
        ),
        SiteTemplate(
            name="Shahed-136 Swarm Unit",
            preset_id="shahed_136_swarm_unit",
            role="attacker",
            category="drone",
            primary_weapon_id="shahed_136",
            secondary_weapon_id=None,
            launcher_count=4,
            ready_capacity=20,  # 4 concealed flatbed truck racks x 5-cell launch container
            radar_system=None,
            c2_system="Pre-programmed multi-waypoint GNSS mission computer with terrain masking",
            footprint_radius_km=10.0,
            description="Mobile containerized salvo launcher disguised on commercial flatbed trucks, firing coordinated saturation waves of low-cost delta-wing loitering drones.",
            tactical_doctrine="Time-on-Target (TOT) simultaneous saturation salvos designed to deplete defender missile stocks and overwhelm radar tracking pipelines."
        ),
        SiteTemplate(
            name="Phalanx CIWS Point Defense",
            preset_id="phalanx_ciws_point_defense",
            role="defender",
            category="ciws_gun",
            primary_weapon_id="phalanx_lpws",
            secondary_weapon_id=None,
            launcher_count=4,
            ready_capacity=6000,  # 4 mounts x 1,500 rounds ready-to-fire 20mm HEIT-SD
            radar_system="Integrated Ku-band Pulse Doppler Search & Track Radar per mount",
            c2_system="Centurion Local Fire Control System with automatic FLIR target tracking",
            footprint_radius_km=2.0,
            description="Last-ditch inner ring perimeter defense consisting of four 20mm Gatling rotary cannons firing 4,500 rpm self-destructing ammunition to defeat penetrating munitions.",
            tactical_doctrine="Autonomous engagement of low-altitude threats breaching missile envelopes with high-density 75-100 round bursts."
        ),
        SiteTemplate(
            name="S-400 Triumf Battery",
            preset_id="s400_triumf_battery",
            role="defender",
            category="air_defense",
            primary_weapon_id="s400_48n6dm",
            secondary_weapon_id="flakpanzer_gepard",
            launcher_count=8,
            ready_capacity=32,  # 8 TELs x 4 canisters
            radar_system="91N6E Big Bird Panoramic Surveillance Radar + 92N6E Grave Stone Engagement Radar",
            c2_system="54K6E Command Post Vehicle",
            footprint_radius_km=25.0,
            description="Russian long-range mobile surface-to-air missile division capable of simultaneous multi-target engagement up to 250 km downrange.",
            tactical_doctrine="Multi-missile track-via-missile (TVM) engagement of high-altitude stealth and aerodynamic threats paired with close-in SPAAG escorts."
        ),
        SiteTemplate(
            name="THAAD Battery",
            preset_id="thaad_battery",
            role="defender",
            category="air_defense",
            primary_weapon_id="thaad",
            secondary_weapon_id=None,
            launcher_count=6,
            ready_capacity=48,  # 6 TELs x 8 missiles
            radar_system="AN/TPY-2 Forward-Based / Terminal X-Band Phased Array Radar",
            c2_system="THAAD Fire Control and Communications (TFCC) Tactical Operations Station",
            footprint_radius_km=30.0,
            description="Upper-tier theater missile defense battery providing wide-area exo- and endo-atmospheric terminal interception against ballistic threats.",
            tactical_doctrine="Layered upper-tier handoff to Patriot PAC-3 lower-tier batteries; pure kinetic hit-to-kill interception above 40 km altitude."
        ),
        SiteTemplate(
            name="Aegis Ashore / BMD Destroyer",
            preset_id="aegis_ashore_bmd",
            role="defender",
            category="air_defense",
            primary_weapon_id="sm3_block_iia",
            secondary_weapon_id="patriot_pac3_mse",
            launcher_count=24,
            ready_capacity=24,  # 24 Mk 41 VLS cells allocated for SM-3
            radar_system="AN/SPY-1D(V) / AN/SPY-6(V)1 Air and Missile Defense Radar (AMDR)",
            c2_system="Aegis Weapon System Baseline 9/10 Command & Decision",
            footprint_radius_km=50.0,
            description="Land-based Aegis Ashore installation or Arleigh Burke Flight III guided-missile destroyer equipped with SM-3 Block IIA exo-atmospheric interceptors.",
            tactical_doctrine="Exo-atmospheric midcourse ballistic missile interception against intermediate-range and ICBM threats before reentry."
        ),
        SiteTemplate(
            name="Iron Dome Mobile Battery",
            preset_id="iron_dome_battery",
            role="defender",
            category="air_defense",
            primary_weapon_id="iron_dome_tamir",
            secondary_weapon_id=None,
            launcher_count=4,
            ready_capacity=80,  # 4 launchers x 20 Tamir missiles
            radar_system="EL/M-2084 Multi-Mission S-band Active Electronically Scanned Array (AESA)",
            c2_system="Battle Management & Weapon Control (BMC) unit",
            footprint_radius_km=12.0,
            description="Highly mobile tactical defense system countering unguided artillery, mortar, drone swarms, and low-altitude cruise missiles with selective trajectory threat filtering.",
            tactical_doctrine="Autonomous impact-point prediction: only threats calculated to impact within protected asset polygons are engaged, conserving interceptor stocks."
        ),
        SiteTemplate(
            name="Skynex Air Defense Battery",
            preset_id="skynex_air_defense_battery",
            role="defender",
            category="ciws_gun",
            primary_weapon_id="skynex_35mm",
            secondary_weapon_id=None,
            launcher_count=4,
            ready_capacity=1000,  # 4 Revolver Gun Mk3 mounts x 250 ready rounds
            radar_system="Oerlikon X-TAR3D Tactical Acquisition 3D Radar",
            c2_system="Oerlikon Skymaster Command & Control System",
            footprint_radius_km=4.5,
            description="Networked short-range air defense battery employing 35mm AHEAD programmable airburst ammunition to form lethal tungsten fragment clouds against swarms and cruise missiles.",
            tactical_doctrine="Time-fused inductive muzzle programming ejecting 152 sub-projectiles per shell directly into threat flight path at 1,000 rpm."
        ),
        SiteTemplate(
            name="Flakpanzer Gepard Air Defense Platoon",
            preset_id="gepard_air_defense_platoon",
            role="defender",
            category="ciws_gun",
            primary_weapon_id="flakpanzer_gepard",
            secondary_weapon_id=None,
            launcher_count=4,
            ready_capacity=2560,  # 4 tracked vehicles x 640 rounds 35mm
            radar_system="Integrated onboard S-band search radar (15 km) and Ku-band tracking radar",
            c2_system="Gepard Autonomous Fire-Control Computer with optical aiming back-up",
            footprint_radius_km=6.0,
            description="Mobile armored all-weather air defense platoon protecting maneuvering mechanized units against low-flying subsonic cruise missiles and loitering munitions.",
            tactical_doctrine="High-mobility convoy escort and forward area defense utilizing frangible armor-piercing discarding sabot (FAPDS) ammunition."
        ),
        SiteTemplate(
            name="Anduril Barracuda Swarm Cell",
            preset_id="anduril_barracuda_swarm_cell",
            role="attacker",
            category="cruise",
            primary_weapon_id="anduril_barracuda_500",
            secondary_weapon_id="anduril_barracuda_100",
            launcher_count=6,
            ready_capacity=24,  # Palletized Rapid Dragon or mobile container launchers
            radar_system=None,
            c2_system="Anduril Lattice Collaborative Autonomous Swarm Tasking",
            footprint_radius_km=15.0,
            description="Deployable standoff strike cell launching mass Autonomous Air Vehicles (AAVs) for long-range theater strike and saturation of enemy integrated air defense grids.",
            tactical_doctrine="Autonomous cooperative routing, synchronized multi-axis convergence, and decoy/strike payload pairing."
        ),
        SiteTemplate(
            name="ATACMS / HIMARS Fire Platoon",
            preset_id="atacms_himars_platoon",
            role="attacker",
            category="ballistic",
            primary_weapon_id="mgm140_atacms",
            secondary_weapon_id=None,
            launcher_count=4,
            ready_capacity=4,  # 4 M142 HIMARS launchers x 1 ATACMS pod each
            radar_system=None,
            c2_system="Advanced Field Artillery Tactical Data System (AFATDS)",
            footprint_radius_km=10.0,
            description="High-mobility rocket artillery platoon firing precision MGM-140 ATACMS missiles for deep-strike counter-battery and command-node interdiction.",
            tactical_doctrine="Dispersed rapid positioning, instant digital target package upload, single-missile launch, and 2-minute egress before counter-battery detection."
        ),
    ]

    return {t.name: t for t in templates}


def get_site_template(template_name: str) -> SiteTemplate:
    """
    Retrieve a specific site template preset by name or preset_id.
    
    Args:
        template_name: Template identifier (e.g. 'Patriot PAC-3 Battery', 'patriot_pac3_battery').
        
    Returns:
        SiteTemplate dataclass instance.
    """
    templates = get_site_templates()
    if template_name in templates:
        return templates[template_name]

    # Search by normalized preset_id
    norm_search = template_name.strip().lower().replace("-", "_")
    for t in templates.values():
        if t.preset_id == norm_search or t.name.lower().replace("-", "_") == norm_search:
            return t

    raise KeyError(f"Site template '{template_name}' not found. Available presets: {list(templates.keys())}")


def get_all_categories() -> List[str]:
    """Returns list of distinct weapon categories in the catalog."""
    catalog = load_catalog()
    unique = catalog.unique_weapons() if hasattr(catalog, "unique_weapons") else list(set(catalog.values()))
    return sorted(list(set(w.category for w in unique)))


def print_catalog_summary(catalog_path: Optional[Union[str, Path]] = None) -> None:
    """Prints a structured summary of the weapons catalog to stdout."""
    catalog = load_catalog(catalog_path)
    unique_weapons = catalog.unique_weapons() if hasattr(catalog, "unique_weapons") else list(set(catalog.values()))
    categories = get_all_categories()
    templates = get_site_templates()

    print("=" * 85)
    print(f"WEAPONS CATALOG SUMMARY: {len(unique_weapons)} UNIQUE REGISTERED WEAPON SYSTEMS")
    print("=" * 85)

    for cat in categories:
        weapons_in_cat = [w for w in unique_weapons if w.category == cat]
        print(f"\n[{cat.upper()}] ({len(weapons_in_cat)} systems):")
        for w in weapons_in_cat:
            envelope = f"Range: {w.range_km:.0f} km | Speed: Mach {w.max_speed_mach:.1f} ({w.max_speed_kmh:.0f} km/h)"
            if w.radar_range_km:
                envelope += f" | Radar: {w.radar_range_km:.0f} km"
            print(f"  * {w.id:24s} | {w.name:42s} | {envelope}")

    print("\n" + "=" * 85)
    print(f"FORCE SITE TEMPLATES: {len(templates)} PRECONFIGURED COMBAT PRESETS")
    print("=" * 85)
    for name, t in templates.items():
        print(f"  * {t.name:32s} [{t.role.upper():9s}] | Primary: {t.primary_weapon_id:22s} | Ready Cap: {t.ready_capacity:4d} units")
    print("=" * 85)


if __name__ == "__main__":
    print_catalog_summary()
