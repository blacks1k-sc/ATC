import requests
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

AIRLINES_DAT_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"

def download_airlines_data() -> None:
    """Download airlines.dat and convert to JSON."""
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    
    airlines_json_path = cache_dir / "airlines.json"
    if airlines_json_path.exists():
        logger.info("Airlines data already cached")
        return
    
    logger.info("Downloading airlines.dat...")
    try:
        response = requests.get(AIRLINES_DAT_URL, timeout=30)
        response.raise_for_status()
        
        airlines = []
        for line_num, line in enumerate(response.text.split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(',')
            if len(parts) < 8:
                continue
            
            try:
                airline = {
                    "id": int(parts[0]) if parts[0] else None,
                    "name": parts[1].strip('"'),
                    "alias": parts[2].strip('"') if parts[2] else None,
                    "iata": parts[3].strip('"') if parts[3] else None,
                    "icao": parts[4].strip('"') if parts[4] else None,
                    "callsign": parts[5].strip('"') if parts[5] else None,
                    "country": parts[6].strip('"') if parts[6] else None,
                    "active": parts[7].strip('"') == 'Y'
                }
                
                # Only include airlines with valid ICAO codes
                if airline["icao"] and len(airline["icao"]) == 3:
                    airlines.append(airline)
                    
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping invalid airline data at line {line_num}: {e}")
                continue
        
        # Save to JSON
        with open(airlines_json_path, 'w', encoding='utf-8') as f:
            json.dump(airlines, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Downloaded and processed {len(airlines)} airlines")
        
    except Exception as e:
        logger.error(f"Failed to download airlines data: {e}")

def load_airlines() -> List[Dict[str, any]]:
    """Load airlines data from cache."""
    airlines_json_path = Path("cache") / "airlines.json"
    if not airlines_json_path.exists():
        logger.warning("Airlines data not found, downloading...")
        download_airlines_data()
    
    try:
        with open(airlines_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load airlines data: {e}")
        return []
