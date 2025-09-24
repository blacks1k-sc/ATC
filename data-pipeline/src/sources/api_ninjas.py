import os
from typing import Optional
from slugify import slugify
from ..models import TypeSpec, EngineSpec, Dimensions
from ..utils.http import request_json
from ..utils.cache import get_cached_json, set_cached_json
from ..utils.derive import normalize_engine_type, lbs_to_kg, ft_to_m
import logging

logger = logging.getLogger(__name__)

def get_api_key() -> Optional[str]:
    """Get API Ninjas key from environment."""
    return os.getenv("API_NINJAS_KEY")

def _safe_float(value) -> Optional[float]:
    """Safely convert value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def fetch_by_model(manufacturer: str, model: str) -> Optional[TypeSpec]:
    """
    Fetch aircraft data from API Ninjas by manufacturer and model.
    
    Args:
        manufacturer: Aircraft manufacturer
        model: Aircraft model
        
    Returns:
        TypeSpec with available data or None if failed
    """
    api_key = get_api_key()
    if not api_key:
        logger.warning("API_NINJAS_KEY not set, skipping API Ninjas")
        return None
    
    # Create cache key
    cache_key = f"ninjas_{slugify(manufacturer)}_{slugify(model)}"
    
    # Check cache first
    cached_data = get_cached_json(cache_key)
    if cached_data:
        return _parse_response(cached_data, manufacturer, model)
    
    # Make API request
    url = "https://api.api-ninjas.com/v1/aircraft"
    headers = {"X-Api-Key": api_key}
    params = {
        "manufacturer": manufacturer,
        "model": model
    }
    
    logger.info(f"Fetching from API Ninjas: {manufacturer} {model}")
    data = request_json(url, headers=headers, params=params)
    
    if not data:
        logger.warning(f"No data from API Ninjas for {manufacturer} {model}")
        return None
    
    # Cache the response
    set_cached_json(cache_key, data)
    
    return _parse_response(data, manufacturer, model)

def _parse_response(data: dict, manufacturer: str, model: str) -> Optional[TypeSpec]:
    """
    Parse API Ninjas response into TypeSpec.
    
    Args:
        data: API response data
        manufacturer: Aircraft manufacturer
        model: Aircraft model
        
    Returns:
        TypeSpec or None if parsing failed
    """
    try:
        # API Ninjas returns a list, take first result
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            logger.warning(f"Unexpected API Ninjas response format for {manufacturer} {model}")
            return None
        
        # Extract dimensions
        dimensions = None
        if any(field in item for field in ["wing_span_ft", "length_ft", "height_ft"]):
            dimensions = Dimensions(
                length_m=ft_to_m(_safe_float(item.get("length_ft"))),
                wingspan_m=ft_to_m(_safe_float(item.get("wing_span_ft"))),
                height_m=ft_to_m(_safe_float(item.get("height_ft")))
            )
        
        # Extract engine information
        engine_count = item.get("engines")
        engine_type = normalize_engine_type(item.get("engine_type"))
        
        engines = EngineSpec(
            count=engine_count,
            type=engine_type
        )
        
        # Create TypeSpec (we don't have ICAO type from API Ninjas, will be set later)
        typespec = TypeSpec(
            icao_type="",  # Will be set by caller
            wake=None,  # Will be derived from MTOW
            engines=engines,
            dimensions=dimensions,
            mtow_kg=lbs_to_kg(_safe_float(item.get("gross_weight_lbs"))),
            cruise_speed_kts=_safe_float(item.get("cruise_speed_knots")),
            max_speed_kts=_safe_float(item.get("max_speed_knots")),
            range_nm=_safe_float(item.get("range_nautical_miles")),
            ceiling_ft=_safe_float(item.get("ceiling_ft")),
            takeoff_ground_run_ft=_safe_float(item.get("takeoff_ground_run_ft")),
            landing_ground_roll_ft=_safe_float(item.get("landing_ground_roll_ft")),
            engine_thrust_lbf=_safe_float(item.get("engine_thrust_lb_ft")),  # Note: API field name might be different
                notes={"source": [f"API Ninjas ({manufacturer} {model})"]}
        )
        
        logger.debug(f"Parsed API Ninjas data for {manufacturer} {model}")
        return typespec
        
    except Exception as e:
        logger.error(f"Failed to parse API Ninjas response for {manufacturer} {model}: {e}")
        return None
