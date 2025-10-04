"""
Core navigation utilities for aircraft positioning and waypoint navigation
"""

import math
from typing import Tuple, Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class NavigationUtils:
    """Navigation utility functions for aircraft positioning"""
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth
        Returns distance in nautical miles
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in nautical miles
        earth_radius_nm = 3440.065
        distance_nm = earth_radius_nm * c
        
        return distance_nm
    
    @staticmethod
    def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the bearing from point 1 to point 2
        Returns bearing in degrees (0-360)
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlon = lon2_rad - lon1_rad
        
        y = math.sin(dlon) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        # Normalize to 0-360
        bearing_deg = (bearing_deg + 360) % 360
        
        return bearing_deg
    
    @staticmethod
    def calculate_new_position(lat: float, lon: float, bearing: float, 
                            distance_nm: float) -> Tuple[float, float]:
        """
        Calculate new position given current position, bearing, and distance
        Returns (new_lat, new_lon)
        """
        # Convert to radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        # Earth's radius in nautical miles
        earth_radius_nm = 3440.065
        
        # Calculate new position
        new_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_nm / earth_radius_nm) +
            math.cos(lat_rad) * math.sin(distance_nm / earth_radius_nm) * math.cos(bearing_rad)
        )
        
        new_lon_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_nm / earth_radius_nm) * math.cos(lat_rad),
            math.cos(distance_nm / earth_radius_nm) - math.sin(lat_rad) * math.sin(new_lat_rad)
        )
        
        # Convert back to degrees
        new_lat = math.degrees(new_lat_rad)
        new_lon = math.degrees(new_lon_rad)
        
        return new_lat, new_lon
    
    @staticmethod
    def calculate_turn_radius(speed_kts: float, bank_angle_deg: float = 25.0) -> float:
        """
        Calculate turn radius for a given speed and bank angle
        Returns radius in nautical miles
        """
        # Convert to radians
        bank_angle_rad = math.radians(bank_angle_deg)
        
        # Turn radius formula: R = V² / (g * tan(φ))
        # Where V is velocity, g is gravity, φ is bank angle
        g = 32.174  # ft/s²
        speed_ft_per_sec = speed_kts * 1.68781  # Convert knots to ft/s
        
        radius_ft = (speed_ft_per_sec ** 2) / (g * math.tan(bank_angle_rad))
        radius_nm = radius_ft / 6076.12  # Convert feet to nautical miles
        
        return radius_nm
    
    @staticmethod
    def calculate_intercept_course(current_lat: float, current_lon: float,
                                 current_heading: float, current_speed: float,
                                 target_lat: float, target_lon: float,
                                 target_speed: float) -> float:
        """
        Calculate the course to intercept a moving target
        Returns intercept course in degrees
        """
        # This is a simplified intercept calculation
        # In reality, this would be more complex with relative motion
        
        # For now, just calculate direct bearing to target
        return NavigationUtils.calculate_bearing(current_lat, current_lon, target_lat, target_lon)
    
    @staticmethod
    def is_within_waypoint_tolerance(current_lat: float, current_lon: float,
                                   waypoint_lat: float, waypoint_lon: float,
                                   tolerance_nm: float = 2.0) -> bool:
        """
        Check if aircraft is within tolerance of a waypoint
        Returns True if within tolerance
        """
        distance = NavigationUtils.haversine_distance(
            current_lat, current_lon, waypoint_lat, waypoint_lon
        )
        return distance <= tolerance_nm
    
    @staticmethod
    def calculate_altitude_change_rate(current_alt: int, target_alt: int, 
                                     time_seconds: float) -> float:
        """
        Calculate required altitude change rate in feet per minute
        """
        alt_diff = target_alt - current_alt
        if time_seconds <= 0:
            return 0
        
        # Convert to feet per minute
        rate_fpm = (alt_diff * 60) / time_seconds
        return rate_fpm
    
    @staticmethod
    def calculate_speed_change_rate(current_speed: float, target_speed: float,
                                  time_seconds: float) -> float:
        """
        Calculate required speed change rate in knots per second
        """
        speed_diff = target_speed - current_speed
        if time_seconds <= 0:
            return 0
        
        rate_kts_per_sec = speed_diff / time_seconds
        return rate_kts_per_sec
