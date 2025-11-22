"""
Aircraft kinematics formulas for deterministic motion simulation.
All formulas operate on 1-second time steps (Δt = 1 s).

This module is Ray-distributed for parallel execution on remote cluster nodes.
"""

import math
import random
from typing import Dict, Any, Optional

try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False

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


def calculate_holding_heading(lat: float, lon: float, current_distance_nm: float) -> float:
    """
    Calculate heading to maintain or extend distance from airport.
    Used for holding pattern when aircraft haven't been assigned waypoints.
    
    Args:
        lat, lon: Current aircraft position
        current_distance_nm: Current distance from airport
    
    Returns:
        Heading in degrees to maintain distance > 60 NM
    """
    yyz_lat = 43.6777
    yyz_lon = -79.6248
    
    # Calculate bearing from aircraft to airport
    bearing_to_airport = calculate_heading_to_yyz(lat, lon)
    
    # More aggressive holding pattern based on distance using configurable constants
    from .constants import HOLDING_BOUNDARY_NM
    
    if current_distance_nm < HOLDING_BOUNDARY_NM:
        # Aircraft is INSIDE boundary - turn AWAY from airport to increase distance
        # Turn 180 degrees opposite to airport bearing to move away
        holding_heading = (bearing_to_airport + 180) % 360
        print("INSIDE BOUNDARY: Turning 180 deg away from airport")
    elif current_distance_nm <= HOLDING_BOUNDARY_NM + 5.0:
        # Aircraft is close to boundary - turn perpendicular for circular pattern
        holding_heading = (bearing_to_airport + 90) % 360
        print("CLOSE TO BOUNDARY: Turning 90 deg perpendicular")
    elif current_distance_nm <= HOLDING_BOUNDARY_NM + 10.0:
        # Aircraft is approaching boundary - turn more away from airport
        holding_heading = (bearing_to_airport + 120) % 360
        print("APPROACHING BOUNDARY: Turning 120 deg away")
    else:
        # Aircraft is further out - turn more away from airport to extend distance
        holding_heading = (bearing_to_airport + 120) % 360
    
    return holding_heading


def should_enter_holding_pattern(aircraft: Dict[str, Any]) -> bool:
    """
    Determine if aircraft should enter holding pattern.
    
    More aggressive conditions to prevent aircraft from penetrating 60 NM boundary:
    1. Aircraft is INSIDE 60 NM boundary (any altitude), OR
    2. Aircraft is approaching 60 NM boundary (60-70 NM) and below 16,000 ft, OR
    3. Aircraft is at any distance but significantly below proper altitude for approach
    
    Args:
        aircraft: Aircraft data dictionary
    
    Returns:
        True if aircraft should enter holding pattern
    """
    position = aircraft["position"]
    altitude_ft = position["altitude_ft"]
    distance_nm = aircraft.get("distance_to_airport_nm", 999.0)
    controller = aircraft.get("controller", "ENGINE")
    
    # Check if aircraft has specific assignments (waypoints, targets)
    has_specific_assignments = (
        aircraft.get("target_heading_deg") is not None or
        aircraft.get("target_altitude_ft") is not None or
        aircraft.get("target_speed_kts") is not None or
        aircraft.get("waypoints") is not None
    )
    
    # More aggressive holding pattern conditions using configurable constants
    from .constants import (
        HOLDING_BOUNDARY_NM, HOLDING_APPROACH_RANGE_NM, 
        HOLDING_MIN_ALTITUDE_FT, HOLDING_TARGET_ALTITUDE_FT
    )
    
    # Trigger holding pattern if:
    # 1. Inside boundary (any altitude)
    inside_boundary = distance_nm < HOLDING_BOUNDARY_NM
    
    # 2. Approaching boundary and below target altitude
    approaching_boundary_low = (HOLDING_BOUNDARY_NM <= distance_nm <= HOLDING_APPROACH_RANGE_NM 
                               and altitude_ft < HOLDING_TARGET_ALTITUDE_FT)
    
    # 3. Any distance but significantly below proper altitude for approach
    altitude_too_low = altitude_ft < HOLDING_MIN_ALTITUDE_FT
    
    engine_controlled = controller == "ENGINE"
    not_assigned = not has_specific_assignments
    
    should_hold = (inside_boundary or approaching_boundary_low or altitude_too_low) and engine_controlled and not_assigned
    
    # Debug logging
    if should_hold:
        callsign = aircraft.get("callsign", "UNKNOWN")
        print(f"HOLDING TRIGGERED: {callsign} - Distance: {distance_nm:.1f} NM, Alt: {altitude_ft:.0f} ft")
        print(f"   Inside: {inside_boundary}, Approaching: {approaching_boundary_low}, Low Alt: {altitude_too_low}")
    
    return should_hold


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


def calculate_descent_profile(current_distance_nm: float, current_altitude_ft: float, 
                            target_altitude_ft: float = None) -> float:
    """
    Calculate descent rate to reach target altitude at boundary.
    
    Args:
        current_distance_nm: Current distance from YYZ
        current_altitude_ft: Current altitude MSL
        target_altitude_ft: Target altitude at boundary (uses constant if None)
    
    Returns:
        Required descent rate (fpm)
    """
    from .constants import HOLDING_BOUNDARY_NM, HOLDING_DESCENT_TARGET_ALTITUDE_FT
    
    if target_altitude_ft is None:
        target_altitude_ft = HOLDING_DESCENT_TARGET_ALTITUDE_FT
    
    distance_to_boundary = current_distance_nm - HOLDING_BOUNDARY_NM
    altitude_to_lose = current_altitude_ft - target_altitude_ft
    
    if distance_to_boundary > 0 and altitude_to_lose > 0:
        # Calculate required descent rate (ft/NM)
        required_descent_rate = altitude_to_lose / distance_to_boundary
        # Convert to fpm (feet per minute) at typical speed
        descent_rate_fpm = required_descent_rate * 300  # Assuming 300 kts
        return min(descent_rate_fpm, 2000)  # Cap at 2000 fpm
    return 0


def calculate_speed_profile(current_distance_nm: float, current_speed_kts: float) -> float:
    """
    Calculate speed reduction to reach target speed at boundary.
    
    Args:
        current_distance_nm: Current distance from YYZ
        current_speed_kts: Current speed
    
    Returns:
        Target speed (kts)
    """
    from .constants import HOLDING_BOUNDARY_NM, HOLDING_TARGET_SPEED_KTS
    
    if current_distance_nm > HOLDING_BOUNDARY_NM:
        # Gradual speed reduction from 300+ to target speed at boundary
        # At 80 NM: 300+ kts, At boundary: target speed
        distance_factor = (current_distance_nm - HOLDING_BOUNDARY_NM) / 20  # 0 to 1 as distance decreases
        target_speed = HOLDING_TARGET_SPEED_KTS + distance_factor * 20  # target to target+20 kts
        return min(target_speed, current_speed_kts)
    return current_speed_kts


def calculate_heading_to_yyz(lat: float, lon: float) -> float:
    """
    Calculate heading from current position to YYZ.
    
    Args:
        lat: Current latitude
        lon: Current longitude
    
    Returns:
        Heading to YYZ (degrees, 0-360)
    """
    yyz_lat = 43.6777
    yyz_lon = -79.6248
    
    d_lon = (yyz_lon - lon) * math.pi / 180
    lat1 = lat * math.pi / 180
    lat2 = yyz_lat * math.pi / 180
    
    y = math.sin(d_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    
    heading = math.atan2(y, x) * 180 / math.pi
    return (heading + 360) % 360


def apply_logical_approach_physics(aircraft: Dict[str, Any], dt: float = DT) -> Dict[str, Any]:
    """
    Apply logical approach physics instead of random drift.
    
    Args:
        aircraft: Aircraft state dictionary
        dt: Time step (seconds)
    
    Returns:
        Updated aircraft state with logical physics applied
    """
    # Extract current state
    position = aircraft.get("position", {})
    lat = position.get("lat", 0.0)
    lon = position.get("lon", 0.0)
    altitude_ft = position.get("altitude_ft", 0.0)
    speed_kts = position.get("speed_kts", 0.0)
    heading = position.get("heading", 0.0)
    
    # Calculate distance to YYZ
    from .geo_utils import distance_to_airport
    distance_nm = distance_to_airport(lat, lon)
    
    # Apply altitude profile based on situation - using configurable constants
    from .constants import (
        HOLDING_BOUNDARY_NM, HOLDING_MIN_ALTITUDE_FT, HOLDING_TARGET_ALTITUDE_FT
    )
    
    if altitude_ft < HOLDING_MIN_ALTITUDE_FT:
        # Aircraft is significantly below proper altitude - FORCE CLIMB to target altitude
        target_altitude = HOLDING_TARGET_ALTITUDE_FT
        new_altitude, vertical_speed = update_altitude(
            altitude_ft, target_altitude, distance_nm, False, dt
        )
        print(f"FORCED CLIMB: Altitude {altitude_ft:.0f} ft -> {target_altitude:.0f} ft")
    elif distance_nm < HOLDING_BOUNDARY_NM and altitude_ft < HOLDING_TARGET_ALTITUDE_FT:
        # Aircraft is inside boundary but below target altitude - CLIMB to target altitude
        target_altitude = HOLDING_TARGET_ALTITUDE_FT
        new_altitude, vertical_speed = update_altitude(
            altitude_ft, target_altitude, distance_nm, False, dt
        )
    elif distance_nm > HOLDING_BOUNDARY_NM:
        # Normal descent profile for aircraft approaching boundary
        target_altitude = calculate_descent_profile(distance_nm, altitude_ft)
        new_altitude, vertical_speed = update_altitude(
            altitude_ft, target_altitude, distance_nm, False, dt
        )
    else:
        # Aircraft is at proper altitude and distance
        new_altitude = altitude_ft
        vertical_speed = 0.0
    
    # Apply speed profile using configurable constants
    from .constants import HOLDING_BOUNDARY_NM
    if distance_nm > HOLDING_BOUNDARY_NM:
        target_speed = calculate_speed_profile(distance_nm, speed_kts)
        new_speed = update_speed(speed_kts, target_speed, dt)
    else:
        new_speed = speed_kts
    
    # Check if aircraft should enter holding pattern
    if should_enter_holding_pattern(aircraft):
        # Apply holding pattern - turn perpendicular to maintain distance > 60 NM
        holding_heading = calculate_holding_heading(lat, lon, distance_nm)
        new_heading = update_heading(heading, holding_heading, speed_kts, dt)
        
        # Log holding pattern activation with more detail
        callsign = aircraft.get("callsign", "UNKNOWN")
        if distance_nm < 60.0:
            print(f"HOLDING PATTERN: {callsign} INSIDE 60 NM at {distance_nm:.1f} NM, {altitude_ft:.0f} ft - TURNING AWAY")
        else:
            print(f"HOLDING PATTERN: {callsign} approaching 60 NM at {distance_nm:.1f} NM, {altitude_ft:.0f} ft")
    else:
        # Normal approach - maintain heading toward YYZ (with small random variation)
        yyz_heading = calculate_heading_to_yyz(lat, lon)
        heading_variation = random.uniform(-5, 5)  # ±5 degrees
        target_heading = (yyz_heading + heading_variation) % 360
        new_heading = update_heading(heading, target_heading, speed_kts, dt)
    
    # Update position
    from .geo_utils import update_position
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


def update_aircraft_state(aircraft: Dict[str, Any], dt: float = DT) -> Dict[str, Any]:
    """
    Update complete aircraft state for one tick.
    Applies logical approach physics for arrivals, random drift for others.
    
    This function is CPU-intensive and executes on Ray cluster nodes.
    
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
    
    # Calculate distance to airport
    from .geo_utils import distance_to_airport
    distance_nm = distance_to_airport(lat, lon)
    
    # Check if aircraft is controlled by ENGINE and is an arrival
    controller = aircraft.get("controller", "ENGINE")
    flight_type = aircraft.get("flight_type", "ARRIVAL")
    
    # Apply logical approach physics for ENGINE-controlled arrivals
    if controller == "ENGINE" and flight_type == "ARRIVAL":
        return apply_logical_approach_physics(aircraft, dt)
    
    # For other aircraft, use original logic with targets or drift
    target_speed = aircraft.get("target_speed_kts")
    target_heading = aircraft.get("target_heading_deg")
    target_altitude = aircraft.get("target_altitude_ft")
    
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
    from .geo_utils import update_position
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

