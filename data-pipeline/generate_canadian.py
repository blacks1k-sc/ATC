#!/usr/bin/env python3
"""
Generate synthetic aircraft records using only Canadian and international airlines
that operate to/from Canada.
"""

import typer
import json
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from rich.console import Console

app = typer.Typer(help="Generate synthetic aircraft records with Canadian airlines.")
console = Console()

# Load aircraft types and airlines data
AIRCRAFT_TYPES: List[Dict[str, Any]] = []
AIRLINES: List[Dict[str, Any]] = []

def load_data():
    global AIRCRAFT_TYPES, AIRLINES
    try:
        with open("dist/aircraft_types.json", "r") as f:
            AIRCRAFT_TYPES = json.load(f)
        with open("dist/airlines.json", "r") as f:
            all_airlines = json.load(f)
        
        # Filter for Canadian and international airlines that operate to Canada
        canadian_airlines = []
        for airline in all_airlines:
            name = airline.get("name", "").lower()
            icao = airline.get("icao", "").upper()
            
            # Canadian airlines
            if any(canadian in name for canadian in [
                "air canada", "westjet", "porter", "flair", "transat", "canadian",
                "sunwing", "rouge", "jazz", "north", "western"
            ]):
                canadian_airlines.append(airline)
            # Major international airlines that operate to Canada
            elif any(international in name for international in [
                "american", "united", "delta", "british airways", "lufthansa",
                "air france", "klm", "swiss", "austrian", "sas", "iberia",
                "alitalia", "turkish", "emirates", "qatar", "cathay", "ana",
                "japan", "korean", "singapore", "thai", "malaysia", "garuda",
                "virgin", "jetblue", "southwest", "alaska", "hawaiian"
            ]):
                canadian_airlines.append(airline)
            # Airlines with Canadian ICAO codes (some patterns)
            elif icao in ["ACA", "JZA", "TSC", "CDN", "WJA", "POE", "FLE", "WEN"]:
                canadian_airlines.append(airline)
        
        AIRLINES = canadian_airlines
        console.print(f"Loaded {len(AIRCRAFT_TYPES)} aircraft types and {len(AIRLINES)} Canadian/international airlines")
        
    except FileNotFoundError:
        console.log("[bold red]Error: aircraft_types.json or airlines.json not found in dist/.[/bold red]")
        console.log("Please run 'make build' first to generate the data.")
        typer.Exit(code=1)

@app.callback()
def main_callback():
    """
    Synthetic aircraft record generator with Canadian airlines.
    """
    load_data()

def generate_record(record_id: int, origin: str) -> Dict[str, Any]:
    """
    Generates a single synthetic aircraft record.
    """
    if not AIRCRAFT_TYPES or not AIRLINES:
        raise ValueError("Aircraft types or airlines data not loaded.")

    aircraft_type = random.choice(AIRCRAFT_TYPES)
    airline = random.choice(AIRLINES)

    # Generate a plausible destination (simplified)
    # In a real system, this would be based on actual routes
    destinations = ["LFPG", "KJFK", "EGLL", "OMDB", "ZBAA", "RJTT", "CYYZ", "KLAX", "EDDF", "EHAM"]
    destination = random.choice([d for d in destinations if d != origin])

    # Generate a random callsign
    callsign = f"{airline['icao']} {random.randint(100, 9999)}"

    # Generate random altitude and speed based on aircraft type (simplified)
    # In a real system, this would be more dynamic based on flight phase
    altitude = random.randint(1000, 40000)
    speed = random.randint(150, 550)

    # Generate position (simplified - just use origin coordinates with some offset)
    # In a real system, this would be based on actual flight paths
    lat = 43.6777 + random.uniform(-0.1, 0.1)  # Toronto area
    lon = -79.6248 + random.uniform(-0.1, 0.1)

    return {
        "id": f"aircraft_{record_id:06d}",
        "callsign": callsign,
        "aircraft_type": aircraft_type["icao_type"],
        "airline": f"{airline['icao']}-{airline['name']}",
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
    output: str = typer.Option("dist/sample_records_canadian.jsonl", "--output", "-o", help="Output file path")
):
    """
    Generates N synthetic aircraft records using Canadian and international airlines.
    """
    console.print(f"[bold blue]Generating {n} aircraft records with Canadian/international airlines...[/bold blue]")

    records: List[Dict[str, Any]] = []
    with console.status("  Generating records...") as status:
        for i in range(n):
            try:
                record = generate_record(i + 1, origin)
                records.append(record)
            except ValueError as e:
                console.log(f"[bold red]Error generating record: {e}[/bold red]")
                typer.Exit(code=1)
            status.update(f"  Generating records... {i+1}/{n}")

    with open(output, "w") as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    console.print(f"[green]✓ Generated {len(records)} aircraft records[/green]")
    console.print(f"[green]✓ Output written to {output}[/green]")

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
    
    # Show some airline examples
    console.print("\n[bold]Sample Airlines Used:[/bold]")
    for airline_code in list(airline_counts.keys())[:10]:
        # Find airline name
        airline_name = "Unknown"
        for airline in AIRLINES:
            if airline.get("icao") == airline_code:
                airline_name = airline.get("name", "Unknown")
                break
        console.print(f"  {airline_code}: {airline_name}")

if __name__ == "__main__":
    app()
