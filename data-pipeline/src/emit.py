"""
Data emission module - uses API Ninjas to enrich aircraft types and writes output files.
"""

import json
import os
import sys
import logging
import csv
from datetime import datetime, timezone
from typing import List, Set, Dict, Any
from .models import TypeSpec, Airline, Dimensions, EngineSpec
from .sources.apininjas import fetch_by_model, normalize, lookup_from_icao_guess
from .sources.aerodatabox import fetch_by_model as aerodatabox_fetch_by_model
from .sources.ourairports import get_all_ourairports_data, get_type_enrichment_map
from .sources.airlines import get_airlines

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_icao_codes() -> Set[str]:
    """
    Collect ICAO type codes from available sources.
    Priority: existing dist/aircraft_types.json, then planes.dat, then OurAirports.
    """
    icao_codes = set()
    
    # 1. Try to load from existing dist/aircraft_types.json (for rebuilds)
    dist_file = "dist/aircraft_types.json"
    if os.path.exists(dist_file):
        try:
            with open(dist_file, 'r') as f:
                data = json.load(f)
            for item in data:
                if item.get("icao_type"):
                    icao_codes.add(item["icao_type"])
            logger.info(f"Loaded {len(icao_codes)} ICAO codes from existing {dist_file}")
        except Exception as e:
            logger.warning(f"Failed to load existing aircraft types: {e}")
    
    # 2. Load from planes.dat (OpenFlights)
    planes_file = "cache/planes.dat"
    if os.path.exists(planes_file):
        try:
            with open(planes_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3 and row[2].strip():
                        icao = row[2].strip().upper()
                        if icao not in ("\\N", "NULL", ""):
                            icao_codes.add(icao)
            logger.info(f"Added ICAO codes from planes.dat, total: {len(icao_codes)}")
        except Exception as e:
            logger.warning(f"Failed to load planes.dat: {e}")
    
    # 3. Add from OurAirports data
    try:
        ourairports_data = get_all_ourairports_data()
        for icao in ourairports_data.keys():
            icao_codes.add(icao)
        logger.info(f"Added ICAO codes from OurAirports, total: {len(icao_codes)}")
    except Exception as e:
        logger.warning(f"Failed to load OurAirports data: {e}")
    
    if not icao_codes:
        logger.error("No ICAO codes found from any source")
        sys.exit(2)
    
    return icao_codes


def join_aircraft_data() -> List[TypeSpec]:
    """
    Join aircraft data from multiple sources with API Ninjas enrichment.
    """
    print("Collecting ICAO type codes...")
    icao_codes = collect_icao_codes()
    logger.info(f"Found {len(icao_codes)} unique ICAO type codes")
    
    # Check API keys
    api_ninjas_key = os.getenv("API_NINJAS_KEY")
    aerodatabox_key = os.getenv("AERODATABOX_KEY")
    aerodatabox_host = os.getenv("AERODATABOX_HOST")
    
    api_ninjas_enabled = api_ninjas_key and api_ninjas_key != "your_api_key_here"
    aerodatabox_enabled = aerodatabox_key and aerodatabox_host
    
    if api_ninjas_enabled:
        print("API Ninjas enrichment enabled")
    if aerodatabox_enabled:
        print("AeroDataBox enrichment enabled")
    
    if not api_ninjas_enabled and not aerodatabox_enabled:
        logger.warning("No API keys configured. Skipping API enrichment.")
    
    # Load OurAirports enrichment data
    print("Loading OurAirports enrichment data...")
    ourairports_data = get_all_ourairports_data()
    enrich_map = get_type_enrichment_map()
    
    # Build TypeSpec objects
    enriched_types = []
    api_ninjas_success_count = 0
    aerodatabox_success_count = 0
    ourairports_enriched = 0
    fallback_count = 0
    
    for icao in icao_codes:
        # Start with basic TypeSpec
        type_spec = {
            "icao_type": icao,
            "wake": None,
            "engines": None,
            "dimensions": None,
            "mtow_kg": None,
            "climb_rate_fpm": None,
            "notes": None,
            # New enriched fields
            "max_speed_kts": None,
            "cruise_speed_kts": None,
            "ceiling_ft": None,
            "range_nm": None,
            "takeoff_ground_run_ft": None,
            "landing_ground_roll_ft": None,
            "engine_thrust_lbf": None,
        }
        
        # Try API enrichment (API Ninjas first, then AeroDataBox)
        if api_ninjas_enabled or aerodatabox_enabled:
            try:
                # Generate manufacturer + model guess from ICAO
                guess = lookup_from_icao_guess(icao)
                if guess:
                    manufacturer = guess.get("manufacturer")
                    model = guess.get("model")
                    
                    # Step 1: Try API Ninjas first
                    if api_ninjas_enabled:
                        api_record = fetch_by_model(manufacturer, model)
                        if api_record:
                            # Normalize the API response
                            normalized = normalize(api_record)
                            
                            # Merge into type_spec (don't overwrite non-null with null)
                            for key, value in normalized.items():
                                if value is not None and type_spec.get(key) is None:
                                    type_spec[key] = value
                            
                            api_ninjas_success_count += 1
                            logger.debug(f"API Ninjas enriched {icao}: {manufacturer} {model}")
                    
                    # Step 2: Try AeroDataBox to fill gaps
                    if aerodatabox_enabled:
                        aerodatabox_record = aerodatabox_fetch_by_model(manufacturer, model)
                        if aerodatabox_record:
                            # Merge AeroDataBox data (only fill missing fields)
                            for key, value in aerodatabox_record.items():
                                if value is not None and type_spec.get(key) is None:
                                    type_spec[key] = value
                            
                            aerodatabox_success_count += 1
                            logger.debug(f"AeroDataBox enriched {icao}: {manufacturer} {model}")
                        
            except Exception as e:
                logger.warning(f"API enrichment failed for {icao}: {e}")
        
        # Try to enhance with OurAirports data
        oa_data = ourairports_data.get(icao)
        if oa_data:
            # Add dimensions if available
            if not type_spec.get("dimensions") and all([
                oa_data.get("wingspan_m"), 
                oa_data.get("length_m"), 
                oa_data.get("height_m")
            ]):
                type_spec["dimensions"] = {
                    "wingspan_m": oa_data["wingspan_m"],
                    "length_m": oa_data["length_m"],
                    "height_m": oa_data["height_m"]
                }
                ourairports_enriched += 1
            
            # Add MTOW if available
            if not type_spec.get("mtow_kg") and oa_data.get("mtow_kg"):
                type_spec["mtow_kg"] = float(oa_data["mtow_kg"])
        
        # Try enrichment map
        enrich_data = enrich_map.get(icao)
        if enrich_data:
            for key in ["wake", "engines", "dimensions", "mtow_kg"]:
                if not type_spec.get(key) and enrich_data.get(key):
                    type_spec[key] = enrich_data[key]
        
        # Apply fallback data for common aircraft if still missing critical fields
        if not type_spec.get("wake") or not type_spec.get("engines"):
            fallback_data = _get_fallback_data(icao)
            if fallback_data:
                if not type_spec.get("wake") and fallback_data.get("wake"):
                    type_spec["wake"] = fallback_data["wake"]
                if not type_spec.get("engines") and fallback_data.get("engines"):
                    type_spec["engines"] = fallback_data["engines"]
                if not type_spec.get("mtow_kg") and fallback_data.get("mtow_kg"):
                    type_spec["mtow_kg"] = fallback_data["mtow_kg"]
                fallback_count += 1
        
        # Validate that we have required fields
        if not type_spec.get("wake") or not type_spec.get("engines"):
            logger.debug(f"Skipping {icao}: missing wake or engines")
            continue
        
        # Validate engines structure
        engines = type_spec.get("engines")
        if not engines.get("count") or not engines.get("type"):
            logger.debug(f"Skipping {icao}: incomplete engine info")
            continue
        
        # Create TypeSpec object
        try:
            engines_spec = EngineSpec(**engines)
            dimensions_spec = None
            if type_spec.get("dimensions"):
                dimensions_spec = Dimensions(**type_spec["dimensions"])
            
            enriched_type = TypeSpec(
                icao_type=icao,
                wake=type_spec["wake"],
                engines=engines_spec,
                dimensions=dimensions_spec,
                mtow_kg=type_spec.get("mtow_kg"),
                climb_rate_fpm=type_spec.get("climb_rate_fpm"),
                notes=type_spec.get("notes"),
                # New enriched fields
                max_speed_kts=type_spec.get("max_speed_kts"),
                cruise_speed_kts=type_spec.get("cruise_speed_kts"),
                ceiling_ft=type_spec.get("ceiling_ft"),
                range_nm=type_spec.get("range_nm"),
                takeoff_ground_run_ft=type_spec.get("takeoff_ground_run_ft"),
                landing_ground_roll_ft=type_spec.get("landing_ground_roll_ft"),
                engine_thrust_lbf=type_spec.get("engine_thrust_lbf"),
            )
            
            enriched_types.append(enriched_type)
            
        except Exception as e:
            logger.warning(f"Failed to create TypeSpec for {icao}: {e}")
            continue
    
    # Log statistics
    logger.info(f"Successfully enriched {len(enriched_types)} aircraft types")
    logger.info(f"API Ninjas provided data for {api_ninjas_success_count} types")
    logger.info(f"AeroDataBox provided data for {aerodatabox_success_count} types")
    logger.info(f"OurAirports enriched {ourairports_enriched} types with dimensions")
    logger.info(f"Fallback data used for {fallback_count} types")
    
    # Validation
    if len(enriched_types) < 10:
        logger.error(f"Too few valid aircraft types: {len(enriched_types)}")
        sys.exit(2)
    
    print(f"Successfully enriched {len(enriched_types)} aircraft types")
    return enriched_types


def _get_fallback_data(icao: str) -> Dict[str, Any]:
    """Get fallback data for common aircraft types."""
    fallback_data = {
        # Heavy aircraft
        "A380": {"wake": "J", "engines": {"count": 4, "type": "JET"}, "mtow_kg": 560000},
        "A388": {"wake": "J", "engines": {"count": 4, "type": "JET"}, "mtow_kg": 560000},
        "B747": {"wake": "H", "engines": {"count": 4, "type": "JET"}, "mtow_kg": 396890},
        "B744": {"wake": "H", "engines": {"count": 4, "type": "JET"}, "mtow_kg": 396890},
        "B748": {"wake": "H", "engines": {"count": 4, "type": "JET"}, "mtow_kg": 448000},
        "B777": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 351534},
        "B77W": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 351534},
        "B77L": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 347450},
        "B787": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 227930},
        "B788": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 227930},
        "B789": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 254011},
        "A350": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 280000},
        "A359": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 280000},
        "A330": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 242000},
        "A332": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 242000},
        "A333": {"wake": "H", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 242000},
        
        # Medium aircraft
        "A320": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 78000},
        "A20N": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 79000},
        "A321": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 97000},
        "A21N": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 97000},
        "A319": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 75000},
        "B737": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 70535},
        "B738": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 79016},
        "B739": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 85139},
        "B38M": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 82191},
        "B39M": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 88415},
        "E190": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 51800},
        "E195": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 61200},
        "CRJ7": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 36500},
        "CRJ9": {"wake": "M", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 36500},
        "AT72": {"wake": "M", "engines": {"count": 2, "type": "TURBOPROP"}, "mtow_kg": 23000},
        "AT76": {"wake": "M", "engines": {"count": 2, "type": "TURBOPROP"}, "mtow_kg": 23000},
        
        # Light aircraft
        "CRJ2": {"wake": "L", "engines": {"count": 2, "type": "JET"}, "mtow_kg": 24000},
        "DH8D": {"wake": "L", "engines": {"count": 2, "type": "TURBOPROP"}, "mtow_kg": 29950},
        "C172": {"wake": "L", "engines": {"count": 1, "type": "PISTON"}, "mtow_kg": 1157},
        "C208": {"wake": "L", "engines": {"count": 1, "type": "TURBOPROP"}, "mtow_kg": 3990},
    }
    return fallback_data.get(icao)


def write_aircraft_types(types: List[TypeSpec], output_dir: str = "dist"):
    """Write aircraft types to JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert to dict format for JSON serialization
    types_data = [type_spec.model_dump() for type_spec in types]
    
    output_file = os.path.join(output_dir, "aircraft_types.json")
    with open(output_file, 'w') as f:
        json.dump(types_data, f, indent=2)
    
    print(f"Written {len(types)} aircraft types to {output_file}")


def write_airlines(airlines: List[Airline], output_dir: str = "dist"):
    """Write airlines to JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert to dict format for JSON serialization
    airlines_data = [airline.model_dump() for airline in airlines]
    
    output_file = os.path.join(output_dir, "airlines.json")
    with open(output_file, 'w') as f:
        json.dump(airlines_data, f, indent=2)
    
    print(f"Written {len(airlines)} airlines to {output_file}")


def write_metadata(aircraft_count: int, airline_count: int, output_dir: str = "dist"):
    """Write build metadata to JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    
    metadata = {
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "aircraft_types_count": aircraft_count,
        "airlines_count": airline_count,
        "version": "1.0.0",
        "description": "ATC Data Pipeline - Aircraft types and airlines data"
    }
    
    output_file = os.path.join(output_dir, "meta.json")
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Written metadata to {output_file}")


def main():
    """Main emission function."""
    print("Starting ATC data pipeline emission...")
    
    # Join aircraft data using API Ninjas and other sources
    aircraft_types = join_aircraft_data()
    
    # Load airlines
    print("Loading airlines data...")
    airlines = get_airlines()
    
    # Write output files
    write_aircraft_types(aircraft_types)
    write_airlines(airlines)
    write_metadata(len(aircraft_types), len(airlines))
    
    print("Data pipeline emission completed successfully!")
    print(f"Generated {len(aircraft_types)} aircraft types and {len(airlines)} airlines")
    
    # Final summary with counts
    logger.info(f"Final counts: {len(aircraft_types)} aircraft types, {len(airlines)} airlines")


if __name__ == "__main__":
    main()