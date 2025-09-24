import os
from typing import Optional
from slugify import slugify
from ..models import TypeSpec, EngineSpec, Dimensions
from ..utils.http import request_json
from ..utils.cache import get_cached_json, set_cached_json
from ..utils.derive import normalize_engine_type, km_to_nm
import logging

logger = logging.getLogger(__name__)

# AeroDataBox API configuration
AERODATABOX_BASE_URL = "https://aerodatabox.p.rapidapi.com"
AERODATABOX_SEARCH_ENDPOINT = "/aircrafts/search/term"

def get_api_key() -> Optional[str]:
    """Get AeroDataBox API key from environment."""
    return os.getenv("AERODATABOX_KEY")

def get_api_host() -> str:
    """Get AeroDataBox API host from environment."""
    return os.getenv("AERODATABOX_HOST", "aerodatabox.p.rapidapi.com")

def fetch_by_model(manufacturer: str, model: str) -> Optional[TypeSpec]:
    """
    Fetch aircraft data from AeroDataBox by manufacturer and model.
    
    Args:
        manufacturer: Aircraft manufacturer
        model: Aircraft model
        
    Returns:
        TypeSpec with available data or None if failed
    """
    api_key = get_api_key()
    if not api_key:
        logger.warning("AERODATABOX_KEY not set, skipping AeroDataBox")
        return None
    
    # Create cache key
    cache_key = f"adb_{slugify(manufacturer)}_{slugify(model)}"
    
    # Check cache first
    cached_data = get_cached_json(cache_key)
    if cached_data:
        return _parse_response(cached_data, manufacturer, model)
    
    # Build URL with search query
    url = AERODATABOX_BASE_URL + AERODATABOX_SEARCH_ENDPOINT
    params = {"q": f"{manufacturer} {model}"}
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": get_api_host()
    }
    
    logger.info(f"Fetching from AeroDataBox: {manufacturer} {model}")
    data = request_json(url, headers=headers, params=params)
    
    if not data:
        logger.warning(f"No data from AeroDataBox for {manufacturer} {model}")
        return None
    
    # Cache the response
    set_cached_json(cache_key, data)
    
    return _parse_response(data, manufacturer, model)

def _parse_response(data: dict, manufacturer: str, model: str) -> Optional[TypeSpec]:
    """
    Parse AeroDataBox response into TypeSpec.
    
    Args:
        data: API response data
        manufacturer: Aircraft manufacturer
        model: Aircraft model
        
    Returns:
        TypeSpec or None if parsing failed
    """
    try:
        # AeroDataBox response structure may vary, handle different formats
        item = data
        if isinstance(data, dict) and "data" in data:
            item = data["data"]
        elif isinstance(data, list) and len(data) > 0:
            item = data[0]
        
        # Extract dimensions
        dimensions = None
        if any(field in item for field in ["wingspanMeters", "lengthMeters", "heightMeters"]):
            dimensions = Dimensions(
                length_m=item.get("lengthMeters"),
                wingspan_m=item.get("wingspanMeters"),
                height_m=item.get("heightMeters")
            )
        
        # Extract engine information
        engines_data = item.get("engines", {})
        engine_count = engines_data.get("count") if isinstance(engines_data, dict) else None
        engine_type = normalize_engine_type(engines_data.get("type") if isinstance(engines_data, dict) else item.get("engineType"))
        
        engines = EngineSpec(
            count=engine_count,
            type=engine_type
        )
        
        # Create TypeSpec (we don't have ICAO type from AeroDataBox, will be set later)
        typespec = TypeSpec(
            icao_type="",  # Will be set by caller
            wake=None,  # Will be derived from MTOW
            engines=engines,
            dimensions=dimensions,
            mtow_kg=item.get("maxTakeoffWeightKg"),
            cruise_speed_kts=item.get("cruiseSpeedKts"),
            max_speed_kts=item.get("maxSpeedKts"),
            range_nm=km_to_nm(item.get("rangeKm")),  # Convert km to nm
            ceiling_ft=item.get("ceilingFt"),
            takeoff_ground_run_ft=item.get("takeoffDistanceFt"),
            landing_ground_roll_ft=item.get("landingDistanceFt"),
            engine_thrust_lbf=item.get("engineThrustLbf"),
                notes={"source": [f"AeroDataBox ({manufacturer} {model})"]}
        )
        
        logger.debug(f"Parsed AeroDataBox data for {manufacturer} {model}")
        return typespec
        
    except Exception as e:
        logger.error(f"Failed to parse AeroDataBox response for {manufacturer} {model}: {e}")
        return None
