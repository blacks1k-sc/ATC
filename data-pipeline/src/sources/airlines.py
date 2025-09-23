"""
Global airlines data loader with real data fetching.
"""

import csv
import os
import requests
import logging
from typing import List, Set, Optional
from ..models import Airline

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_airlines_data(cache_dir: str = "cache") -> str:
    """
    Download global airlines data.
    Returns the path to the cached CSV file.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "airlines.csv")
    
    # Check if we have a cached file
    if os.path.exists(cache_file):
        logger.info(f"Using cached airlines data: {cache_file}")
        return cache_file
    
    # Try to download from various sources
    urls = [
        "https://davidmegginson.github.io/ourairports-data/airlines.csv",
        "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airlines.csv",
        # Alternative sources
        "https://raw.githubusercontent.com/openskies-sh/aircraft-standards/master/data/airlines.csv",
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
    ]
    
    for url in urls:
        try:
            logger.info(f"Attempting to download airlines data from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Successfully downloaded and cached airlines data")
            return cache_file
            
        except Exception as e:
            logger.warning(f"Failed to download from {url}: {e}")
            continue
    
    # If all downloads fail, create a comprehensive sample file for development
    logger.warning("Could not download airlines data. Creating comprehensive sample file for development.")
    sample_data = """icao,iata,name,country
ACA,AC,Air Canada,Canada
WJA,WS,WestJet,Canada
POE,PD,Porter Airlines,Canada
TSC,TS,Air Transat,Canada
SWG,WG,Sunwing Airlines,Canada
FLE,F8,Flair Airlines,Canada
WSW,WO,Swoop,Canada
UAL,UA,United Airlines,United States
AAL,AA,American Airlines,United States
DAL,DL,Delta Air Lines,United States
SWA,WN,Southwest Airlines,United States
JBU,B6,JetBlue Airways,United States
ASA,AS,Alaska Airlines,United States
NKS,NK,Spirit Airlines,United States
FFT,F9,Frontier Airlines,United States
HAL,HA,Hawaiian Airlines,United States
SKW,OO,SkyWest Airlines,United States
RPA,YX,Republic Airways,United States
ASH,YV,Mesa Airlines,United States
ENY,MQ,Envoy Air,United States
PDT,9E,Piedmont Airlines,United States
JIA,OH,PSA Airlines,United States
BAW,BA,British Airways,United Kingdom
DLH,LH,Lufthansa,Germany
AFR,AF,Air France,France
KLM,KL,KLM Royal Dutch Airlines,Netherlands
IBE,IB,Iberia,Spain
SWR,LX,Swiss International Air Lines,Switzerland
AUA,OS,Austrian Airlines,Austria
SAS,SK,SAS Scandinavian Airlines,Sweden
FIN,AY,Finnair,Finland
EIN,EI,Aer Lingus,Ireland
JAL,JL,Japan Airlines,Japan
ANA,NH,All Nippon Airways,Japan
KAL,KE,Korean Air,South Korea
AAR,OZ,Asiana Airlines,South Korea
CES,MU,China Eastern Airlines,China
CSN,CZ,China Southern Airlines,China
CCA,CA,Air China,China
CPA,CX,Cathay Pacific,Hong Kong
SIA,SQ,Singapore Airlines,Singapore
THA,TG,Thai Airways,Thailand
UAE,EK,Emirates,United Arab Emirates
QTR,QR,Qatar Airways,Qatar
ETD,EY,Etihad Airways,United Arab Emirates
THY,TK,Turkish Airlines,Turkey
AMX,AM,Aeromexico,Mexico
LAN,LA,LATAM Airlines,Chile
AVA,AV,Avianca,Colombia
CMP,CM,Copa Airlines,Panama
ETH,ET,Ethiopian Airlines,Ethiopia
SAA,SA,South African Airways,South Africa
KQA,KQ,Kenya Airways,Kenya
QFA,QF,Qantas,Australia
VOZ,VA,Virgin Australia,Australia
FDX,FX,FedEx,United States
UPS,5X,UPS Airlines,United States
DHK,D0,DHL Aviation,Germany
CLX,CV,Cargolux,Luxembourg"""
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(sample_data)
    
    return cache_file


def load_airlines_data(csv_path: Optional[str] = None) -> List[Airline]:
    """
    Load global airlines data from CSV.
    """
    if csv_path is None:
        # Check environment variable
        csv_path = os.getenv("AIRLINES_CSV")
        if csv_path is None:
            csv_path = download_airlines_data()
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Airlines CSV file not found: {csv_path}")
    
    logger.info(f"Loading airlines data from: {csv_path}")
    
    airlines = []
    seen_icao: Set[str] = set()
    seen_iata_name: Set[tuple] = set()
    skipped = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Try to detect delimiter
        sample = f.read(1024)
        f.seek(0)
        delimiter = ',' if ',' in sample else '\t'
        
        # Try to detect if CSV has headers by checking if first row looks like headers
        first_line = f.readline().strip()
        f.seek(0)
        
        # Check if first line contains typical header keywords
        has_header = any(keyword in first_line.lower() for keyword in ['icao', 'iata', 'name', 'country', 'airline'])
        
        if has_header:
            # Use DictReader for header-based format
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Get fields with flexible field name matching
                    icao = None
                    iata = None
                    name = None
                    country = None
                    
                    # Header-based format
                    for field in ['icao', 'ICAO', 'icao_code', 'ICAO_Code']:
                        if field in row and row[field] and row[field] != '\\N':
                            icao = row[field].strip().upper()
                            break
                    
                    for field in ['iata', 'IATA', 'iata_code', 'IATA_Code']:
                        if field in row and row[field] and row[field] != '\\N':
                            iata = row[field].strip().upper()
                            break
                    
                    for field in ['name', 'Name', 'airline_name', 'Airline_Name']:
                        if field in row and row[field] and row[field] != '\\N':
                            name = row[field].strip()
                            break
                    
                    for field in ['country', 'Country', 'country_name', 'Country_Name']:
                        if field in row and row[field] and row[field] != '\\N':
                            country = row[field].strip()
                            break
                    
                    # Validate required fields
                    if not icao or len(icao) != 3:
                        logger.warning(f"Row {row_num}: Invalid ICAO code: {icao}")
                        skipped += 1
                        continue
                    
                    if not name or len(name) < 2:
                        logger.warning(f"Row {row_num}: Invalid airline name: {name}")
                        skipped += 1
                        continue
                    
                    # Validate IATA if present
                    if iata and len(iata) != 2:
                        logger.warning(f"Row {row_num}: Invalid IATA code: {iata}")
                        iata = None  # Set to None if invalid
                    
                    # De-duplicate by ICAO first
                    if icao in seen_icao:
                        logger.debug(f"Row {row_num}: Duplicate ICAO code: {icao}")
                        skipped += 1
                        continue
                    
                    # De-duplicate by (IATA, name) if ICAO is not available
                    if not iata:
                        iata_name_key = (None, name)
                    else:
                        iata_name_key = (iata, name)
                    
                    if iata_name_key in seen_iata_name:
                        logger.debug(f"Row {row_num}: Duplicate IATA/name combination: {iata_name_key}")
                        skipped += 1
                        continue
                    
                    # Create airline record
                    airline = Airline(
                        name=name,
                        icao=icao,
                        iata=iata,
                        country=country
                    )
                    
                    airlines.append(airline)
                    seen_icao.add(icao)
                    seen_iata_name.add(iata_name_key)
                    
                except Exception as e:
                    logger.warning(f"Row {row_num}: Error processing row: {e}")
                    skipped += 1
                    continue
        else:
            # Use regular reader for positional format (OurAirports format)
            reader = csv.reader(f, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Positional format (OurAirports format)
                    # Column 0: ID, 1: Name, 2: Alias, 3: IATA, 4: ICAO, 5: Callsign, 6: Country, 7: Active
                    if len(row) >= 7:
                        name = row[1].strip() if row[1] and row[1] != '\\N' else None
                        iata = row[3].strip().upper() if row[3] and row[3] != '\\N' and row[3] != '-' else None
                        icao = row[4].strip().upper() if row[4] and row[4] != '\\N' and row[4] != 'N/A' else None
                        country = row[6].strip() if row[6] and row[6] != '\\N' else None
                        
                        # Validate required fields
                        if not icao or len(icao) != 3:
                            logger.warning(f"Row {row_num}: Invalid ICAO code: {icao}")
                            skipped += 1
                            continue
                        
                        if not name or len(name) < 2:
                            logger.warning(f"Row {row_num}: Invalid airline name: {name}")
                            skipped += 1
                            continue
                        
                        # Validate IATA if present
                        if iata and len(iata) != 2:
                            logger.warning(f"Row {row_num}: Invalid IATA code: {iata}")
                            iata = None  # Set to None if invalid
                        
                        # De-duplicate by ICAO first
                        if icao in seen_icao:
                            logger.debug(f"Row {row_num}: Duplicate ICAO code: {icao}")
                            skipped += 1
                            continue
                        
                        # De-duplicate by (IATA, name) if ICAO is not available
                        if not iata:
                            iata_name_key = (None, name)
                        else:
                            iata_name_key = (iata, name)
                        
                        if iata_name_key in seen_iata_name:
                            logger.debug(f"Row {row_num}: Duplicate IATA/name combination: {iata_name_key}")
                            skipped += 1
                            continue
                        
                        # Create airline record
                        airline = Airline(
                            name=name,
                            icao=icao,
                            iata=iata,
                            country=country
                        )
                        
                        airlines.append(airline)
                        seen_icao.add(icao)
                        seen_iata_name.add(iata_name_key)
                    else:
                        logger.warning(f"Row {row_num}: Insufficient columns: {len(row)}")
                        skipped += 1
                        continue
                        
                except Exception as e:
                    logger.warning(f"Row {row_num}: Error processing row: {e}")
                    skipped += 1
                    continue
    
    logger.info(f"Loaded {len(airlines)} airlines, skipped {skipped} invalid/duplicate rows")
    return airlines


def get_airlines() -> List[Airline]:
    """
    Get the global airlines list.
    """
    return load_airlines_data()
