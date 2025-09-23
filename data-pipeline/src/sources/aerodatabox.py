"""
AeroDataBox API integration module.

This module provides functions to fetch aircraft data from AeroDataBox API,
with caching, rate limiting, and data normalization as a secondary fallback
to API Ninjas.
"""

import os
import json
import time
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import quote
import re

logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "https://aerodatabox.p.rapidapi.com/aircrafts"
API_KEY_ENV = "AERODATABOX_KEY"
API_HOST_ENV = "AERODATABOX_HOST"
CACHE_DIR = Path("cache/aerodatabox")
MIN_REQUEST_INTERVAL = 0.5  # Minimum seconds between requests
MAX_RETRIES = 3

# Ensure cache directory exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Global rate limiting
_last_request_time = 0.0


def _rate_limit():
    """Enforce rate limiting between API requests."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    
    if time_since_last < MIN_REQUEST_INTERVAL:
        sleep_time = MIN_REQUEST_INTERVAL - time_since_last
        logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)
    
    _last_request_time = time.time()


def _slugify_params(manufacturer: str, model: str) -> str:
    """Create a stable cache key from manufacturer and model."""
    manufacturer_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', manufacturer.strip())
    model_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', model.strip())
    return f"{manufacturer_slug}_{model_slug}"


def _get_cache_path(manufacturer: str, model: str) -> Path:
    """Get cache file path for given manufacturer and model."""
    cache_key = _slugify_params(manufacturer, model)
    return CACHE_DIR / f"aircraft_{cache_key}.json"


def _load_from_cache(cache_path: Path) -> Optional[Dict]:
    """Load data from cache if available."""
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            logger.debug(f"Cache hit: {cache_path.name}")
            return data
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}")
    return None


def _save_to_cache(cache_path: Path, data: Dict):
    """Save data to cache."""
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Cached: {cache_path.name}")
    except Exception as e:
        logger.warning(f"Failed to save cache {cache_path}: {e}")


def _make_api_request(url: str, headers: Dict[str, str]) -> Optional[Dict]:
    """Make API request to AeroDataBox with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            _rate_limit()
            
            logger.debug(f"AeroDataBox API request (attempt {attempt + 1}): {url}")
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                # Rate limited - backoff
                if attempt < MAX_RETRIES - 1:
                    backoff_time = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {backoff_time}s")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error("Max retries exceeded for rate limiting")
                    return None
            
            elif response.status_code >= 500:
                # Server error - retry
                if attempt < MAX_RETRIES - 1:
                    backoff_time = 2 ** attempt
                    logger.warning(f"Server error {response.status_code}, retrying in {backoff_time}s")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for server error {response.status_code}")
                    return None
            
            else:
                # Other 4xx errors - don't retry
                logger.warning(f"AeroDataBox API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                backoff_time = 2 ** attempt
                logger.warning(f"Request exception: {e}, retrying in {backoff_time}s")
                time.sleep(backoff_time)
                continue
            else:
                logger.error(f"Max retries exceeded for request exception: {e}")
                return None
    
    return None


def _normalize_aerodatabox_response(api_data: Dict) -> Dict:
    """
    Normalize AeroDataBox API response to our schema.
    
    Args:
        api_data: Raw AeroDataBox API response
    
    Returns:
        Normalized record with our field names and units
    """
    if not api_data:
        return {}
    
    result = {}
    
    # Basic string fields
    result["manufacturer"] = api_data.get("manufacturer")
    result["model"] = api_data.get("model")
    
    # MTOW conversion (already in kg from AeroDataBox)
    try:
        if api_data.get("maxTakeoffWeightKg"):
            result["mtow_kg"] = float(api_data["maxTakeoffWeightKg"])
    except (ValueError, TypeError):
        pass
    
    # Dimensions (convert from meters if needed, or from feet)
    dimensions = {}
    try:
        if api_data.get("lengthM"):
            dimensions["length_m"] = float(api_data["lengthM"])
        elif api_data.get("lengthFt"):
            dimensions["length_m"] = float(api_data["lengthFt"]) * 0.3048
    except (ValueError, TypeError):
        pass
    
    try:
        if api_data.get("wingspanM"):
            dimensions["wingspan_m"] = float(api_data["wingspanM"])
        elif api_data.get("wingspanFt"):
            dimensions["wingspan_m"] = float(api_data["wingspanFt"]) * 0.3048
    except (ValueError, TypeError):
        pass
    
    try:
        if api_data.get("heightM"):
            dimensions["height_m"] = float(api_data["heightM"])
        elif api_data.get("heightFt"):
            dimensions["height_m"] = float(api_data["heightFt"]) * 0.3048
    except (ValueError, TypeError):
        pass
    
    if dimensions:
        result["dimensions"] = dimensions
    
    # Speed data
    try:
        if api_data.get("maxSpeedKts"):
            result["max_speed_kts"] = float(api_data["maxSpeedKts"])
        elif api_data.get("maxSpeedKmh"):
            result["max_speed_kts"] = float(api_data["maxSpeedKmh"]) * 0.539957  # km/h to knots
    except (ValueError, TypeError):
        pass
    
    try:
        if api_data.get("cruiseSpeedKts"):
            result["cruise_speed_kts"] = float(api_data["cruiseSpeedKts"])
        elif api_data.get("cruiseSpeedKmh"):
            result["cruise_speed_kts"] = float(api_data["cruiseSpeedKmh"]) * 0.539957  # km/h to knots
    except (ValueError, TypeError):
        pass
    
    # Ceiling
    try:
        if api_data.get("ceilingFt"):
            result["ceiling_ft"] = float(api_data["ceilingFt"])
        elif api_data.get("ceilingM"):
            result["ceiling_ft"] = float(api_data["ceilingM"]) * 3.28084  # meters to feet
    except (ValueError, TypeError):
        pass
    
    # Range
    try:
        if api_data.get("rangeNm"):
            result["range_nm"] = float(api_data["rangeNm"])
        elif api_data.get("rangeKm"):
            result["range_nm"] = float(api_data["rangeKm"]) * 0.539957  # km to nautical miles
    except (ValueError, TypeError):
        pass
    
    # Takeoff and landing distances
    try:
        if api_data.get("takeoffRunFt"):
            result["takeoff_ground_run_ft"] = float(api_data["takeoffRunFt"])
        elif api_data.get("takeoffRunM"):
            result["takeoff_ground_run_ft"] = float(api_data["takeoffRunM"]) * 3.28084  # meters to feet
    except (ValueError, TypeError):
        pass
    
    try:
        if api_data.get("landingRunFt"):
            result["landing_ground_roll_ft"] = float(api_data["landingRunFt"])
        elif api_data.get("landingRunM"):
            result["landing_ground_roll_ft"] = float(api_data["landingRunM"]) * 3.28084  # meters to feet
    except (ValueError, TypeError):
        pass
    
    # Engine thrust
    try:
        if api_data.get("thrustLbf"):
            result["engine_thrust_lbf"] = float(api_data["thrustLbf"])
        elif api_data.get("thrustN"):
            result["engine_thrust_lbf"] = float(api_data["thrustN"]) * 0.224809  # Newtons to pounds-force
    except (ValueError, TypeError):
        pass
    
    # Engine type normalization
    engine_type_str = api_data.get("engineType", "").lower()
    if any(term in engine_type_str for term in ["jet", "turbofan", "turbojet"]):
        result["engine_type"] = "JET"
    elif any(term in engine_type_str for term in ["turboprop", "prop"]):
        result["engine_type"] = "TURBOPROP"
    elif "piston" in engine_type_str:
        result["engine_type"] = "PISTON"
    else:
        result["engine_type"] = "JET"  # Default assumption
    
    # Engine count inference
    model_name = (result.get("model") or "").upper()
    if any(term in model_name for term in ["A340", "B744", "747", "A380"]):
        result["engine_count"] = 4
    elif any(term in model_name for term in ["DC-10", "MD-11", "L-1011"]):
        result["engine_count"] = 3
    elif result["engine_type"] in ["JET", "TURBOPROP"]:
        result["engine_count"] = 2
    else:
        result["engine_count"] = 1
    
    # Derive wake category from MTOW (ICAO standards)
    mtow_kg = result.get("mtow_kg")
    if mtow_kg:
        if mtow_kg >= 560000:
            result["wake"] = "J"  # Super
        elif mtow_kg >= 136000:
            result["wake"] = "H"  # Heavy
        elif mtow_kg >= 7000:
            result["wake"] = "M"  # Medium
        else:
            result["wake"] = "L"  # Light
    
    # Derive climb rate (simple heuristic)
    engine_type = result.get("engine_type")
    if engine_type and mtow_kg:
        if engine_type == "JET":
            base = 2500
        elif engine_type == "TURBOPROP":
            base = 1800
        elif engine_type == "PISTON":
            base = 1200
        else:
            base = 2000
        
        # Adjust for weight: heavier aircraft climb slower
        adjust = (80000 - mtow_kg) / 80000
        adjust = max(-0.4, min(0.4, adjust))  # Clamp to ±40%
        
        result["climb_rate_fpm"] = round(base * (1 + adjust))
    
    return result


def fetch_by_model(manufacturer: str, model: str) -> Optional[Dict]:
    """
    Fetch aircraft data from AeroDataBox by manufacturer and model.
    
    Args:
        manufacturer: Aircraft manufacturer
        model: Aircraft model name
    
    Returns:
        Normalized aircraft record or None
    """
    if not manufacturer or not model:
        return None
    
    api_key = os.getenv(API_KEY_ENV)
    api_host = os.getenv(API_HOST_ENV)
    
    if not api_key or not api_host:
        logger.debug(f"AeroDataBox credentials not found. Set {API_KEY_ENV} and {API_HOST_ENV} environment variables.")
        return None
    
    # Check cache first
    cache_path = _get_cache_path(manufacturer, model)
    cached_data = _load_from_cache(cache_path)
    if cached_data is not None:
        return _normalize_aerodatabox_response(cached_data)
    
    # Make API request
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host
    }
    
    # URL encode manufacturer and model
    url = f"{API_BASE_URL}/{quote(manufacturer)}/{quote(model)}"
    
    api_data = _make_api_request(url, headers)
    
    if api_data:
        # Cache successful response
        _save_to_cache(cache_path, api_data)
        return _normalize_aerodatabox_response(api_data)
    else:
        # Cache empty result to avoid repeated failed queries
        _save_to_cache(cache_path, {})
        return None
