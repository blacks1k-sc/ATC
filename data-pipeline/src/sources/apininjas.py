"""
API Ninjas Aircraft API integration module.

This module provides functions to fetch aircraft data from API Ninjas,
with caching, rate limiting, and data normalization.
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
API_BASE_URL = "https://api.api-ninjas.com/v1/aircraft"
API_KEY_ENV = "API_NINJAS_KEY"
CACHE_DIR = Path("cache/api_ninjas")
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


def _slugify_params(params: Dict[str, str]) -> str:
    """Create a stable cache key from request parameters."""
    # Sort params for consistent keys
    sorted_params = sorted(params.items())
    key_parts = []
    for k, v in sorted_params:
        # Slugify the value
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', str(v).strip())
        key_parts.append(f"{k}_{slug}")
    return "_".join(key_parts)


def _get_cache_path(params: Dict[str, str]) -> Path:
    """Get cache file path for given parameters."""
    cache_key = _slugify_params(params)
    return CACHE_DIR / f"aircraft_{cache_key}.json"


def _load_from_cache(cache_path: Path) -> Optional[List[Dict]]:
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


def _save_to_cache(cache_path: Path, data: List[Dict]):
    """Save data to cache."""
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Cached: {cache_path.name}")
    except Exception as e:
        logger.warning(f"Failed to save cache {cache_path}: {e}")


def _request(params: Dict[str, str]) -> List[Dict]:
    """
    Make API request to API Ninjas with caching and rate limiting.
    
    Args:
        params: Query parameters (manufacturer, model, etc.)
    
    Returns:
        List of aircraft records from API
    """
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        logger.error(f"API key not found. Set {API_KEY_ENV} environment variable.")
        return []
    
    # Check cache first
    cache_path = _get_cache_path(params)
    cached_data = _load_from_cache(cache_path)
    if cached_data is not None:
        return cached_data
    
    # Make API request with retries
    headers = {"X-Api-Key": api_key}
    
    for attempt in range(MAX_RETRIES):
        try:
            _rate_limit()
            
            logger.debug(f"API request (attempt {attempt + 1}): {params}")
            response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                # Cache successful response
                _save_to_cache(cache_path, data)
                return data
            
            elif response.status_code == 429:
                # Rate limited - backoff
                if attempt < MAX_RETRIES - 1:
                    backoff_time = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {backoff_time}s")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error("Max retries exceeded for rate limiting")
                    return []
            
            elif response.status_code >= 500:
                # Server error - retry
                if attempt < MAX_RETRIES - 1:
                    backoff_time = 2 ** attempt
                    logger.warning(f"Server error {response.status_code}, retrying in {backoff_time}s")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for server error {response.status_code}")
                    return []
            
            else:
                # Other 4xx errors - don't retry
                logger.warning(f"API request failed: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                backoff_time = 2 ** attempt
                logger.warning(f"Request exception: {e}, retrying in {backoff_time}s")
                time.sleep(backoff_time)
                continue
            else:
                logger.error(f"Max retries exceeded for request exception: {e}")
                return []
    
    return []


def _clean_model_name(model: str) -> str:
    """Clean model name by removing dashes and extra spaces."""
    return re.sub(r'[-_\s]+', ' ', model.strip())


def fetch_by_model(manufacturer: Optional[str] = None, model: str = None) -> Optional[Dict]:
    """
    Fetch aircraft data by manufacturer and model with fallback strategies.
    
    Args:
        manufacturer: Aircraft manufacturer (optional)
        model: Aircraft model name
    
    Returns:
        First matching aircraft record or None
    """
    if not model:
        return None
    
    # Strategy 1: Try exact model with manufacturer
    if manufacturer:
        params = {"manufacturer": manufacturer, "model": model}
        results = _request(params)
        if results:
            logger.debug(f"Found {len(results)} results for {manufacturer} {model}")
            return results[0]
    
    # Strategy 2: Try model only
    params = {"model": model}
    results = _request(params)
    if results:
        logger.debug(f"Found {len(results)} results for model {model}")
        return results[0]
    
    # Strategy 3: Try cleaned model name
    cleaned_model = _clean_model_name(model)
    if cleaned_model != model:
        params = {"model": cleaned_model}
        results = _request(params)
        if results:
            logger.debug(f"Found {len(results)} results for cleaned model {cleaned_model}")
            return results[0]
    
    logger.debug(f"No results found for {manufacturer} {model}")
    return None


def normalize(record: Dict) -> Dict:
    """
    Normalize API record to our schema with unit conversions and derivations.
    
    Args:
        record: Raw API response record
    
    Returns:
        Normalized record with our field names and units
    """
    if not record:
        return {}
    
    result = {}
    
    # Basic string fields
    result["manufacturer"] = record.get("manufacturer")
    result["model"] = record.get("model")
    
    # Unit conversions
    try:
        if record.get("gross_weight_lbs"):
            result["mtow_kg"] = float(record["gross_weight_lbs"]) * 0.45359237
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("max_speed_knots"):
            result["max_speed_kts"] = float(record["max_speed_knots"])
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("cruise_speed_knots"):
            result["cruise_speed_kts"] = float(record["cruise_speed_knots"])
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("ceiling_ft"):
            result["ceiling_ft"] = float(record["ceiling_ft"])
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("range_nautical_miles"):
            result["range_nm"] = float(record["range_nautical_miles"])
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("takeoff_ground_run_ft"):
            result["takeoff_ground_run_ft"] = float(record["takeoff_ground_run_ft"])
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("landing_ground_roll_ft"):
            result["landing_ground_roll_ft"] = float(record["landing_ground_roll_ft"])
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("engine_thrust_lb_ft"):
            result["engine_thrust_lbf"] = float(record["engine_thrust_lb_ft"])
    except (ValueError, TypeError):
        pass
    
    # Dimensions (convert feet to meters)
    dimensions = {}
    try:
        if record.get("length_ft"):
            dimensions["length_m"] = float(record["length_ft"]) * 0.3048
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("wing_span_ft"):
            dimensions["wingspan_m"] = float(record["wing_span_ft"]) * 0.3048
    except (ValueError, TypeError):
        pass
    
    try:
        if record.get("height_ft"):
            dimensions["height_m"] = float(record["height_ft"]) * 0.3048
    except (ValueError, TypeError):
        pass
    
    if dimensions:
        result["dimensions"] = dimensions
    
    # Engine type normalization
    engine_type_str = record.get("engine_type", "").lower()
    if any(term in engine_type_str for term in ["jet", "propjet"]):
        result["engine_type"] = "JET"
    elif any(term in engine_type_str for term in ["prop", "turboprop"]):
        result["engine_type"] = "TURBOPROP"
    elif "piston" in engine_type_str:
        result["engine_type"] = "PISTON"
    else:
        result["engine_type"] = "JET"  # Default assumption
    
    # Engine count inference (simple heuristic)
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


def lookup_from_icao_guess(icao: str) -> Optional[Dict[str, str]]:
    """
    Translate ICAO code to manufacturer + model guesses.
    
    This is a small heuristic mapping for common aircraft types.
    Keep this minimal and clearly marked as heuristic.
    
    Args:
        icao: ICAO aircraft type code
    
    Returns:
        Dict with 'manufacturer' and 'model' keys, or None
    """
    if not icao:
        return None
    
    icao_upper = icao.upper()
    
    # Heuristic ICAO → manufacturer + model mapping
    # This is intentionally small and conservative
    icao_mappings = {
        # Airbus
        "A320": {"manufacturer": "Airbus", "model": "A320"},
        "A20N": {"manufacturer": "Airbus", "model": "A320neo"},
        "A321": {"manufacturer": "Airbus", "model": "A321"},
        "A21N": {"manufacturer": "Airbus", "model": "A321neo"},
        "A319": {"manufacturer": "Airbus", "model": "A319"},
        "A332": {"manufacturer": "Airbus", "model": "A330-200"},
        "A333": {"manufacturer": "Airbus", "model": "A330-300"},
        "A343": {"manufacturer": "Airbus", "model": "A340-300"},
        "A345": {"manufacturer": "Airbus", "model": "A340-500"},
        "A359": {"manufacturer": "Airbus", "model": "A350-900"},
        "A388": {"manufacturer": "Airbus", "model": "A380-800"},
        
        # Boeing
        "B738": {"manufacturer": "Boeing", "model": "737-800"},
        "B737": {"manufacturer": "Boeing", "model": "737-700"},
        "B739": {"manufacturer": "Boeing", "model": "737-900"},
        "B38M": {"manufacturer": "Boeing", "model": "737 MAX 8"},
        "B39M": {"manufacturer": "Boeing", "model": "737 MAX 9"},
        "B77W": {"manufacturer": "Boeing", "model": "777-300ER"},
        "B772": {"manufacturer": "Boeing", "model": "777-200"},
        "B788": {"manufacturer": "Boeing", "model": "787-8"},
        "B789": {"manufacturer": "Boeing", "model": "787-9"},
        "B744": {"manufacturer": "Boeing", "model": "747-400"},
        "B748": {"manufacturer": "Boeing", "model": "747-8"},
        
        # Embraer
        "E190": {"manufacturer": "Embraer", "model": "E190"},
        "E195": {"manufacturer": "Embraer", "model": "E195"},
        "E170": {"manufacturer": "Embraer", "model": "E170"},
        "E175": {"manufacturer": "Embraer", "model": "E175"},
        
        # ATR
        "AT72": {"manufacturer": "ATR", "model": "ATR 72-500"},
        "AT76": {"manufacturer": "ATR", "model": "ATR 72-600"},
        "AT42": {"manufacturer": "ATR", "model": "ATR 42"},
        
        # Bombardier
        "CRJ2": {"manufacturer": "Bombardier", "model": "CRJ-200"},
        "CRJ7": {"manufacturer": "Bombardier", "model": "CRJ-700"},
        "CRJ9": {"manufacturer": "Bombardier", "model": "CRJ-900"},
        "DH8D": {"manufacturer": "Bombardier", "model": "Dash 8-400"},
        
        # Cessna
        "C172": {"manufacturer": "Cessna", "model": "172"},
        "C208": {"manufacturer": "Cessna", "model": "208"},
        
        # Gulfstream
        "GLF5": {"manufacturer": "Gulfstream", "model": "G550"},
        "GLF6": {"manufacturer": "Gulfstream", "model": "G650"},
    }
    
    return icao_mappings.get(icao_upper)
