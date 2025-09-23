"""
CLI for generating synthetic aircraft records.
"""

import json
import os
import random
from datetime import datetime, timezone
from typing import List, Optional
import typer
from .models import AircraftRecord, TypeSpec, Airline, EngineSpec, Dimensions
from .utils.registries import UniquenessRegistry
from .utils.randomizers import AircraftRandomizer
from .utils.geo import GeographicUtils
from .utils.derive import derive_wake_from_mtow, estimate_climb_rate_fpm


def load_aircraft_types(file_path: str = "dist/aircraft_types.json") -> List[TypeSpec]:
    """Load aircraft types from JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Aircraft types file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    types = []
    for item in data:
        # Reconstruct TypeSpec from dict
        engines = EngineSpec(**item["engines"])
        dimensions = None
        if item.get("dimensions"):
            dimensions = Dimensions(**item["dimensions"])
        
        type_spec = TypeSpec(
            icao_type=item["icao_type"],
            wake=item["wake"],
            engines=engines,
            dimensions=dimensions,
            mtow_kg=item.get("mtow_kg"),
            climb_rate_fpm=item.get("climb_rate_fpm"),
            notes=item.get("notes"),
            # New enriched fields
            max_speed_kts=item.get("max_speed_kts"),
            cruise_speed_kts=item.get("cruise_speed_kts"),
            ceiling_ft=item.get("ceiling_ft"),
            range_nm=item.get("range_nm"),
            takeoff_ground_run_ft=item.get("takeoff_ground_run_ft"),
            landing_ground_roll_ft=item.get("landing_ground_roll_ft"),
            engine_thrust_lbf=item.get("engine_thrust_lbf"),
        )
        types.append(type_spec)
    
    return types


def load_airlines(file_path: str = "dist/airlines.json") -> List[Airline]:
    """Load airlines from JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Airlines file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    airlines = []
    for item in data:
        airline = Airline(**item)
        airlines.append(airline)
    
    return airlines


def generate_aircraft_record(
    aircraft_types: List[TypeSpec],
    airlines: List[Airline],
    randomizer: AircraftRandomizer,
    geo_utils: GeographicUtils,
    origin: str = "CYYZ",
    op_category: str = "PASSENGER"
) -> AircraftRecord:
    """Generate a single synthetic aircraft record."""
    
    # Select random airline
    airline = random.choice(airlines)
    
    # Select appropriate aircraft type for airline
    aircraft_type = randomizer.random_aircraft_type_for_airline(airline, aircraft_types)
    
    # Generate unique identifiers
    icao24 = randomizer.random_icao24()
    country = randomizer.random_country_for_airline(airline)
    registration = randomizer.random_registration(country)
    callsign = randomizer.random_callsign(airline)
    flight_number = randomizer.random_flight_number()
    squawk = randomizer.random_squawk()
    
    # Generate route
    origin_airport, destination_airport = geo_utils.random_route(origin)
    
    # Generate flight status and position
    statuses = ["PARKED", "TAXI", "TAKEOFF", "ENROUTE", "APPROACH", "LANDING"]
    status = random.choice(statuses)
    phase = geo_utils.get_flight_phase(status)
    
    lat, lon, altitude, heading, speed = geo_utils.spawn_position(status, origin_airport, destination_airport)
    
    # Generate gate and runway assignments (only for certain statuses)
    gate_assigned = None
    runway_assigned = None
    stand_type = None
    
    if status in ["PARKED", "TAXI"]:
        gate_assigned = f"{random.choice(['A', 'B', 'C', 'D', 'E', 'F'])}{random.randint(1, 50):02d}"
        stand_type = random.choice(["TERMINAL", "REMOTE", "CARGO"])
    
    if status in ["TAKEOFF", "LANDING"]:
        runways = ["05L", "05R", "06L", "06R", "15L", "15R", "23L", "23R", "24L", "24R", "33L", "33R"]
        runway_assigned = random.choice(runways)
    
    # Generate turnaround time (for parked aircraft)
    turnaround_time_min = None
    if status == "PARKED":
        turnaround_time_min = random.randint(30, 120)
    
    # Generate assigned sector
    sectors = ["ACC", "APP", "TWR", "GND", "DEL"]
    assigned_sector = random.choice(sectors)
    
    # Generate emergency flag
    emergency_flags = ["NONE", "NONE", "NONE", "NONE", "NONE", "MINOR"]  # Mostly none, occasional minor
    emergency_flag = random.choice(emergency_flags)
    
    # Ensure wake category is available (derive if missing)
    wake = aircraft_type.wake
    if not wake:
        wake = derive_wake_from_mtow(aircraft_type.mtow_kg, aircraft_type.icao_type)
        if not wake:
            # Fallback to medium wake if cannot be determined
            wake = "M"
    
    # Derive climb rate if missing
    climb_rate = None
    if aircraft_type.engines and aircraft_type.mtow_kg:
        climb_rate = estimate_climb_rate_fpm(aircraft_type.engines.type, aircraft_type.mtow_kg)
    
    # Create the aircraft record
    record = AircraftRecord(
        icao24=icao24,
        registration=registration,
        callsign=callsign,
        airline=airline,
        flight_number=flight_number,
        icao_type=aircraft_type.icao_type,
        wake=wake,
        engines=aircraft_type.engines,
        dimensions=aircraft_type.dimensions,
        mtow_kg=aircraft_type.mtow_kg,
        climb_rate_fpm=climb_rate,
        op_category=op_category,
        # Enriched fields from API Ninjas
        max_speed_kts=aircraft_type.max_speed_kts,
        cruise_speed_kts=aircraft_type.cruise_speed_kts,
        ceiling_ft=aircraft_type.ceiling_ft,
        range_nm=aircraft_type.range_nm,
        takeoff_ground_run_ft=aircraft_type.takeoff_ground_run_ft,
        landing_ground_roll_ft=aircraft_type.landing_ground_roll_ft,
        engine_thrust_lbf=aircraft_type.engine_thrust_lbf,
        origin=origin_airport,
        destination=destination_airport,
        gate_assigned=gate_assigned,
        stand_type=stand_type,
        runway_assigned=runway_assigned,
        status=status,
        phase=phase,
        lat=lat,
        lon=lon,
        altitude_ft=altitude,
        heading_deg=heading,
        speed_kts=speed,
        squawk=squawk,
        assigned_sector=assigned_sector,
        emergency_flag=emergency_flag,
        created_at=datetime.now(timezone.utc),
        turnaround_time_min=turnaround_time_min,
        notes=""
    )
    
    return record


def generate_records(
    n: int,
    origin: str = "CYYZ",
    op_category: str = "PASSENGER",
    output_file: str = "dist/sample_records.jsonl",
    random_seed: Optional[int] = None
):
    """Generate N synthetic aircraft records."""
    
    # Set random seed for reproducibility
    if random_seed is not None:
        random.seed(random_seed)
    
    print(f"Generating {n} synthetic aircraft records...")
    print(f"Origin: {origin}, Operation category: {op_category}")
    
    # Load data
    print("Loading aircraft types and airlines...")
    aircraft_types = load_aircraft_types()
    airlines = load_airlines()
    
    print(f"Loaded {len(aircraft_types)} aircraft types and {len(airlines)} airlines")
    
    # Initialize utilities
    registry = UniquenessRegistry()
    randomizer = AircraftRandomizer(registry, random_seed)
    geo_utils = GeographicUtils(random_seed)
    
    # Generate records
    records = []
    for i in range(n):
        try:
            record = generate_aircraft_record(
                aircraft_types, airlines, randomizer, geo_utils, origin, op_category
            )
            records.append(record)
            
            if (i + 1) % 100 == 0:
                print(f"Generated {i + 1}/{n} records...")
                
        except Exception as e:
            print(f"Warning: Failed to generate record {i + 1}: {e}")
            continue
    
    # Write records to JSONL file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        for record in records:
            json.dump(record.model_dump(mode='json'), f)
            f.write('\n')
    
    print(f"Generated {len(records)} records successfully")
    print(f"Records written to {output_file}")
    
    # Print registry stats
    stats = registry.get_stats()
    print(f"Registry stats: {stats}")


def main(
    n: int = typer.Option(50, "--n", help="Number of records to generate"),
    origin: str = typer.Option("CYYZ", "--origin", help="Origin airport ICAO code"),
    op: str = typer.Option("PASSENGER", "--op", help="Operation category (PASSENGER/CARGO/GA)"),
    output: str = typer.Option("dist/sample_records.jsonl", "--output", help="Output file path"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducibility")
):
    """Generate synthetic aircraft records for ATC simulation."""
    
    # Validate operation category
    valid_ops = ["PASSENGER", "CARGO", "GA"]
    if op not in valid_ops:
        typer.echo(f"Error: Operation category must be one of {valid_ops}")
        raise typer.Exit(1)
    
    # Use environment variable for seed if not provided
    if seed is None:
        import os
        env_seed = os.getenv("RANDOM_SEED")
        if env_seed:
            try:
                seed = int(env_seed)
            except ValueError:
                typer.echo(f"Warning: Invalid RANDOM_SEED environment variable: {env_seed}")
    
    generate_records(n, origin, op, output, seed)


if __name__ == "__main__":
    typer.run(main)
