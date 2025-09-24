from typing import Optional
from ..models import Wake, EngineType

def wake_from_mtow(mtow_kg: Optional[float], icao_type: Optional[str] = None) -> Optional[Wake]:
    """
    Derive wake category from MTOW according to ICAO standards.
    
    Args:
        mtow_kg: Maximum takeoff weight in kg
        icao_type: ICAO type designator for special cases
        
    Returns:
        Wake category or None if cannot determine
    """
    if mtow_kg is None:
        return None
    
    # Special case for A380 (Super category)
    if icao_type == "A388":
        return "J"
    
    # ICAO wake turbulence categories
    if mtow_kg < 7000:
        return "L"  # Light
    elif mtow_kg < 136000:
        return "M"  # Medium
    else:
        return "H"  # Heavy

def normalize_engine_type(s: Optional[str]) -> EngineType:
    """
    Normalize engine type string to standard enum.
    
    Args:
        s: Raw engine type string
        
    Returns:
        Normalized engine type
    """
    if not s:
        return "OTHER"
    
    s_upper = s.upper().strip()
    
    # Jet engines
    if any(term in s_upper for term in ["JET", "TURBOJET", "TURBOFAN", "TURBOSHAFT"]):
        return "JET"
    
    # Turboprop
    if any(term in s_upper for term in ["TURBOPROP", "PROP", "TURBINE"]):
        return "TURBOPROP"
    
    # Piston
    if any(term in s_upper for term in ["PISTON", "RECIPROCATING", "RECIP"]):
        return "PISTON"
    
    # Electric
    if any(term in s_upper for term in ["ELECTRIC", "BATTERY", "HYBRID"]):
        return "ELECTRIC"
    
    return "OTHER"

def lbs_to_kg(lbs: Optional[float]) -> Optional[float]:
    """Convert pounds to kilograms."""
    if lbs is None:
        return None
    return lbs * 0.453592

def ft_to_m(ft: Optional[float]) -> Optional[float]:
    """Convert feet to meters."""
    if ft is None:
        return None
    return ft * 0.3048

def nm_to_km(nm: Optional[float]) -> Optional[float]:
    """Convert nautical miles to kilometers."""
    if nm is None:
        return None
    return nm * 1.852

def km_to_nm(km: Optional[float]) -> Optional[float]:
    """Convert kilometers to nautical miles."""
    if km is None:
        return None
    return km / 1.852

def estimate_climb_rate(engine_type: EngineType, mtow_kg: Optional[float]) -> Optional[float]:
    """
    Estimate climb rate based on engine type and MTOW.
    
    Args:
        engine_type: Engine type
        mtow_kg: Maximum takeoff weight in kg
        
    Returns:
        Estimated climb rate in feet per minute
    """
    if mtow_kg is None:
        return None
    
    # Base climb rates by engine type (fpm)
    base_rates = {
        "JET": 2200,
        "TURBOPROP": 1800,
        "PISTON": 1000,
        "ELECTRIC": 900,
        "OTHER": 1200
    }
    
    base_fpm = base_rates.get(engine_type, 1200)
    
    # Scale by MTOW (heavier aircraft climb slower)
    # Scale factor between 0.6 and 1.4 based on 120,000 kg reference
    scale_factor = max(0.6, min(1.4, 120000 / mtow_kg))
    
    return int(base_fpm * scale_factor)
