"""
Unit tests for kinematics formulas.
Validates deterministic behavior and physical constraints.
"""

import unittest
import math
from engine.kinematics import (
    update_speed,
    update_heading,
    update_altitude,
    calculate_turn_radius,
    calculate_max_turn_rate,
    calculate_glideslope_altitude,
    clip,
)
from engine.constants import (
    A_ACC_MAX,
    A_DEC_MAX,
    DT,
    PHI_MAX_DEG,
    CYYZ_ELEVATION_FT,
)


class TestKinematics(unittest.TestCase):
    """Test kinematics formulas."""
    
    def test_clip(self):
        """Test clip function."""
        self.assertEqual(clip(5, 0, 10), 5)
        self.assertEqual(clip(-5, 0, 10), 0)
        self.assertEqual(clip(15, 0, 10), 10)
    
    def test_update_speed_acceleration(self):
        """Test speed update with acceleration."""
        # Accelerate from 200 to 250 kts
        new_speed = update_speed(200, 250, DT)
        
        # Should increase by at most A_ACC_MAX * DT
        expected_max = 200 + A_ACC_MAX * DT
        self.assertLessEqual(new_speed, expected_max + 0.01)
        self.assertGreater(new_speed, 200)
    
    def test_update_speed_deceleration(self):
        """Test speed update with deceleration."""
        # Decelerate from 300 to 250 kts
        new_speed = update_speed(300, 250, DT)
        
        # Should decrease by at most A_DEC_MAX * DT
        expected_min = 300 - A_DEC_MAX * DT
        self.assertGreaterEqual(new_speed, expected_min - 0.01)
        self.assertLess(new_speed, 300)
    
    def test_update_speed_stability(self):
        """Test speed stability when at target."""
        # Already at target speed
        new_speed = update_speed(250, 250, DT)
        self.assertAlmostEqual(new_speed, 250, places=2)
    
    def test_calculate_max_turn_rate(self):
        """Test turn rate calculation."""
        # At 250 kts with 25° bank
        turn_rate = calculate_max_turn_rate(250, math.radians(PHI_MAX_DEG))
        
        # Should be positive and reasonable (around 2-4 deg/s for jets)
        self.assertGreater(turn_rate, 0)
        self.assertLess(turn_rate, 10)  # Sanity check
    
    def test_update_heading_right_turn(self):
        """Test heading update with right turn."""
        # Turn from 0° to 90° at 250 kts
        new_heading = update_heading(0, 90, 250, DT)
        
        # Should turn right (increase)
        self.assertGreater(new_heading, 0)
        self.assertLess(new_heading, 90)  # Can't reach instantly
    
    def test_update_heading_left_turn(self):
        """Test heading update with left turn."""
        # Turn from 90° to 0° at 250 kts
        new_heading = update_heading(90, 0, 250, DT)
        
        # Should turn left (decrease)
        self.assertLess(new_heading, 90)
        self.assertGreater(new_heading, 0)  # Can't reach instantly
    
    def test_update_heading_wraparound(self):
        """Test heading wraparound at 0/360."""
        # Turn from 350° to 10° (shortest path through 0)
        new_heading = update_heading(350, 10, 250, DT)
        
        # Should turn right through 360/0
        self.assertTrue(new_heading > 350 or new_heading < 10)
    
    def test_calculate_turn_radius(self):
        """Test turn radius calculation."""
        # At 250 kts with 25° bank
        radius = calculate_turn_radius(250, math.radians(PHI_MAX_DEG))
        
        # Should be positive and reasonable (a few NM for jets)
        self.assertGreater(radius, 0)
        self.assertLess(radius, 10)  # Typical jet turn radius
    
    def test_update_altitude_climb(self):
        """Test altitude update climbing."""
        # Climb from 10000 to 15000 ft
        new_alt, vs = update_altitude(10000, 15000, 50.0, False, DT)
        
        # Should climb
        self.assertGreater(new_alt, 10000)
        self.assertGreater(vs, 0)  # Positive vertical speed
    
    def test_update_altitude_descent(self):
        """Test altitude update descending."""
        # Descend from 15000 to 10000 ft
        new_alt, vs = update_altitude(15000, 10000, 50.0, False, DT)
        
        # Should descend
        self.assertLess(new_alt, 15000)
        self.assertLess(vs, 0)  # Negative vertical speed
    
    def test_update_altitude_approach_limits(self):
        """Test altitude limits on approach."""
        # Steep descent on approach should be limited to 1800 fpm
        new_alt, vs = update_altitude(5000, 1000, 5.0, True, DT)
        
        # Vertical speed should be capped
        self.assertGreaterEqual(vs, -1800 - 1)  # Allow 1 fpm tolerance
        self.assertLess(vs, 0)  # Should still be descending
    
    def test_calculate_glideslope_altitude(self):
        """Test glideslope altitude calculation."""
        # At 10 NM from runway
        target_alt = calculate_glideslope_altitude(10.0, CYYZ_ELEVATION_FT)
        
        # Should be roughly 3° * 10 NM = ~3000 ft above runway
        expected_alt = CYYZ_ELEVATION_FT + (10.0 * 6076 * 0.0524)
        self.assertAlmostEqual(target_alt, expected_alt, places=0)
        self.assertGreater(target_alt, CYYZ_ELEVATION_FT + 2500)
        self.assertLess(target_alt, CYYZ_ELEVATION_FT + 3500)
    
    def test_glideslope_at_threshold(self):
        """Test glideslope at runway threshold."""
        # At 0 NM from runway
        target_alt = calculate_glideslope_altitude(0.0, CYYZ_ELEVATION_FT)
        
        # Should be at runway elevation
        self.assertAlmostEqual(target_alt, CYYZ_ELEVATION_FT, places=0)
    
    def test_deterministic_behavior(self):
        """Test that formulas produce deterministic results."""
        # Run same calculation twice
        speed1 = update_speed(200, 250, DT)
        speed2 = update_speed(200, 250, DT)
        
        # Should be identical
        self.assertEqual(speed1, speed2)
        
        heading1 = update_heading(0, 90, 250, DT)
        heading2 = update_heading(0, 90, 250, DT)
        
        self.assertEqual(heading1, heading2)


if __name__ == '__main__':
    unittest.main()

