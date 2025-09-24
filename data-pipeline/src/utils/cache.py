import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_cache_dir() -> Path:
    """Get cache directory path."""
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

def get_cache_ttl_hours() -> int:
    """Get cache TTL from environment variable."""
    return int(os.getenv("CACHE_TTL_HOURS", "72"))

def get_cached_json(key: str) -> Optional[Dict[str, Any]]:
    """
    Get cached JSON data by key.
    
    Args:
        key: Cache key
        
    Returns:
        Cached data or None if not found/expired
    """
    cache_file = get_cache_dir() / "http" / f"{key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        # Check TTL
        ttl_hours = get_cache_ttl_hours()
        if ttl_hours > 0:
            cache_time = data.get('_cache_timestamp', 0)
            current_time = time.time()
            if current_time - cache_time > ttl_hours * 3600:
                logger.debug(f"Cache expired for key: {key}")
                cache_file.unlink()  # Remove expired cache
                return None
        
        logger.debug(f"Cache hit for key: {key}")
        return data.get('data')
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Invalid cache file for key {key}: {e}")
        cache_file.unlink()  # Remove invalid cache
        return None

def set_cached_json(key: str, data: Dict[str, Any], ttl_hours: Optional[int] = None) -> None:
    """
    Set cached JSON data by key.
    
    Args:
        key: Cache key
        data: Data to cache
        ttl_hours: TTL in hours (uses env default if None)
    """
    cache_dir = get_cache_dir() / "http"
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{key}.json"
    
    cache_data = {
        'data': data,
        '_cache_timestamp': time.time()
    }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        logger.debug(f"Cached data for key: {key}")
    except Exception as e:
        logger.error(f"Failed to cache data for key {key}: {e}")
