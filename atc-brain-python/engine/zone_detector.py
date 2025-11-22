"""
Zone detection module for determining aircraft sector zones based on distance thresholds.
Returns zone names based on distance from airport using thresholds: 60→50→20→5→0 NM.
"""

from typing import Optional


# Zone distance thresholds (nautical miles from airport)
ZONE_THRESHOLD_60_NM = 60.0
ZONE_THRESHOLD_50_NM = 50.0
ZONE_THRESHOLD_20_NM = 20.0
ZONE_THRESHOLD_5_NM = 5.0
ZONE_THRESHOLD_0_NM = 0.0

# Zone names
ZONE_ENTRY = "ENTRY"          # > 60 NM
ZONE_ENROUTE_50 = "ENROUTE_50"  # 50-60 NM
ZONE_ENROUTE_20 = "ENROUTE_20"  # 20-50 NM
ZONE_APPROACH_5 = "APPROACH_5"  # 5-20 NM
ZONE_RUNWAY = "RUNWAY"         # 0-5 NM


def determine_zone(distance_nm: float) -> str:
    """
    Determine aircraft zone based on distance from airport.
    
    Zones are defined by distance thresholds:
    - ENTRY: > 60 NM
    - ENROUTE_50: 50-60 NM
    - ENROUTE_20: 20-50 NM
    - APPROACH_5: 5-20 NM
    - RUNWAY: 0-5 NM
    
    Args:
        distance_nm: Distance to airport in nautical miles
        
    Returns:
        Zone name string
    """
    if distance_nm > ZONE_THRESHOLD_60_NM:
        return ZONE_ENTRY
    elif distance_nm > ZONE_THRESHOLD_50_NM:
        return ZONE_ENROUTE_50
    elif distance_nm > ZONE_THRESHOLD_20_NM:
        return ZONE_ENROUTE_20
    elif distance_nm > ZONE_THRESHOLD_5_NM:
        return ZONE_APPROACH_5
    else:
        return ZONE_RUNWAY


def has_zone_changed(current_zone: Optional[str], new_zone: str) -> bool:
    """
    Check if zone has changed.
    
    Args:
        current_zone: Current zone name (may be None)
        new_zone: New zone name
        
    Returns:
        True if zone changed, False otherwise
    """
    return current_zone != new_zone

