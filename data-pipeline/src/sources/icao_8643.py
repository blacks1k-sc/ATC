import os
import csv
import requests
from pathlib import Path
from typing import Iterator, Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)

def get_planes_dat_url() -> str:
    """Get planes.dat URL from environment."""
    return os.getenv("PLANES_DAT_URL", "https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat")

def get_icao_8643_csv_path() -> Optional[str]:
    """Get ICAO 8643 CSV path from environment."""
    return os.getenv("ICAO_8643_CSV")

def ensure_fallbacks() -> None:
    """Download fallback data files if not present."""
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    
    # Download planes.dat if not present
    planes_dat_path = cache_dir / "planes.dat"
    if not planes_dat_path.exists():
        logger.info("Downloading planes.dat...")
        try:
            url = get_planes_dat_url()
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(planes_dat_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"Downloaded planes.dat to {planes_dat_path}")
        except Exception as e:
            logger.error(f"Failed to download planes.dat: {e}")
    
    # Copy ICAO 8643 CSV if specified and not present
    icao_csv_path = get_icao_8643_csv_path()
    if icao_csv_path and Path(icao_csv_path).exists():
        target_path = cache_dir / "icao_8643.csv"
        if not target_path.exists():
            logger.info(f"Copying ICAO 8643 CSV to {target_path}")
            try:
                import shutil
                shutil.copy2(icao_csv_path, target_path)
                logger.info("Copied ICAO 8643 CSV")
            except Exception as e:
                logger.error(f"Failed to copy ICAO 8643 CSV: {e}")

def iter_icao_candidates() -> Iterator[Tuple[str, str, str]]:
    """
    Iterate over ICAO type candidates from planes.dat.
    
    Yields:
        Tuple of (icao_type, manufacturer_guess, model_guess)
    """
    planes_dat_path = Path("cache") / "planes.dat"
    if not planes_dat_path.exists():
        logger.warning("planes.dat not found, cannot generate ICAO candidates")
        return
    
    try:
        with open(planes_dat_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse CSV line properly - handle quoted fields
                parts = []
                current_part = ""
                in_quotes = False
                
                for char in line:
                    if char == '"' and not in_quotes:
                        in_quotes = True
                    elif char == '"' and in_quotes:
                        in_quotes = False
                    elif char == ',' and not in_quotes:
                        parts.append(current_part.strip())
                        current_part = ""
                        continue
                    current_part += char
                
                # Add the last part
                if current_part:
                    parts.append(current_part.strip())
                
                if len(parts) < 3:
                    continue
                
                # Extract fields: "Aircraft Name", "IATA Code", "ICAO Code"
                aircraft_name = parts[0].strip('"')
                iata_code = parts[1].strip('"')
                icao_code = parts[2].strip('"')
                
                # Skip if no ICAO code (\\N means null)
                if not icao_code or icao_code == "\\N":
                    continue
                
                # Extract manufacturer and model from aircraft name
                manufacturer_guess, model_guess = _extract_manufacturer_model(aircraft_name)
                
                if manufacturer_guess and model_guess:
                    yield (icao_code, manufacturer_guess, model_guess)
                
    except Exception as e:
        logger.error(f"Error reading planes.dat: {e}")

def _extract_manufacturer_model(aircraft_name: str) -> Tuple[str, str]:
    """
    Extract manufacturer and model from aircraft name.
    
    Examples:
        "Boeing 737" -> ("Boeing", "737")
        "Airbus A320" -> ("Airbus", "A320")
        "Aerospatiale (Nord) 262" -> ("Aerospatiale", "262")
        "Aerospatiale/Alenia ATR 42-300" -> ("ATR", "42-300")
    """
    aircraft_name = aircraft_name.strip()
    
    # Handle complex manufacturer patterns with parentheses and slashes
    complex_patterns = [
        # Aerospatiale variants
        ("Aerospatiale (Nord)", "Aerospatiale"),
        ("Aerospatiale (Sud Aviation)", "Aerospatiale"), 
        ("Aerospatiale/Alenia", "ATR"),
        ("Aerospatiale", "Aerospatiale"),
        
        # British Aerospace variants
        ("British Aerospace (BAC)", "British Aerospace"),
        ("British Aerospace", "British Aerospace"),
        ("BAe", "British Aerospace"),
        
        # McDonnell Douglas variants
        ("McDonnell Douglas", "McDonnell Douglas"),
        ("Douglas", "McDonnell Douglas"),
        
        # Lockheed variants
        ("Lockheed", "Lockheed"),
        
        # De Havilland variants
        ("De Havilland Canada", "De Havilland"),
        ("De Havilland", "De Havilland"),
        
        # Canadair variants
        ("Canadair", "Bombardier"),
        
        # Fairchild variants
        ("Fairchild Dornier", "Fairchild"),
        ("Fairchild", "Fairchild"),
        
        # Gulfstream variants
        ("Gulfstream Aerospace", "Gulfstream"),
        ("Gulfstream/Rockwell", "Gulfstream"),
        ("Gulfstream", "Gulfstream"),
        
        # Harbin variants
        ("Harbin Yunshuji", "Harbin"),
        ("Harbin", "Harbin"),
        
        # Pilatus variants
        ("Pilatus Britten-Norman", "Pilatus"),
        ("Pilatus", "Pilatus"),
        
        # Shorts variants
        ("Shorts", "Shorts"),
        
        # Sikorsky variants
        ("Sikorsky", "Sikorsky"),
        
        # Bell variants
        ("Bell", "Bell"),
        
        # NAMC variants
        ("NAMC", "NAMC"),
        
        # Partenavia variants
        ("Partenavia", "Partenavia"),
        
        # COMAC variants
        ("COMAC", "COMAC"),
        
        # Concorde variants
        ("Concorde", "Concorde"),
        
        # Standard manufacturers
        ("Boeing", "Boeing"),
        ("Airbus", "Airbus"),
        ("Embraer", "Embraer"),
        ("Bombardier", "Bombardier"),
        ("ATR", "ATR"),
        ("Cessna", "Cessna"),
        ("Piper", "Piper"),
        ("Beechcraft", "Beechcraft"),
        ("Dassault", "Dassault"),
        ("Learjet", "Learjet"),
        ("Saab", "Saab"),
        ("Fokker", "Fokker"),
        ("Antonov", "Antonov"),
        ("Ilyushin", "Ilyushin"),
        ("Tupolev", "Tupolev"),
        ("Yakovlev", "Yakovlev"),
        ("Sukhoi", "Sukhoi"),
        ("Avro", "Avro"),
    ]
    
    # Find manufacturer using complex patterns
    manufacturer = "Unknown"
    model = aircraft_name
    
    for pattern, normalized_manufacturer in complex_patterns:
        if aircraft_name.startswith(pattern):
            manufacturer = normalized_manufacturer
            # Extract model (everything after the pattern)
            model = aircraft_name[len(pattern):].strip()
            break
    
    # Clean up model name
    if model:
        # Remove common suffixes that aren't part of the model
        model = model.replace(" series", "").replace(" (above 200 hp)", "").replace(" (up to 180 hp)", "")
        model = model.strip()
    
    return manufacturer, model

def lookup_8643_row(icao_type: str) -> Optional[Dict[str, str]]:
    """
    Look up ICAO type in 8643 CSV if available.
    
    Args:
        icao_type: ICAO type designator
        
    Returns:
        Dictionary with wake, engines info or None if not found
    """
    icao_csv_path = Path("cache") / "icao_8643.csv"
    if not icao_csv_path.exists():
        return None
    
    try:
        with open(icao_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Type Designator", "").strip().upper() == icao_type.upper():
                    return {
                        "wake": row.get("WTC", "").strip(),
                        "engines": row.get("Engines", "").strip(),
                        "engine_type": row.get("Engine Type", "").strip()
                    }
    except Exception as e:
        logger.error(f"Error reading ICAO 8643 CSV: {e}")
    
    return None
