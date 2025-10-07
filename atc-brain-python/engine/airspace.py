"""
Airspace sector management for multi-sector ATC operations.
Handles sector detection, boundary checking, and handoff logic.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from .constants import (
    CYYZ_LAT,
    CYYZ_LON,
    SECTOR_ENTRY_INNER_NM,
    SECTOR_ENTRY_OUTER_NM,
    SECTOR_ENROUTE_INNER_NM,
    SECTOR_ENROUTE_OUTER_NM,
    SECTOR_APPROACH_INNER_NM,
    SECTOR_APPROACH_OUTER_NM,
    SECTOR_RUNWAY_INNER_NM,
    SECTOR_RUNWAY_OUTER_NM,
    SECTOR_HYSTERESIS_NM,
)


@dataclass
class SectorDefinition:
    """Airspace sector definition."""
    name: str
    type: str
    radius_nm_inner: float
    radius_nm_outer: float
    altitude_ft_min: float
    altitude_ft_max: float
    controller_hint: str
    hysteresis_nm: float
    behavior: str
    params: Dict[str, Any]


class AirspaceManager:
    """Manages airspace sectors and boundary detection."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.sectors: List[SectorDefinition] = []
        self.entry_fixes: List[Dict[str, Any]] = []
        self.handoff_thresholds: Dict[str, Dict[str, Any]] = {}
        self.spawn_zones: Dict[str, Dict[str, Any]] = {}
        
        self.airport_center = {
            "lat": CYYZ_LAT,
            "lon": CYYZ_LON
        }
        
        # Load configuration
        if config_path:
            self.load_config(config_path)
        else:
            self._load_default_config()
    
    def _load_default_config(self):
        """Load default sector configuration from constants."""
        self.sectors = [
            SectorDefinition(
                name="ENTRY",
                type="ENTRY_EXIT",
                radius_nm_inner=SECTOR_ENTRY_INNER_NM,
                radius_nm_outer=SECTOR_ENTRY_OUTER_NM,
                altitude_ft_min=20000,
                altitude_ft_max=60000,
                controller_hint="ENTRY_ATC",
                hysteresis_nm=SECTOR_HYSTERESIS_NM,
                behavior="random_drift",
                params={}
            ),
            SectorDefinition(
                name="ENROUTE",
                type="ENROUTE",
                radius_nm_inner=SECTOR_ENROUTE_INNER_NM,
                radius_nm_outer=SECTOR_ENROUTE_OUTER_NM,
                altitude_ft_min=18000,
                altitude_ft_max=35000,
                controller_hint="ENROUTE_ATC",
                hysteresis_nm=SECTOR_HYSTERESIS_NM,
                behavior="controlled_descent",
                params={}
            ),
            SectorDefinition(
                name="APPROACH",
                type="APPROACH_DEPARTURE",
                radius_nm_inner=SECTOR_APPROACH_INNER_NM,
                radius_nm_outer=SECTOR_APPROACH_OUTER_NM,
                altitude_ft_min=0,
                altitude_ft_max=18000,
                controller_hint="APPROACH_ATC",
                hysteresis_nm=SECTOR_HYSTERESIS_NM,
                behavior="approach_sequencing",
                params={}
            ),
            SectorDefinition(
                name="RUNWAY",
                type="RUNWAY_OPS",
                radius_nm_inner=SECTOR_RUNWAY_INNER_NM,
                radius_nm_outer=SECTOR_RUNWAY_OUTER_NM,
                altitude_ft_min=0,
                altitude_ft_max=3000,
                controller_hint="TOWER_ATC",
                hysteresis_nm=SECTOR_HYSTERESIS_NM,
                behavior="final_approach",
                params={}
            ),
        ]
    
    def load_config(self, config_path: str) -> bool:
        """
        Load airspace configuration from JSON file.
        
        Args:
            config_path: Path to JSON config file
            
        Returns:
            True if successful
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Load sectors
            self.sectors = []
            for sector_data in config.get("sectors", []):
                sector = SectorDefinition(
                    name=sector_data["name"],
                    type=sector_data["type"],
                    radius_nm_inner=sector_data["radius_nm_inner"],
                    radius_nm_outer=sector_data["radius_nm_outer"],
                    altitude_ft_min=sector_data["altitude_ft_min"],
                    altitude_ft_max=sector_data["altitude_ft_max"],
                    controller_hint=sector_data["controller_hint"],
                    hysteresis_nm=sector_data.get("hysteresis_nm", SECTOR_HYSTERESIS_NM),
                    behavior=sector_data.get("behavior", "controlled"),
                    params=sector_data.get("drift_params", sector_data.get("descent_params", {}))
                )
                self.sectors.append(sector)
            
            # Load entry fixes
            self.entry_fixes = config.get("entry_fixes", [])
            
            # Load handoff thresholds
            self.handoff_thresholds = config.get("handoff_thresholds", {})
            
            # Load spawn zones
            self.spawn_zones = config.get("spawn_zones", {})
            
            # Update airport center if provided
            if "airport" in config and "center" in config["airport"]:
                self.airport_center = config["airport"]["center"]
            
            print(f"✅ Loaded airspace config: {len(self.sectors)} sectors, {len(self.entry_fixes)} entry fixes")
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to load airspace config: {e}")
            print(f"   Using default sector configuration")
            self._load_default_config()
            return False
    
    def get_sector_by_position(self, distance_nm: float, altitude_ft: float) -> Optional[SectorDefinition]:
        """
        Determine sector based on distance and altitude.
        
        Args:
            distance_nm: Distance from airport center (nautical miles)
            altitude_ft: Altitude MSL (feet)
            
        Returns:
            SectorDefinition or None
        """
        # Check sectors from innermost to outermost
        for sector in sorted(self.sectors, key=lambda s: s.radius_nm_inner):
            # Check if within radial bounds
            if sector.radius_nm_inner <= distance_nm <= sector.radius_nm_outer:
                # Check altitude bounds
                if sector.altitude_ft_min <= altitude_ft <= sector.altitude_ft_max:
                    return sector
        
        return None
    
    def check_sector_transition(self, current_sector: str, distance_nm: float, 
                                altitude_ft: float, prev_distance_nm: float) -> Optional[Tuple[str, str]]:
        """
        Check if aircraft should transition to a new sector.
        
        Args:
            current_sector: Current sector name
            distance_nm: Current distance from airport
            altitude_ft: Current altitude MSL
            prev_distance_nm: Previous distance (for inbound check)
            
        Returns:
            Tuple of (from_sector, to_sector) if transition should occur, None otherwise
        """
        new_sector = self.get_sector_by_position(distance_nm, altitude_ft)
        
        if new_sector and new_sector.name != current_sector:
            # Check if moving inbound (distance decreasing)
            is_inbound = distance_nm < prev_distance_nm
            
            # Require inbound movement for handoffs (arrivals)
            if is_inbound:
                return (current_sector, new_sector.name)
        
        return None
    
    def is_at_outer_boundary(self, sector_name: str, distance_nm: float) -> bool:
        """
        Check if aircraft is at outer boundary of sector.
        
        Args:
            sector_name: Sector name
            distance_nm: Distance from airport
            
        Returns:
            True if at or beyond outer boundary
        """
        sector = self.get_sector_by_name(sector_name)
        if sector:
            return distance_nm >= sector.radius_nm_outer - sector.hysteresis_nm
        return False
    
    def get_sector_by_name(self, name: str) -> Optional[SectorDefinition]:
        """Get sector definition by name."""
        for sector in self.sectors:
            if sector.name == name:
                return sector
        return None
    
    def get_nearest_entry_fix(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Find nearest entry fix to given position.
        
        Args:
            lat, lon: Position coordinates
            
        Returns:
            Entry fix dict or None
        """
        from .geo_utils import flat_earth_distance
        
        if not self.entry_fixes:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for fix in self.entry_fixes:
            distance = flat_earth_distance(lat, lon, fix["lat"], fix["lon"])
            if distance < min_distance:
                min_distance = distance
                nearest = fix
        
        return nearest
    
    def calculate_reflection_heading(self, current_heading: float, 
                                     bearing_to_center: float) -> float:
        """
        Calculate reflected heading when bouncing off outer boundary.
        
        Args:
            current_heading: Current aircraft heading (degrees)
            bearing_to_center: Bearing to airport center (degrees)
            
        Returns:
            New reflected heading (degrees)
        """
        import random
        
        # Reflect heading toward center with some randomness
        # Target heading is roughly toward center ± 20 degrees
        base_reflection = bearing_to_center
        randomness = random.uniform(-20, 20)
        
        new_heading = (base_reflection + randomness) % 360
        return new_heading
    
    def get_spawn_zone(self, flight_type: str = "ARRIVAL") -> Dict[str, Any]:
        """
        Get spawn zone parameters for flight type.
        
        Args:
            flight_type: 'ARRIVAL' or 'DEPARTURE'
            
        Returns:
            Spawn zone configuration dict
        """
        key = "arrivals" if flight_type == "ARRIVAL" else "departures"
        
        if key in self.spawn_zones:
            return self.spawn_zones[key]
        
        # Default spawn zone for arrivals
        return {
            "sector": "ENTRY",
            "radius_nm_min": 40.0,
            "radius_nm_max": 60.0,
            "altitude_ft_min": 25000,
            "altitude_ft_max": 35000,
            "speed_kts_min": 280,
            "speed_kts_max": 350,
            "random_bearing": True
        }
    
    def __repr__(self) -> str:
        return f"AirspaceManager(sectors={len(self.sectors)}, entry_fixes={len(self.entry_fixes)})"


# Global airspace manager instance
_airspace_manager: Optional[AirspaceManager] = None


def get_airspace_manager(config_path: Optional[str] = None, reload: bool = False) -> AirspaceManager:
    """
    Get or create global airspace manager instance.
    
    Args:
        config_path: Path to airspace config JSON (optional)
        reload: Force reload from disk
        
    Returns:
        AirspaceManager instance
    """
    global _airspace_manager
    
    if _airspace_manager is None or reload:
        # Try to load from default location if no path provided
        if config_path is None:
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "airspace",
                "yyz_sectors.json"
            )
            if os.path.exists(default_path):
                config_path = default_path
        
        _airspace_manager = AirspaceManager(config_path)
    
    return _airspace_manager

