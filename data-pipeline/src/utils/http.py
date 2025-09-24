import os
import time
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_env_timeout() -> int:
    """Get HTTP timeout from environment variable."""
    return int(os.getenv("HTTP_TIMEOUT", "30"))

def get_rate_limit_qps() -> float:
    """Get rate limit QPS from environment variable."""
    return float(os.getenv("RATE_LIMIT_QPS", "0.5"))

def request_json(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
    retries: int = 3,
    backoff_factor: float = 1.0
) -> Optional[Dict[str, Any]]:
    """
    Make HTTP request with retries and rate limiting.
    
    Args:
        url: Request URL
        method: HTTP method (default: GET)
        headers: Request headers
        params: Query parameters
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        backoff_factor: Backoff multiplier for retries
        
    Returns:
        JSON response data or None if failed
    """
    if timeout is None:
        timeout = get_env_timeout()
    
    if headers is None:
        headers = {}
    
    # Rate limiting
    qps = get_rate_limit_qps()
    if qps > 0:
        time.sleep(1.0 / qps)
    
    for attempt in range(retries + 1):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=timeout
            )
            
            # Handle rate limiting (429) and server errors (5xx)
            if response.status_code == 429:
                if attempt < retries:
                    wait_time = backoff_factor * (2 ** attempt) + 2  # Add extra 2 seconds
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limited after {retries} retries")
                    return None
            
            elif 500 <= response.status_code < 600:
                if attempt < retries:
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Server error {response.status_code}, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Server error {response.status_code} after {retries} retries")
                    return None
            
            elif response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"HTTP {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Request failed: {e}, waiting {wait_time}s before retry {attempt + 1}")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"Request failed after {retries} retries: {e}")
                return None
    
    return None
