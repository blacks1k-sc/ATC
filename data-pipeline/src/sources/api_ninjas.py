"""
API Ninjas Aircraft API integration module.

This module provides a typed client for the API Ninjas Aircraft API with:
- Proper caching to disk
- Exponential backoff with jitter for retries
- Response normalization to our TypeSpec format
- Wake turbulence and climb rate derivation
- Engine type normalization and count inference
"""

import os
import json
import time
import random
import requests
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import quote
import re

from ..models import TypeSpec, Dimensions, EngineSpec

logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "https://api.api-ninjas.com/v1/aircraft"
API_KEY_ENV = "API_NINJAS_KEY"
CACHE_DIR = Path("cache/api_ninjas")
MIN_REQUEST_INTERVAL = 0.5  # Minimum seconds between requests
MAX_RETRIES = 5
BASE_BACKOFF = 1.0  # Base backoff time in seconds

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


def _make_api_request(url: str, headers: Dict[str, str], params: Dict[str, str]) -> Optional[List[Dict]]:
    """Make API request with exponential backoff retry logic."""
    _rate_limit()
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"API request (attempt {attempt + 1}): {url}")
            response = requests.get(url, headers=headers, params=params, timeout=20)
            
            if response.status_code == 200:
                return response.json()
            
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff with jitter
                    backoff_time = BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Server error {response.status_code}, retrying in {backoff_time:.2f}s")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for {response.status_code}")
                    return None
            
            # For other 4xx errors, don't retry
            logger.warning(f"API request failed: {response.status_code} - {response.text}")
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                backoff_time = BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Request exception: {e}, retrying in {backoff_time:.2f}s")
                time.sleep(backoff_time)
                continue
            else:
                logger.error(f"Max retries exceeded for request exception: {e}")
                return None
    
    return None


def _get_cache_path(model: Optional[str] = None, manufacturer: Optional[str] = None) -> Path:
    """Get cache file path for given model or manufacturer."""
    if model:
        # Slugify model name for cache key
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', model.strip())
        cache_key = f"model_{slug}.json"
    elif manufacturer:
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', manufacturer.strip())
        cache_key = f"manufacturer_{slug}.json"
    else:
        raise ValueError("Either model or manufacturer must be provided")
    
    return CACHE_DIR / cache_key


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


def normalize_engine_type(s: Optional[str]) -> str:
    """Normalize engine type string to our enum values."""
    s_up = (s or '').strip().upper()
    if any(k in s_up for k in ['TURBOFAN', 'TURBOJET', 'JET']):
        return 'JET'
    if any(k in s_up for k in ['TURBOPROP', 'TURBO-PROP']):
        return 'TURBOPROP'
    if any(k in s_up for k in ['PISTON', 'RECIP']):
        return 'PISTON'
    if 'ELECTRIC' in s_up:
        return 'ELECTRIC'
    return 'OTHER'


def infer_engine_count(engine_type: str, model: str) -> int:
    """Infer engine count from engine type and model name."""
    m = model.upper()
    if 'TRIJET' in m or 'L-1011' in m or 'DC-10' in m or 'MD-11' in m:
        return 3
    if any(t in m for t in ['A340', 'B744', '747', 'IL-86', 'IL-96']):
        return 4
    if engine_type in ['JET', 'TURBOPROP']:
        return 2
    return 1


def _guess_icao_type_from_model(model: str) -> Optional[str]:
    """Guess ICAO type code from model name using regex/token rules."""
    if not model:
        return None
    
    model_upper = model.upper().strip()
    
    # Airbus models
    if re.match(r'A320-?200?$', model_upper) or model_upper == 'A320':
        return 'A320'
    if re.match(r'A321NEO?$', model_upper):
        return 'A21N'
    if re.match(r'A320NEO?$', model_upper):
        return 'A20N'
    if re.match(r'A319$', model_upper):
        return 'A319'
    if re.match(r'A321$', model_upper):
        return 'A321'
    if re.match(r'A330-?200?$', model_upper):
        return 'A332'
    if re.match(r'A330-?300?$', model_upper):
        return 'A333'
    if re.match(r'A340-?300?$', model_upper):
        return 'A343'
    if re.match(r'A340-?500?$', model_upper):
        return 'A345'
    if re.match(r'A350-?900?$', model_upper):
        return 'A359'
    if re.match(r'A380-?800?$', model_upper):
        return 'A388'
    
    # Boeing models
    if re.match(r'B?737-?800?$', model_upper) or re.match(r'737-?800?$', model_upper):
        return 'B738'
    if re.match(r'B?737-?700?$', model_upper) or re.match(r'737-?700?$', model_upper):
        return 'B737'
    if re.match(r'B?737-?900?$', model_upper) or re.match(r'737-?900?$', model_upper):
        return 'B739'
    if re.match(r'737\s*MAX\s*8$', model_upper) or re.match(r'B?737-?8$', model_upper):
        return 'B38M'
    if re.match(r'737\s*MAX\s*9$', model_upper) or re.match(r'B?737-?9$', model_upper):
        return 'B39M'
    if re.match(r'B?777-?300ER?$', model_upper) or re.match(r'777-?300ER?$', model_upper) or model_upper == '77W':
        return 'B77W'
    if re.match(r'B?777-?200?$', model_upper) or re.match(r'777-?200?$', model_upper):
        return 'B772'
    if re.match(r'B?787-?8$', model_upper) or re.match(r'787-?8$', model_upper):
        return 'B788'
    if re.match(r'B?787-?9$', model_upper) or re.match(r'787-?9$', model_upper):
        return 'B789'
    if re.match(r'B?747-?400?$', model_upper) or re.match(r'747-?400?$', model_upper):
        return 'B744'
    if re.match(r'B?747-?800?$', model_upper) or re.match(r'747-?800?$', model_upper):
        return 'B748'
    
    # Embraer models
    if re.match(r'E190$', model_upper):
        return 'E190'
    if re.match(r'E195$', model_upper):
        return 'E195'
    if re.match(r'E170$', model_upper):
        return 'E170'
    if re.match(r'E175$', model_upper):
        return 'E175'
    
    # ATR models
    if re.match(r'ATR\s*72-?600?$', model_upper) or re.match(r'ATR-?72-?600?$', model_upper):
        return 'AT76'
    if re.match(r'ATR\s*72-?500?$', model_upper) or re.match(r'ATR-?72-?500?$', model_upper):
        return 'AT72'
    if re.match(r'ATR\s*42$', model_upper) or re.match(r'ATR-?42$', model_upper):
        return 'AT42'
    
    # Bombardier models
    if re.match(r'CRJ\s*200?$', model_upper) or re.match(r'CRJ-?200?$', model_upper):
        return 'CRJ2'
    if re.match(r'CRJ\s*700?$', model_upper) or re.match(r'CRJ-?700?$', model_upper):
        return 'CRJ7'
    if re.match(r'CRJ\s*900?$', model_upper) or re.match(r'CRJ-?900?$', model_upper):
        return 'CRJ9'
    if re.match(r'DH8D$', model_upper) or re.match(r'DASH\s*8-?400?$', model_upper):
        return 'DH8D'
    
    # Cessna models
    if re.match(r'C172$', model_upper):
        return 'C172'
    if re.match(r'C208$', model_upper):
        return 'C208'
    
    # Default: return None if ambiguous
    return None


def _derive_wake_from_mtow(mtow_kg: Optional[float]) -> Optional[str]:
    """Derive wake turbulence category from MTOW."""
    if mtow_kg is None:
        return None
    
    if mtow_kg >= 560000:
        return 'J'  # Super
    elif mtow_kg >= 136000:
        return 'H'  # Heavy
    elif mtow_kg >= 7000:
        return 'M'  # Medium
    else:
        return 'L'  # Light


def _estimate_climb_rate_fpm(engine_type: str, mtow_kg: Optional[float]) -> Optional[int]:
    """Estimate climb rate in feet per minute."""
    if not engine_type or mtow_kg is None:
        return None
    
    # Base climb rates by engine type
    base_rates = {
        'JET': 2500,
        'TURBOPROP': 1800,
        'PISTON': 900,
        'ELECTRIC': 800,
        'OTHER': 1000
    }
    
    base_fpm = base_rates.get(engine_type, 1000)
    
    # Scale based on weight
    weight_factor = (70000 / max(mtow_kg, 70000)) ** 0.5
    weight_factor = max(0.6, min(1.5, weight_factor))
    
    return int(base_fpm * weight_factor)


def _normalize_api_response(api_data: List[Dict], model: Optional[str] = None) -> List[TypeSpec]:
    """Normalize API response to our TypeSpec format."""
    if not api_data:
        return []
    
    results = []
    
    for aircraft in api_data:
        try:
            # Extract basic fields
            manufacturer = aircraft.get("manufacturer")
            model_name = aircraft.get("model") or model
            engine_type_str = aircraft.get("engine_type")
            
            if not model_name:
                continue
            
            # Normalize engine type
            engine_type = normalize_engine_type(engine_type_str)
            engine_count = infer_engine_count(engine_type, model_name)
            
            # Guess ICAO type
            icao_type = _guess_icao_type_from_model(model_name)
            
            # Parse dimensions
            dimensions = None
            try:
                length_ft = aircraft.get("length_ft")
                wingspan_ft = aircraft.get("wing_span_ft")
                height_ft = aircraft.get("height_ft")
                
                if any([length_ft, wingspan_ft, height_ft]):
                    dimensions = Dimensions(
                        length_m=float(length_ft) * 0.3048 if length_ft else None,
                        wingspan_m=float(wingspan_ft) * 0.3048 if wingspan_ft else None,
                        height_m=float(height_ft) * 0.3048 if height_ft else None
                    )
            except (ValueError, TypeError):
                dimensions = None
            
            # Parse MTOW
            mtow_kg = None
            try:
                gross_weight_lbs = aircraft.get("gross_weight_lbs")
                if gross_weight_lbs:
                    mtow_kg = float(gross_weight_lbs) * 0.453592  # Convert lbs to kg
            except (ValueError, TypeError):
                pass
            
            # Parse other fields
            cruise_speed_kts = None
            try:
                max_speed_knots = aircraft.get("max_speed_knots")
                if max_speed_knots:
                    cruise_speed_kts = float(max_speed_knots)
            except (ValueError, TypeError):
                pass
            
            range_km = None
            try:
                range_nm = aircraft.get("range_nautical_miles")
                if range_nm:
                    range_km = float(range_nm) * 1.852  # Convert nm to km
            except (ValueError, TypeError):
                pass
            
            # Derive wake category
            wake = _derive_wake_from_mtow(mtow_kg)
            
            # Estimate climb rate
            climb_rate_fpm = _estimate_climb_rate_fpm(engine_type, mtow_kg)
            
            # Create TypeSpec
            type_spec = TypeSpec(
                icao_type=icao_type,
                engines=EngineSpec(
                    count=engine_count,
                    type=engine_type
                ),
                wake=wake,
                dimensions=dimensions,
                mtow_kg=int(mtow_kg) if mtow_kg else None,
                climb_rate_fpm=climb_rate_fpm,
                # Store additional metadata in notes
                notes=f"API Ninjas: {manufacturer} {model_name}" if manufacturer else f"API Ninjas: {model_name}"
            )
            
            results.append(type_spec)
            
        except Exception as e:
            logger.warning(f"Failed to normalize aircraft data: {e}")
            continue
    
    return results


def fetch_type_by_model_or_manufacturer(model: Optional[str] = None, manufacturer: Optional[str] = None) -> List[TypeSpec]:
    """
    Fetch aircraft type data from API Ninjas by model or manufacturer.
    
    Args:
        model: Aircraft model name (e.g., "A320-200", "B737-800")
        manufacturer: Aircraft manufacturer name (e.g., "Airbus", "Boeing")
    
    Returns:
        List of TypeSpec objects normalized from API response
    """
    if not model and not manufacturer:
        logger.warning("Either model or manufacturer must be provided")
        return []
    
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        logger.error(f"API key not found. Set {API_KEY_ENV} environment variable.")
        return []
    
    headers = {"X-Api-Key": api_key}
    
    # Determine cache path and check cache first
    cache_path = _get_cache_path(model=model, manufacturer=manufacturer)
    cached_data = _load_from_cache(cache_path)
    if cached_data:
        return _normalize_api_response(cached_data, model)
    
    # Make API request
    params = {}
    if model:
        params["model"] = model
    elif manufacturer:
        params["manufacturer"] = manufacturer
    
    api_data = _make_api_request(API_BASE_URL, headers, params)
    
    if api_data:
        # Cache successful response
        _save_to_cache(cache_path, api_data)
        return _normalize_api_response(api_data, model)
    else:
        # Cache empty result to avoid repeated failed queries
        _save_to_cache(cache_path, [])
        return []
