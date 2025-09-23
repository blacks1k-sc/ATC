"""
Utilities for deriving aircraft characteristics from available data.
"""

from typing import Literal, Optional


def derive_wake_from_mtow(mtow_kg: Optional[float], icao_type: Optional[str] = None) -> Optional[Literal["L", "M", "H", "J"]]:
    """
    Derive wake turbulence category from MTOW and ICAO type.
    
    Args:
        mtow_kg: Maximum takeoff weight in kilograms
        icao_type: ICAO type designator (for special cases)
    
    Returns:
        Wake turbulence category or None if cannot be determined
    """
    # Special cases for super heavy aircraft
    if icao_type and icao_type.upper() in {"A388", "AN225"}:
        return "J"
    
    # Cannot derive without MTOW
    if mtow_kg is None:
        return None
    
    # Standard wake categories based on MTOW
    if mtow_kg < 7000:
        return "L"  # Light
    elif mtow_kg < 136000:
        return "M"  # Medium
    else:
        return "H"  # Heavy


def estimate_climb_rate_fpm(engine_type: Optional[str], mtow_kg: Optional[float]) -> Optional[int]:
    """
    Estimate climb rate in feet per minute based on engine type and MTOW.
    
    Args:
        engine_type: Engine type ("JET", "TURBOPROP", "PISTON", "ELECTRIC")
        mtow_kg: Maximum takeoff weight in kilograms
    
    Returns:
        Estimated climb rate in fpm or None if cannot be determined
    """
    if engine_type is None or mtow_kg is None:
        return None
    
    # Base climb rates by engine type
    base_rates = {
        "JET": 3000,
        "TURBOPROP": 2000,
        "PISTON": 800,
        "ELECTRIC": 800
    }
    
    base_rate = base_rates.get(engine_type)
    if base_rate is None:
        return None
    
    # Scale based on MTOW (lighter aircraft climb faster)
    # Use a power function to scale: base * (60000 / max(mtow, 6000))^0.25
    # This gives reasonable scaling without extreme values
    weight_factor = (60000 / max(mtow_kg, 6000)) ** 0.25
    estimated_rate = int(base_rate * weight_factor)
    
    # Clamp to reasonable range
    return max(500, min(4500, estimated_rate))


def derive_engine_spec_from_api_data(api_data: dict) -> Optional[dict]:
    """
    Derive engine specification from API data.
    
    Args:
        api_data: Normalized aircraft data from API
    
    Returns:
        Engine specification dict or None
    """
    engine_count = api_data.get("engine_count")
    engine_type = api_data.get("engine_type")
    
    if not engine_count or not engine_type:
        return None
    
    # Validate engine count
    try:
        count = int(engine_count)
        if count < 1 or count > 8:
            return None
    except (ValueError, TypeError):
        return None
    
    # Validate engine type
    if engine_type not in {"JET", "TURBOPROP", "PISTON", "ELECTRIC"}:
        return None
    
    return {
        "count": count,
        "type": engine_type
    }


def derive_dimensions_from_api_data(api_data: dict) -> Optional[dict]:
    """
    Derive dimensions from API data.
    
    Args:
        api_data: Normalized aircraft data from API
    
    Returns:
        Dimensions dict or None
    """
    length_m = api_data.get("length_m")
    wingspan_m = api_data.get("wingspan_m")
    height_m = api_data.get("height_m")
    
    # All three dimensions must be present and positive
    if not all([length_m, wingspan_m, height_m]):
        return None
    
    try:
        length = float(length_m)
        wingspan = float(wingspan_m)
        height = float(height_m)
        
        if length <= 0 or wingspan <= 0 or height <= 0:
            return None
        
        return {
            "length_m": length,
            "wingspan_m": wingspan,
            "height_m": height
        }
    except (ValueError, TypeError):
        return None


def enhance_type_spec_with_derived_data(type_spec: dict, api_data: dict) -> dict:
    """
    Enhance a TypeSpec with derived data from API response.
    
    Args:
        type_spec: Existing TypeSpec data
        api_data: Normalized aircraft data from API
    
    Returns:
        Enhanced TypeSpec dict
    """
    enhanced = type_spec.copy()
    
    # Derive wake if missing
    if not enhanced.get("wake"):
        wake = derive_wake_from_mtow(api_data.get("mtow_kg"), enhanced.get("icao_type"))
        if wake:
            enhanced["wake"] = wake
    
    # Derive engines if missing
    if not enhanced.get("engines"):
        engines = derive_engine_spec_from_api_data(api_data)
        if engines:
            enhanced["engines"] = engines
    
    # Derive dimensions if missing
    if not enhanced.get("dimensions"):
        dimensions = derive_dimensions_from_api_data(api_data)
        if dimensions:
            enhanced["dimensions"] = dimensions
    
    # Add MTOW if available
    if api_data.get("mtow_kg") and not enhanced.get("mtow_kg"):
        enhanced["mtow_kg"] = int(api_data["mtow_kg"])
    
    return enhanced
