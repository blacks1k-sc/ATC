"""
Unit tests for geographic utility functions.
"""

import unittest
import math
from engine.geo_utils import (
    great_circle_distance,
    flat_earth_distance,
    distance_to_airport,
    update_position,
    normalize_heading,
    heading_difference,
    bearing_to_point,
)
from engine.constants import CYYZ_LAT, CYYZ_LON


class TestGeoUtils(unittest.TestCase):
    """Test geographic calculations."""
    
    def test_great_circle_distance_same_point(self):
        """Test distance from point to itself."""
        dist = great_circle_distance(CYYZ_LAT, CYYZ_LON, CYYZ_LAT, CYYZ_LON)
        self.assertAlmostEqual(dist, 0.0, places=2)
    
    def test_great_circle_distance_known(self):
        """Test distance between known points."""
        # Toronto to JFK (roughly 300 NM)
        jfk_lat = 40.6413
        jfk_lon = -73.7781
        
        dist = great_circle_distance(CYYZ_LAT, CYYZ_LON, jfk_lat, jfk_lon)
        
        # Should be around 300 NM
        self.assertGreater(dist, 250)
        self.assertLess(dist, 350)
    
    def test_flat_earth_approximation(self):
        """Test flat earth approximation matches great circle for short distances."""
        # 10 NM away
        target_lat = CYYZ_LAT + 10.0 / 60.0
        target_lon = CYYZ_LON
        
        gc_dist = great_circle_distance(CYYZ_LAT, CYYZ_LON, target_lat, target_lon)
        fe_dist = flat_earth_distance(CYYZ_LAT, CYYZ_LON, target_lat, target_lon)
        
        # Should be very close for short distances
        self.assertAlmostEqual(gc_dist, fe_dist, places=1)
        self.assertAlmostEqual(fe_dist, 10.0, places=1)
    
    def test_update_position_north(self):
        """Test position update moving north."""
        new_lat, new_lon = update_position(CYYZ_LAT, CYYZ_LON, 0.0, 3600.0, 1.0)
        
        # Moving north at 3600 kts for 1 second = 1 NM north
        # 1 NM = 1/60 degree latitude
        expected_lat = CYYZ_LAT + 1.0 / 60.0
        
        self.assertAlmostEqual(new_lat, expected_lat, places=3)
        self.assertAlmostEqual(new_lon, CYYZ_LON, places=3)
    
    def test_update_position_east(self):
        """Test position update moving east."""
        new_lat, new_lon = update_position(CYYZ_LAT, CYYZ_LON, 90.0, 3600.0, 1.0)
        
        # Moving east should increase longitude
        self.assertAlmostEqual(new_lat, CYYZ_LAT, places=3)
        self.assertGreater(new_lon, CYYZ_LON)
    
    def test_normalize_heading(self):
        """Test heading normalization."""
        self.assertAlmostEqual(normalize_heading(0), 0.0)
        self.assertAlmostEqual(normalize_heading(360), 0.0)
        self.assertAlmostEqual(normalize_heading(370), 10.0)
        self.assertAlmostEqual(normalize_heading(-10), 350.0)
        self.assertAlmostEqual(normalize_heading(720), 0.0)
    
    def test_heading_difference(self):
        """Test heading difference calculation."""
        # Simple cases
        self.assertAlmostEqual(heading_difference(0, 90), 90.0)
        self.assertAlmostEqual(heading_difference(90, 0), -90.0)
        
        # Wraparound cases
        self.assertAlmostEqual(heading_difference(350, 10), 20.0)
        self.assertAlmostEqual(heading_difference(10, 350), -20.0)
        
        # 180° ambiguity
        diff = heading_difference(0, 180)
        self.assertAlmostEqual(abs(diff), 180.0)
    
    def test_bearing_to_point_north(self):
        """Test bearing calculation to point directly north."""
        target_lat = CYYZ_LAT + 1.0
        bearing = bearing_to_point(CYYZ_LAT, CYYZ_LON, target_lat, CYYZ_LON)
        
        # Should be approximately 0° (north)
        self.assertLess(abs(bearing), 5.0)
    
    def test_bearing_to_point_east(self):
        """Test bearing calculation to point directly east."""
        target_lon = CYYZ_LON + 1.0
        bearing = bearing_to_point(CYYZ_LAT, CYYZ_LON, CYYZ_LAT, target_lon)
        
        # Should be approximately 90° (east)
        self.assertGreater(bearing, 85.0)
        self.assertLess(bearing, 95.0)
    
    def test_distance_to_airport(self):
        """Test distance calculation to airport."""
        # 30 NM north of airport
        test_lat = CYYZ_LAT + 30.0 / 60.0
        
        dist = distance_to_airport(test_lat, CYYZ_LON)
        
        # Should be approximately 30 NM
        self.assertGreater(dist, 29.0)
        self.assertLess(dist, 31.0)


if __name__ == '__main__':
    unittest.main()

