#!/usr/bin/env python3
"""
Generate synthetic aircraft records for testing.
"""

import json
import random
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

app = typer.Typer()

def load_aircraft_types() -> List[Dict[str, Any]]:
    """Load aircraft types from dist/aircraft_types.json."""
    types_file = Path("dist") / "aircraft_types.json"
    if not types_file.exists():
        console.print("[red]Error: dist/aircraft_types.json not found. Run 'make build' first.[/red]")
        raise typer.Exit(1)
    
    with open(types_file, 'r') as f:
        return json.load(f)

def load_airlines() -> List[Dict[str, Any]]:
    """Load airlines from dist/airlines.json."""
    airlines_file = Path("dist") / "airlines.json"
    if not airlines_file.exists():
        console.print("[red]Error: dist/airlines.json not found. Run 'make build' first.[/red]")
        raise typer.Exit(1)
    
    with open(airlines_file, 'r') as f:
        return json.load(f)

def generate_callsign(airline: Dict[str, Any]) -> str:
    """Generate a realistic callsign for an airline."""
    icao = airline.get("icao", "")
    callsign = airline.get("callsign", "")
    
    if callsign:
        # Use existing callsign with flight number
        flight_num = random.randint(100, 9999)
        return f"{callsign} {flight_num}"
    elif icao:
        # Generate from ICAO code
        flight_num = random.randint(100, 9999)
        return f"{icao} {flight_num}"
    else:
        # Fallback
        return f"FLT {random.randint(1000, 9999)}"

def generate_route(origin: str) -> str:
    """Generate a realistic destination for a route from origin."""
    # Common destinations from major airports
    destinations = {
        "CYYZ": ["KJFK", "KLAX", "KORD", "KDFW", "EGLL", "LFPG", "EDDF", "EHAM", "CYVR", "CYYC"],
        "KJFK": ["EGLL", "LFPG", "EDDF", "EHAM", "CYYZ", "KLAX", "KORD", "KDFW", "RJTT", "VHHH"],
        "KLAX": ["KJFK", "KORD", "KDFW", "CYYZ", "RJTT", "VHHH", "YSSY", "EGLL", "LFPG"],
        "EGLL": ["KJFK", "LFPG", "EDDF", "EHAM", "CYYZ", "RJTT", "VHHH", "YSSY", "OMDB"],
        "LFPG": ["KJFK", "EGLL", "EDDF", "EHAM", "CYYZ", "RJTT", "VHHH", "OMDB", "LTBA"],
        "EDDF": ["KJFK", "EGLL", "LFPG", "EHAM", "CYYZ", "RJTT", "VHHH", "OMDB", "LTBA"],
        "EHAM": ["KJFK", "EGLL", "LFPG", "EDDF", "CYYZ", "RJTT", "VHHH", "OMDB", "LTBA"]
    }
    
    if origin in destinations:
        return random.choice(destinations[origin])
    else:
        # Generic fallback
        return random.choice(["KJFK", "EGLL", "LFPG", "EDDF", "EHAM", "RJTT", "VHHH"])

def generate_altitude(aircraft_type: Dict[str, Any]) -> int:
    """Generate a realistic altitude based on aircraft type."""
    wake = aircraft_type.get("wake", "M")
    ceiling_ft = aircraft_type.get("ceiling_ft")
    
    # Base altitude by wake category
    base_altitudes = {
        "L": (3000, 12000),   # Light aircraft
        "M": (8000, 25000),   # Medium aircraft  
        "H": (15000, 35000),  # Heavy aircraft
        "J": (20000, 40000)   # Super aircraft (A380)
    }
    
    min_alt, max_alt = base_altitudes.get(wake, (8000, 25000))
    
    # Respect aircraft ceiling if available
    if ceiling_ft:
        max_alt = min(max_alt, ceiling_ft - 2000)  # Leave some margin
    
    return random.randint(min_alt, max_alt)

def generate_speed(aircraft_type: Dict[str, Any]) -> int:
    """Generate a realistic speed based on aircraft type."""
    cruise_speed = aircraft_type.get("cruise_speed_kts")
    max_speed = aircraft_type.get("max_speed_kts")
    
    if cruise_speed:
        # Use cruise speed with some variation
        return random.randint(int(cruise_speed * 0.9), int(cruise_speed * 1.1))
    elif max_speed:
        # Use max speed with more variation
        return random.randint(int(max_speed * 0.7), int(max_speed * 0.9))
    else:
        # Fallback based on wake category
        wake = aircraft_type.get("wake", "M")
        base_speeds = {"L": (120, 200), "M": (200, 400), "H": (300, 500), "J": (400, 600)}
        min_speed, max_speed = base_speeds.get(wake, (200, 400))
        return random.randint(min_speed, max_speed)

def generate_aircraft_record(
    aircraft_type: Dict[str, Any], 
    airline: Dict[str, Any], 
    origin: str,
    record_id: int
) -> Dict[str, Any]:
    """Generate a single aircraft record."""
    
    destination = generate_route(origin)
    callsign = generate_callsign(airline)
    altitude = generate_altitude(aircraft_type)
    speed = generate_speed(aircraft_type)
    
    # Generate position (simplified - just use origin coordinates with some offset)
    # In a real system, this would be based on actual flight paths
    lat = 43.6777 + random.uniform(-0.1, 0.1)  # Toronto area
    lon = -79.6248 + random.uniform(-0.1, 0.1)
    
    return {
        "id": f"aircraft_{record_id:06d}",
        "callsign": callsign,
        "aircraft_type": aircraft_type["icao_type"],
        "airline": airline["icao"],
        "origin": origin,
        "destination": destination,
        "position": {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "altitude_ft": altitude,
            "heading": random.randint(0, 359),
            "speed_kts": speed
        },
        "status": None,  # Keep status as null for now
        "timestamp": "2024-01-01T12:00:00Z"  # Placeholder timestamp
    }

@app.command()
def generate(
    n: int = typer.Option(50, "--n", help="Number of aircraft records to generate"),
    origin: str = typer.Option("CYYZ", "--origin", help="Origin airport ICAO code"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducible output"),
    output: str = typer.Option("dist/sample_records.jsonl", "--output", help="Output file path")
):
    """Generate synthetic aircraft records."""
    
    if seed is not None:
        random.seed(seed)
        console.print(f"[blue]Using random seed: {seed}[/blue]")
    
    console.print(f"[bold blue]Generating {n} aircraft records...[/bold blue]")
    
    # Load data
    aircraft_types = load_aircraft_types()
    airlines = load_airlines()
    
    if not aircraft_types:
        console.print("[red]Error: No aircraft types available[/red]")
        raise typer.Exit(1)
    
    if not airlines:
        console.print("[red]Error: No airlines available[/red]")
        raise typer.Exit(1)
    
    console.print(f"Loaded {len(aircraft_types)} aircraft types and {len(airlines)} airlines")
    
    # Create output directory
    output_path = Path(output)
    output_path.parent.mkdir(exist_ok=True)
    
    # Generate records
    records = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Generating records...", total=n)
        
        for i in range(n):
            aircraft_type = random.choice(aircraft_types)
            airline = random.choice(airlines)
            
            record = generate_aircraft_record(aircraft_type, airline, origin, i + 1)
            records.append(record)
            
            progress.advance(task)
    
    # Write output
    with open(output_path, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    
    console.print(f"[green]✓ Generated {len(records)} aircraft records[/green]")
    console.print(f"[green]✓ Output written to {output_path}[/green]")
    
    # Show summary
    aircraft_type_counts = {}
    airline_counts = {}
    
    for record in records:
        aircraft_type_counts[record["aircraft_type"]] = aircraft_type_counts.get(record["aircraft_type"], 0) + 1
        airline_counts[record["airline"]] = airline_counts.get(record["airline"], 0) + 1
    
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Aircraft types: {len(aircraft_type_counts)}")
    console.print(f"  Airlines: {len(airline_counts)}")
    console.print(f"  Status: All set to null (no flight phases assigned)")

if __name__ == "__main__":
    app()
