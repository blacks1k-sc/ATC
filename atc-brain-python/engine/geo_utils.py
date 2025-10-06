"""
Geographic utility functions for coordinate conversion and distance calculations.
Uses small-step Earth approximation suitable for ranges < 100 NM.
"""

import math
from typing import Tuple
from .constants import (
    NM_PER_DEGREE_LAT,
    FT_PER_NM,
    CYYZ_LAT,
    CYYZ_LON,
)


def great_circle_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two points using Haversine formula.
    
    Args:
        lat1, lon1: First point (degrees)
        lat2, lon2: Second point (degrees)
    
    Returns:
        Distance in nautical miles
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Earth's radius in nautical miles (mean radius)
    earth_radius_nm = 3440.065
    distance_nm = earth_radius_nm * c
    
    return distance_nm


def flat_earth_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance using flat-earth approximation (accurate for < 100 NM).
    Faster than great circle for local airspace.
    
    Args:
        lat1, lon1: First point (degrees)
        lat2, lon2: Second point (degrees)
    
    Returns:
        Distance in nautical miles
    """
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    
    # Use midpoint latitude for cos correction
    mid_lat = (lat1 + lat2) / 2
    cos_lat = math.cos(math.radians(mid_lat))
    
    # Convert to nautical miles
    x_nm = delta_lon * NM_PER_DEGREE_LAT * cos_lat
    y_nm = delta_lat * NM_PER_DEGREE_LAT
    
    distance_nm = math.sqrt(x_nm ** 2 + y_nm ** 2)
    return distance_nm


def distance_to_airport(lat: float, lon: float, 
                       airport_lat: float = CYYZ_LAT,
                       airport_lon: float = CYYZ_LON) -> float:
    """
    Calculate distance from aircraft to airport.
    Uses flat-earth approximation for performance.
    
    Args:
        lat, lon: Aircraft position (degrees)
        airport_lat, airport_lon: Airport position (degrees)
    
    Returns:
        Distance in nautical miles
    """
    return flat_earth_distance(lat, lon, airport_lat, airport_lon)


def update_position(lat: float, lon: float, heading_deg: float, 
                   speed_kts: float, dt: float = 1.0) -> Tuple[float, float]:
    """
    Update aircraft position using small-step Earth approximation.
    
    Args:
        lat, lon: Current position (degrees)
        heading_deg: True heading (degrees, 0=North, 90=East)
        speed_kts: Ground speed (knots)
        dt: Time step (seconds, default 1.0)
    
    Returns:
        Tuple of (new_lat, new_lon) in degrees
    """
    # Convert speed to nautical miles per second
    speed_nm_per_sec = speed_kts / 3600.0
    
    # Distance traveled in this time step
    distance_nm = speed_nm_per_sec * dt
    
    # Convert heading to radians (0° = North, 90° = East)
    heading_rad = math.radians(heading_deg)
    
    # Calculate displacement in NM
    # Note: In aviation, heading 0° is North, 90° is East
    delta_north_nm = distance_nm * math.cos(heading_rad)
    delta_east_nm = distance_nm * math.sin(heading_rad)
    
    # Convert to lat/lon change
    delta_lat = delta_north_nm / NM_PER_DEGREE_LAT
    cos_lat = math.cos(math.radians(lat))
    delta_lon = delta_east_nm / (NM_PER_DEGREE_LAT * cos_lat)
    
    # Update position
    new_lat = lat + delta_lat
    new_lon = lon + delta_lon
    
    return new_lat, new_lon


def normalize_heading(heading: float) -> float:
    """
    Normalize heading to 0-360 range.
    
    Args:
        heading: Heading in degrees (may be outside 0-360)
    
    Returns:
        Normalized heading (0-360)
    """
    while heading < 0:
        heading += 360
    while heading >= 360:
        heading -= 360
    return heading


def heading_difference(current: float, target: float) -> float:
    """
    Calculate the shortest angular difference between two headings.
    Returns negative for left turn, positive for right turn.
    
    Args:
        current: Current heading (0-360)
        target: Target heading (0-360)
    
    Returns:
        Difference in degrees (-180 to +180)
    """
    diff = target - current
    
    # Normalize to -180 to +180
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    
    return diff


def bearing_to_point(from_lat: float, from_lon: float, 
                     to_lat: float, to_lon: float) -> float:
    """
    Calculate initial bearing from one point to another.
    
    Args:
        from_lat, from_lon: Starting point (degrees)
        to_lat, to_lon: Destination point (degrees)
    
    Returns:
        Initial bearing in degrees (0-360, 0=North)
    """
    # Convert to radians
    lat1 = math.radians(from_lat)
    lat2 = math.radians(to_lat)
    delta_lon = math.radians(to_lon - from_lon)
    
    # Calculate bearing
    x = math.sin(delta_lon) * math.cos(lat2)
    y = (math.cos(lat1) * math.sin(lat2) -
         math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon))
    
    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)
    
    return normalize_heading(bearing_deg)


def altitude_msl_to_agl(altitude_msl: float, elevation: float) -> float:
    """
    Convert altitude MSL to AGL.
    
    Args:
        altitude_msl: Altitude mean sea level (feet)
        elevation: Field elevation (feet MSL)
    
    Returns:
        Altitude above ground level (feet)
    """
    return altitude_msl - elevation


def altitude_agl_to_msl(altitude_agl: float, elevation: float) -> float:
    """
    Convert altitude AGL to MSL.
    
    Args:
        altitude_agl: Altitude above ground level (feet)
        elevation: Field elevation (feet MSL)
    
    Returns:
        Altitude mean sea level (feet)
    """
    return altitude_agl + elevation

