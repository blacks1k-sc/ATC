"""
OurAirports aircraft data loader with real data fetching.
"""

import csv
import os
import requests
import logging
from typing import Dict, List, Optional
from ..models import Dimensions

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_ourairports_data(cache_dir: str = "cache") -> str:
    """
    Download OurAirports aircraft data.
    Returns the path to the cached CSV file.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "ourairports_aircraft.csv")
    
    # Check if we have a cached file
    if os.path.exists(cache_file):
        logger.info(f"Using cached OurAirports data: {cache_file}")
        return cache_file
    
    # Try to download from OurAirports
    urls = [
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat"
        ]
    
    for url in urls:
        try:
            logger.info(f"Attempting to download OurAirports data from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Successfully downloaded and cached OurAirports data")
            return cache_file
            
        except Exception as e:
            logger.warning(f"Failed to download from {url}: {e}")
            continue
    
    # If all downloads fail, create a sample file for development
    logger.warning("Could not download OurAirports data. Creating sample file for development.")
    sample_data = """icao_type,wingspan_m,length_m,height_m,mtow_kg
A20N,35.1,38.0,12.0,79000
A21N,35.1,44.5,12.0,97000
A319,34.1,33.8,11.8,75000
A320,34.1,37.6,11.8,78000
A321,34.1,44.5,11.8,97000
A332,60.3,58.8,17.4,242000
A333,60.3,63.7,16.8,242000
A359,64.8,66.8,17.1,280000
A388,79.8,72.7,24.1,575000
B38M,35.9,39.5,12.3,82190
B39M,35.9,42.2,12.3,88400
B738,35.8,39.5,12.5,79000
B739,35.8,42.1,12.5,85000
B77W,64.8,73.9,18.6,351534
B77L,64.8,63.7,18.6,347450
B788,60.1,56.7,16.9,228000
B789,60.1,62.8,16.9,254000
B744,64.4,70.7,19.4,396890
B748,68.4,76.3,19.4,448000
CRJ2,21.2,26.8,6.2,24040
CRJ7,23.2,32.5,7.2,32000
CRJ9,24.9,36.4,7.5,36500
E170,26.0,29.9,9.7,38000
E175,26.0,31.7,9.7,40200
E190,28.7,36.2,10.3,52000
E195,28.7,38.7,10.3,54000
AT76,27.1,27.2,7.7,23000
DH8D,32.8,25.7,7.5,29948
SF34,21.4,20.8,6.9,13155
C172,11.0,8.2,2.7,1157
BE58,11.5,9.0,3.0,2132
PA28,9.8,7.2,2.4,1157"""
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(sample_data)
    
    return cache_file


def load_ourairports_data(csv_path: Optional[str] = None) -> Dict[str, Dict]:
    """
    Load OurAirports aircraft data with dimensions and MTOW.
    """
    if csv_path is None:
        # Check environment variable
        csv_path = os.getenv("OURAIRPORTS_AIRCRAFT_CSV")
        if csv_path is None:
            csv_path = download_ourairports_data()
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"OurAirports CSV file not found: {csv_path}")
    
    logger.info(f"Loading OurAirports data from: {csv_path}")
    
    aircraft_data = {}
    skipped = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Check if this is planes.dat format (no headers) or OurAirports format (with headers)
        sample = f.read(1024)
        f.seek(0)
        
        # Check if first line looks like a header
        first_line = f.readline().strip()
        f.seek(0)
        
        if 'icao_type' in first_line.lower() or 'wingspan' in first_line.lower():
            # This is OurAirports format with headers
            delimiter = ',' if ',' in sample else '\t'
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Get ICAO type
                    icao_type = None
                    for field in ['icao_type', 'ICAO_Type', 'Type', 'Aircraft Type']:
                        if field in row and row[field]:
                            icao_type = row[field].strip().upper()
                            break
                    
                    if not icao_type or len(icao_type) < 3:
                        logger.warning(f"Row {row_num}: Invalid ICAO type: {icao_type}")
                        skipped += 1
                        continue
                    
                    # Get dimensions for OurAirports format
                    wingspan_m = None
                    length_m = None
                    height_m = None
                    mtow_kg = None
                    
                    # Try different possible field names for dimensions
                    for field in ['wingspan_m', 'Wingspan', 'Wingspan_m', 'wingspan']:
                        if field in row and row[field]:
                            try:
                                wingspan_m = float(row[field])
                            except ValueError:
                                pass
                            break
                    
                    for field in ['length_m', 'Length', 'Length_m', 'length']:
                        if field in row and row[field]:
                            try:
                                length_m = float(row[field])
                            except ValueError:
                                pass
                            break
                    
                    for field in ['height_m', 'Height', 'Height_m', 'height']:
                        if field in row and row[field]:
                            try:
                                height_m = float(row[field])
                            except ValueError:
                                pass
                            break
                    
                    for field in ['mtow_kg', 'MTOW', 'MTOW_kg', 'mtow', 'max_takeoff_weight']:
                        if field in row and row[field]:
                            try:
                                mtow_kg = int(float(row[field]))
                            except ValueError:
                                pass
                            break
                    
                    # Only add if we have at least some data
                    if any([wingspan_m, length_m, height_m, mtow_kg]):
                        aircraft_data[icao_type] = {
                            "wingspan_m": wingspan_m,
                            "length_m": length_m,
                            "height_m": height_m,
                            "mtow_kg": mtow_kg
                        }
                    else:
                        logger.debug(f"Row {row_num}: No dimension data for {icao_type}")
                        skipped += 1
                
                except Exception as e:
                    logger.warning(f"Row {row_num}: Error processing row: {e}")
                    skipped += 1
                    continue
        else:
            # This is planes.dat format (Name, IATA, ICAO) - no headers
            reader = csv.reader(f)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    if len(row) < 3:
                        logger.warning(f"Row {row_num}: Insufficient columns")
                        skipped += 1
                        continue
                    
                    # planes.dat format: Name, IATA, ICAO
                    icao_type = row[2].strip().upper() if len(row) > 2 and row[2] else None
                    
                    if not icao_type or icao_type in ('\\N', 'NULL', ''):
                        logger.warning(f"Row {row_num}: Invalid ICAO type: {icao_type}")
                        skipped += 1
                        continue
                    
                    # For planes.dat format, we don't have dimension data
                    # Just store the ICAO type for reference
                    aircraft_data[icao_type] = {
                        'wingspan_m': None,
                        'length_m': None,
                        'height_m': None,
                        'mtow_kg': None
                    }
                
                except Exception as e:
                    logger.warning(f"Row {row_num}: Error processing row: {e}")
                    skipped += 1
                    continue
    
    logger.info(f"Loaded {len(aircraft_data)} aircraft with dimension data, skipped {skipped} rows")
    return aircraft_data


def get_ourairports_dimensions(icao_type: str) -> Optional[Dimensions]:
    """
    Get aircraft dimensions from OurAirports data.
    """
    data = load_ourairports_data()
    if icao_type in data:
        dims = data[icao_type]
        # Only return if we have all three dimensions
        if all([dims["wingspan_m"], dims["length_m"], dims["height_m"]]):
            return Dimensions(
                wingspan_m=dims["wingspan_m"],
                length_m=dims["length_m"],
                height_m=dims["height_m"]
            )
    return None


def get_ourairports_mtow(icao_type: str) -> Optional[int]:
    """
    Get aircraft MTOW from OurAirports data.
    """
    data = load_ourairports_data()
    if icao_type in data:
        return data[icao_type]["mtow_kg"]
    return None


def get_all_ourairports_data() -> Dict[str, Dict]:
    """
    Get all OurAirports aircraft data.
    """
    return load_ourairports_data()


def get_type_enrichment_map() -> Dict[str, Dict]:
    """
    Returns enrichment map for aircraft types with wake/engines/dimensions/mtow if available.
    
    Returns: { 'A20N': {'wake':'M','engines':{'count':2,'type':'JET'}, 'dimensions': {...}, 'mtow_kg': 79000}, ... }
    Only include keys that are actually known.
    """
    records = load_ourairports_data()
    out = {}
    wake_engine_count = 0
    
    for icao_type, data in records.items():
        if not icao_type:
            continue
        
        entry = {}
        
        # Add wake if available
        if data.get('wake'):
            entry['wake'] = data['wake'].strip().upper()
        
        # Add engines if available
        if data.get('engines'):
            entry['engines'] = data['engines']
        
        # Add dimensions if available
        if data.get('dimensions'):
            entry['dimensions'] = data['dimensions']
        
        # Add MTOW if available
        if data.get('mtow_kg') is not None:
            entry['mtow_kg'] = data['mtow_kg']
        
        # Track types with wake/engine data
        if entry.get('wake') and entry.get('engines'):
            wake_engine_count += 1
        
        if entry:
            out[icao_type] = entry
    
    logger.info(f"OurAirports enrichment map: {len(out)} types, {wake_engine_count} with wake/engine data")
    return out