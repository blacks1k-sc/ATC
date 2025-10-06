"""
Aircraft kinematics formulas for deterministic motion simulation.
All formulas operate on 1-second time steps (Δt = 1 s).
"""

import math
import random
from typing import Dict, Any, Optional
from .constants import (
    DT,
    A_ACC_MAX,
    A_DEC_MAX,
    PHI_MAX_RAD,
    H_DOT_CLIMB_MAX,
    H_DOT_DESCENT_MAX,
    H_DOT_DESCENT_MAX_APPROACH,
    G,
    GLIDESLOPE_SLOPE,
    FT_PER_NM,
    DRIFT_SPEED_KT,
    DRIFT_HEADING_DEG,
    DEFAULT_MIN_SPEED_KTS,
    DEFAULT_MAX_SPEED_KTS,
    CYYZ_ELEVATION_FT,
)


def clip(value: float, min_val: float, max_val: float) -> float:
    """Clip value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def update_speed(current_speed: float, target_speed: float, dt: float = DT) -> float:
    """
    Update speed with acceleration/deceleration limits.
    
    Speed tracking: ΔV = clip(V* - V, -a_dec_max·Δt, a_acc_max·Δt)
    V_new = V + ΔV
    
    Args:
        current_speed: Current airspeed (knots)
        target_speed: Target airspeed (knots)
        dt: Time step (seconds)
    
    Returns:
        New speed (knots)
    """
    speed_error = target_speed - current_speed
    
    # Calculate maximum speed change this tick
    max_accel = A_ACC_MAX * dt
    max_decel = -A_DEC_MAX * dt
    
    # Clip speed change to acceleration limits
    delta_speed = clip(speed_error, max_decel, max_accel)
    
    # Apply speed change
    new_speed = current_speed + delta_speed
    
    # Safety limits
    new_speed = clip(new_speed, DEFAULT_MIN_SPEED_KTS, DEFAULT_MAX_SPEED_KTS)
    
    return new_speed


def calculate_max_turn_rate(speed_kts: float, bank_angle_rad: float = PHI_MAX_RAD) -> float:
    """
    Calculate maximum turn rate based on bank angle and speed.
    
    ω_max = g·tan(φ_max) / V_m
    
    Args:
        speed_kts: True airspeed (knots)
        bank_angle_rad: Bank angle (radians)
    
    Returns:
        Maximum turn rate (degrees per second)
    """
    # Convert speed to m/s
    speed_ms = speed_kts * 0.514444
    
    # Calculate turn rate in rad/s
    if speed_ms < 1.0:  # Avoid division by zero
        return 0.0
    
    omega_rad_per_sec = (G * math.tan(bank_angle_rad)) / speed_ms
    
    # Convert to degrees per second
    omega_deg_per_sec = math.degrees(omega_rad_per_sec)
    
    return omega_deg_per_sec


def update_heading(current_heading: float, target_heading: float,
                  speed_kts: float, dt: float = DT) -> float:
    """
    Update heading with bank-limited turn rate.
    
    ω_max = g·tan(φ_max) / V_m
    Δψ = clip(ψ* - ψ, -ω_max·Δt, +ω_max·Δt)
    ψ_new = ψ + Δψ
    
    Args:
        current_heading: Current heading (degrees, 0-360)
        target_heading: Target heading (degrees, 0-360)
        speed_kts: Current airspeed (knots)
        dt: Time step (seconds)
    
    Returns:
        New heading (degrees, 0-360)
    """
    # Calculate heading error (shortest turn direction)
    heading_error = target_heading - current_heading
    
    # Normalize to -180 to +180
    while heading_error > 180:
        heading_error -= 360
    while heading_error < -180:
        heading_error += 360
    
    # Calculate maximum turn rate
    max_turn_rate = calculate_max_turn_rate(speed_kts)
    max_heading_change = max_turn_rate * dt
    
    # Clip heading change to turn rate limits
    delta_heading = clip(heading_error, -max_heading_change, max_heading_change)
    
    # Apply heading change
    new_heading = current_heading + delta_heading
    
    # Normalize to 0-360
    while new_heading < 0:
        new_heading += 360
    while new_heading >= 360:
        new_heading -= 360
    
    return new_heading


def calculate_turn_radius(speed_kts: float, bank_angle_rad: float = PHI_MAX_RAD) -> float:
    """
    Calculate turn radius.
    
    R = V_m² / (g·tan(φ_max))
    
    Args:
        speed_kts: True airspeed (knots)
        bank_angle_rad: Bank angle (radians)
    
    Returns:
        Turn radius (nautical miles)
    """
    # Convert speed to m/s
    speed_ms = speed_kts * 0.514444
    
    # Calculate radius in meters
    if math.tan(bank_angle_rad) < 0.001:  # Avoid division by zero
        return 999999.0
    
    radius_m = (speed_ms ** 2) / (G * math.tan(bank_angle_rad))
    
    # Convert to nautical miles
    radius_nm = radius_m / 1852.0
    
    return radius_nm


def update_altitude(current_altitude: float, target_altitude: float,
                   distance_to_airport: float, is_approach: bool = False,
                   dt: float = DT) -> tuple[float, float]:
    """
    Update altitude with vertical speed limits.
    
    Δh = clip(h* - h, -(ḣ↓·Δt/60), +(ḣ↑·Δt/60))
    h_new = h + Δh
    
    For approach: h*(D) = THR_elev + 6076·slope·D (3° glideslope)
    
    Args:
        current_altitude: Current altitude MSL (feet)
        target_altitude: Target altitude MSL (feet)
        distance_to_airport: Distance to airport (nautical miles)
        is_approach: Whether on approach (limits vertical speed)
        dt: Time step (seconds)
    
    Returns:
        Tuple of (new_altitude, vertical_speed_fpm)
    """
    altitude_error = target_altitude - current_altitude
    
    # Determine vertical speed limits
    if is_approach or distance_to_airport < 10.0:
        max_climb_fpm = H_DOT_DESCENT_MAX_APPROACH
        max_descent_fpm = H_DOT_DESCENT_MAX_APPROACH
    else:
        max_climb_fpm = H_DOT_CLIMB_MAX
        max_descent_fpm = H_DOT_DESCENT_MAX
    
    # Calculate maximum altitude change this tick (fpm to ft/s)
    max_climb_ft = (max_climb_fpm / 60.0) * dt
    max_descent_ft = -(max_descent_fpm / 60.0) * dt
    
    # Clip altitude change to vertical speed limits
    delta_altitude = clip(altitude_error, max_descent_ft, max_climb_ft)
    
    # Apply altitude change
    new_altitude = current_altitude + delta_altitude
    
    # Calculate vertical speed in fpm
    vertical_speed_fpm = (delta_altitude / dt) * 60.0
    
    return new_altitude, vertical_speed_fpm


def calculate_glideslope_altitude(distance_nm: float, 
                                 runway_elevation: float = CYYZ_ELEVATION_FT,
                                 slope: float = GLIDESLOPE_SLOPE) -> float:
    """
    Calculate target altitude on 3° glideslope.
    
    h*(D) = THR_elev + 6076·slope·D
    
    Args:
        distance_nm: Distance to runway threshold (nautical miles)
        runway_elevation: Runway elevation (feet MSL)
        slope: Glideslope slope (tan of angle, ~0.0524 for 3°)
    
    Returns:
        Target altitude MSL (feet)
    """
    altitude_above_threshold = FT_PER_NM * slope * distance_nm
    target_altitude = runway_elevation + altitude_above_threshold
    
    return target_altitude


def apply_random_drift(current_value: float, drift_amount: float, 
                      is_circular: bool = False) -> float:
    """
    Apply small random drift to simulate uncontrolled aircraft.
    
    Args:
        current_value: Current value (speed or heading)
        drift_amount: Maximum drift (± value)
        is_circular: Whether value wraps (e.g., heading 0-360)
    
    Returns:
        New value with drift applied
    """
    drift = random.uniform(-drift_amount, drift_amount)
    new_value = current_value + drift
    
    if is_circular:
        # Normalize heading to 0-360
        while new_value < 0:
            new_value += 360
        while new_value >= 360:
            new_value -= 360
    
    return new_value


def update_aircraft_state(aircraft: Dict[str, Any], dt: float = DT) -> Dict[str, Any]:
    """
    Update complete aircraft state for one tick.
    Applies all kinematic formulas and random drift.
    
    Args:
        aircraft: Aircraft state dictionary
        dt: Time step (seconds)
    
    Returns:
        Updated aircraft state dictionary
    """
    # Extract current state
    position = aircraft.get("position", {})
    lat = position.get("lat", 0.0)
    lon = position.get("lon", 0.0)
    altitude = position.get("altitude_ft", 0.0)
    speed = position.get("speed_kts", 0.0)
    heading = position.get("heading", 0.0)
    
    # Get targets (if None, apply drift)
    target_speed = aircraft.get("target_speed_kts")
    target_heading = aircraft.get("target_heading_deg")
    target_altitude = aircraft.get("target_altitude_ft")
    
    # Calculate distance to airport
    from .geo_utils import distance_to_airport, update_position
    distance_nm = distance_to_airport(lat, lon)
    
    # Determine if on approach
    is_approach = distance_nm < 20.0
    
    # Update speed
    if target_speed is not None:
        new_speed = update_speed(speed, target_speed, dt)
    else:
        # Apply random drift
        new_speed = apply_random_drift(speed, DRIFT_SPEED_KT, is_circular=False)
        new_speed = clip(new_speed, DEFAULT_MIN_SPEED_KTS, DEFAULT_MAX_SPEED_KTS)
    
    # Update heading
    if target_heading is not None:
        new_heading = update_heading(heading, target_heading, speed, dt)
    else:
        # Apply random drift
        new_heading = apply_random_drift(heading, DRIFT_HEADING_DEG, is_circular=True)
    
    # Update altitude
    if target_altitude is not None:
        new_altitude, vertical_speed = update_altitude(
            altitude, target_altitude, distance_nm, is_approach, dt
        )
    else:
        # Maintain altitude or gentle descent toward airport
        if distance_nm < 30.0:
            # Auto-descend on glideslope if close to airport
            target_alt = calculate_glideslope_altitude(distance_nm)
            new_altitude, vertical_speed = update_altitude(
                altitude, target_alt, distance_nm, True, dt
            )
        else:
            new_altitude = altitude
            vertical_speed = 0.0
    
    # Update position
    new_lat, new_lon = update_position(lat, lon, new_heading, new_speed, dt)
    
    # Return updated state
    updated = aircraft.copy()
    updated["position"] = {
        "lat": new_lat,
        "lon": new_lon,
        "altitude_ft": new_altitude,
        "speed_kts": new_speed,
        "heading": new_heading,
    }
    updated["vertical_speed_fpm"] = vertical_speed
    updated["distance_to_airport_nm"] = distance_nm
    
    return updated

