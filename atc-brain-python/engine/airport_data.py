"""
Airport reference data loader.
Loads airport coordinates, runways, and entry waypoints from JSON.
"""

import json
import os
from typing import Dict, List, Any, Optional
from .constants import CYYZ_LAT, CYYZ_LON, CYYZ_ELEVATION_FT


class AirportData:
    """Airport reference data container."""
    
    def __init__(self, icao: str = "CYYZ"):
        self.icao = icao
        self.lat = CYYZ_LAT
        self.lon = CYYZ_LON
        self.elevation_ft = CYYZ_ELEVATION_FT
        self.runways: List[Dict[str, Any]] = []
        self.entry_waypoints: List[Dict[str, Any]] = []
        self.loaded = False
    
    def load_from_json(self, json_path: Optional[str] = None) -> bool:
        """
        Load airport data from GeoJSON file.
        
        Args:
            json_path: Path to JSON file (optional, uses env var if not provided)
        
        Returns:
            True if successful, False otherwise
        """
        if json_path is None:
            json_path = os.getenv("AIRPORT_DATA_PATH", "../atc-nextjs/src/data/cyyz-airport.json")
        
        # Resolve relative path from project root
        if not os.path.isabs(json_path):
            # Get project root (parent of atc-brain-python)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_path = os.path.join(project_root, json_path)
        else:
            full_path = json_path
        
        try:
            with open(full_path, 'r') as f:
                data = json.load(f)
            
            # Extract runway data from GeoJSON
            if data.get("type") == "FeatureCollection":
                features = data.get("features", [])
                
                for feature in features:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    
                    if props.get("aeroway") == "runway":
                        runway_info = {
                            "name": props.get("name", "Unknown"),
                            "ref": props.get("ref", ""),
                            "length": props.get("length"),
                            "width": props.get("width"),
                            "coordinates": geom.get("coordinates", [])
                        }
                        self.runways.append(runway_info)
            
            self.loaded = True
            return True
            
        except FileNotFoundError:
            print(f"⚠️  Airport data file not found: {full_path}")
            print(f"   Using default CYYZ coordinates")
            return False
        except json.JSONDecodeError as e:
            print(f"⚠️  Error parsing airport JSON: {e}")
            return False
        except Exception as e:
            print(f"⚠️  Error loading airport data: {e}")
            return False
    
    def generate_entry_waypoints(self, radius_nm: float = 30.0, count: int = 8) -> List[Dict[str, Any]]:
        """
        Generate entry waypoints in a ring around the airport.
        
        Args:
            radius_nm: Distance from airport (nautical miles)
            count: Number of waypoints to generate
        
        Returns:
            List of waypoint dictionaries with name, lat, lon
        """
        import math
        from .geo_utils import NM_PER_DEGREE_LAT
        
        waypoints = []
        
        # Cardinal and intercardinal directions
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        
        for i in range(count):
            # Calculate bearing (0° = North, clockwise)
            bearing_deg = (360.0 / count) * i
            bearing_rad = math.radians(bearing_deg)
            
            # Calculate offset in degrees
            delta_lat = (radius_nm / NM_PER_DEGREE_LAT) * math.cos(bearing_rad)
            delta_lon = (radius_nm / (NM_PER_DEGREE_LAT * math.cos(math.radians(self.lat)))) * math.sin(bearing_rad)
            
            waypoint = {
                "name": f"{self.icao}_{directions[i % len(directions)]}{int(radius_nm)}",
                "lat": self.lat + delta_lat,
                "lon": self.lon + delta_lon,
                "bearing": bearing_deg,
                "distance_nm": radius_nm
            }
            waypoints.append(waypoint)
        
        self.entry_waypoints = waypoints
        return waypoints
    
    def get_nearest_entry_waypoint(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Find nearest entry waypoint to given position.
        
        Args:
            lat, lon: Position to check
        
        Returns:
            Nearest waypoint dict or None
        """
        if not self.entry_waypoints:
            self.generate_entry_waypoints()
        
        from .geo_utils import distance_to_airport
        
        nearest = None
        min_distance = float('inf')
        
        for waypoint in self.entry_waypoints:
            distance = distance_to_airport(lat, lon, waypoint["lat"], waypoint["lon"])
            if distance < min_distance:
                min_distance = distance
                nearest = waypoint
        
        return nearest
    
    def get_runway_heading(self, runway_name: str) -> Optional[float]:
        """
        Get magnetic heading for a runway.
        
        Args:
            runway_name: Runway identifier (e.g., "05L", "23R")
        
        Returns:
            Magnetic heading in degrees or None
        """
        # Extract runway number from name (e.g., "05L" -> 05)
        runway_num = ''.join(filter(str.isdigit, runway_name))
        
        if runway_num:
            try:
                # Runway number * 10 = magnetic heading
                heading = int(runway_num) * 10
                return float(heading)
            except ValueError:
                pass
        
        return None
    
    def __repr__(self) -> str:
        return (f"AirportData(icao={self.icao}, lat={self.lat:.4f}, lon={self.lon:.4f}, "
                f"runways={len(self.runways)}, loaded={self.loaded})")


# Global airport instance
_airport: Optional[AirportData] = None


def get_airport_data(icao: str = "CYYZ", reload: bool = False) -> AirportData:
    """
    Get or create global airport data instance.
    
    Args:
        icao: Airport ICAO code
        reload: Force reload from disk
    
    Returns:
        AirportData instance
    """
    global _airport
    
    if _airport is None or reload:
        _airport = AirportData(icao)
        _airport.load_from_json()
        _airport.generate_entry_waypoints()
    
    return _airport

