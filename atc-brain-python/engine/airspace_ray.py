"""
Ray distributed wrappers for CPU-intensive airspace functions.
These functions execute on remote Ray cluster nodes.
"""

import ray
from typing import Dict, Any, List, Tuple, Optional
from .airspace import AirspaceManager


@ray.remote
class DistributedAirspaceManager:
    """
    Ray Actor for distributed airspace operations.
    Handles sector detection, conflict checking, and separation monitoring.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize distributed airspace manager.
        
        Args:
            config_path: Path to airspace configuration file
        """
        self.manager = AirspaceManager(config_path)
    
    def get_sector_by_position(self, distance_nm: float, altitude_ft: float):
        """Get sector for given position."""
        sector = self.manager.get_sector_by_position(distance_nm, altitude_ft)
        return sector.name if sector else None
    
    def check_sector_transitions_batch(self, aircraft_data: List[Tuple[str, float, float, float]]):
        """
        Check sector transitions for multiple aircraft.
        
        Args:
            aircraft_data: List of tuples (current_sector, distance_nm, altitude_ft, prev_distance_nm)
        
        Returns:
            List of transition tuples or None for each aircraft
        """
        results = []
        for current_sector, distance_nm, altitude_ft, prev_distance_nm in aircraft_data:
            transition = self.manager.check_sector_transition(
                current_sector, distance_nm, altitude_ft, prev_distance_nm
            )
            results.append(transition)
        return results


@ray.remote
def detect_conflicts_batch(aircraft_list: List[Dict[str, Any]], 
                          separation_min_nm: float = 5.0,
                          vertical_sep_ft: float = 1000.0) -> List[Tuple[str, str, float]]:
    """
    Detect conflicts between aircraft in a batch.
    CPU-intensive pairwise distance and separation checking.
    
    Args:
        aircraft_list: List of aircraft state dictionaries
        separation_min_nm: Minimum horizontal separation (nautical miles)
        vertical_sep_ft: Minimum vertical separation (feet)
    
    Returns:
        List of conflict tuples: (callsign1, callsign2, separation_nm)
    """
    from .geo_utils import flat_earth_distance
    
    conflicts = []
    n = len(aircraft_list)
    
    # O(n²) pairwise conflict detection
    for i in range(n):
        for j in range(i + 1, n):
            ac1 = aircraft_list[i]
            ac2 = aircraft_list[j]
            
            pos1 = ac1.get("position", {})
            pos2 = ac2.get("position", {})
            
            # Calculate horizontal separation
            horiz_sep_nm = flat_earth_distance(
                pos1.get("lat", 0.0), pos1.get("lon", 0.0),
                pos2.get("lat", 0.0), pos2.get("lon", 0.0)
            )
            
            # Calculate vertical separation
            vert_sep_ft = abs(pos1.get("altitude_ft", 0.0) - pos2.get("altitude_ft", 0.0))
            
            # Check if conflict exists
            if horiz_sep_nm < separation_min_nm and vert_sep_ft < vertical_sep_ft:
                conflicts.append((
                    ac1.get("callsign", "UNKNOWN"),
                    ac2.get("callsign", "UNKNOWN"),
                    horiz_sep_nm
                ))
    
    return conflicts


@ray.remote
def calculate_separation_matrix_remote(aircraft_list: List[Dict[str, Any]]) -> List[List[float]]:
    """
    Calculate full separation matrix for all aircraft pairs.
    Very CPU-intensive for large aircraft counts.
    
    Args:
        aircraft_list: List of aircraft state dictionaries
    
    Returns:
        2D matrix of separation distances (nautical miles)
    """
    from .geo_utils import flat_earth_distance
    
    n = len(aircraft_list)
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            pos1 = aircraft_list[i].get("position", {})
            pos2 = aircraft_list[j].get("position", {})
            
            distance = flat_earth_distance(
                pos1.get("lat", 0.0), pos1.get("lon", 0.0),
                pos2.get("lat", 0.0), pos2.get("lon", 0.0)
            )
            
            matrix[i][j] = distance
            matrix[j][i] = distance
    
    return matrix

