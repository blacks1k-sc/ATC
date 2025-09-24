#!/usr/bin/env python3
"""
Build aircraft_types.json, airlines.json, and meta.json from various sources.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .models import TypeSpec, EngineSpec, Dimensions
from .sources.api_ninjas import fetch_by_model as ninjas_fetch
from .sources.aerodatabox import fetch_by_model as adb_fetch
from .sources.icao_8643 import iter_icao_candidates, lookup_8643_row, ensure_fallbacks
from .sources.airlines import load_airlines, download_airlines_data
from .utils.merge import merge_typespec, finalize_typespec
from .utils.derive import normalize_engine_type
from .utils.estimators import AircraftParameterEstimator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

# Global estimator instance
_estimator = AircraftParameterEstimator()

def _fill_derived_fields(ts: TypeSpec) -> TypeSpec:
    """Fill missing aircraft parameters using derived estimates."""
    # Build a plain dict for the estimator
    dims = None
    if ts.dimensions:
        # Convert from meters to feet for the estimator
        dims = {
            "length_ft": ts.dimensions.length_m * 3.28084 if ts.dimensions.length_m else 0,
            "wingspan_ft": ts.dimensions.wingspan_m * 3.28084 if ts.dimensions.wingspan_m else 0,
            "height_ft": ts.dimensions.height_m * 3.28084 if ts.dimensions.height_m else 0,
        }

    derived = _estimator.estimate_all_parameters(
        icao_type=ts.icao_type,
        wake_category=ts.wake or "M",  # Default to Medium if not set
        engine_type=ts.engines.type if ts.engines and ts.engines.type else "JET",
        dimensions=dims,
        mtow_kg=ts.mtow_kg or 0,
        max_speed_kts=ts.max_speed_kts or 0,
        range_nm=ts.range_nm or 0,
        ceiling_ft=ts.ceiling_ft or 0,
        climb_rate_fpm=ts.climb_rate_fpm or 0,
    )

    # Engine count
    if (ts.engines is None) or (getattr(ts.engines, "count", None) in (None, 0)):
        ts.engines = ts.engines or EngineSpec(count=None, type=ts.engines.type if ts.engines else "JET")
        ts.engines.count = derived.get("engines_count") or ts.engines.count

    # Cruise speed
    if getattr(ts, "cruise_speed_kts", None) in (None, 0):
        ts.cruise_speed_kts = derived.get("cruise_speed_kts") or ts.cruise_speed_kts

    # Thrust (per engine)
    if getattr(ts, "engine_thrust_lbf", None) in (None, 0):
        ts.engine_thrust_lbf = derived.get("engine_thrust_lbf") or ts.engine_thrust_lbf

    # Ground distances
    if getattr(ts, "takeoff_ground_run_ft", None) in (None, 0):
        ts.takeoff_ground_run_ft = derived.get("takeoff_ground_run_ft") or ts.takeoff_ground_run_ft
    if getattr(ts, "landing_ground_roll_ft", None) in (None, 0):
        ts.landing_ground_roll_ft = derived.get("landing_ground_roll_ft") or ts.landing_ground_roll_ft

    # Provenance
    try:
        if ts.notes is None:
            ts.notes = {"source": ["derived"]}
        else:
            if isinstance(ts.notes, str):
                # Convert string notes to dict format
                ts.notes = {"source": [ts.notes, "derived"]}
            elif isinstance(ts.notes, dict):
                sources = ts.notes.get("source", [])
                if "derived" not in sources:
                    sources.append("derived")
                ts.notes["source"] = sources
    except Exception:
        pass

    return ts

def _summary(types):
    """Print missingness summary for derived fields."""
    fields = ["engines.count", "cruise_speed_kts", "engine_thrust_lbf", "takeoff_ground_run_ft", "landing_ground_roll_ft"]
    missing = {f: 0 for f in fields}
    
    for t in types:
        # Check engines.count
        if not t.get("engines") or not t["engines"].get("count"):
            missing["engines.count"] += 1
        # Check other fields
        for f in fields[1:]:
            if not t.get(f):
                missing[f] += 1
    
    console.print("\n[bold]Derived-field missingness:[/bold]")
    for field, count in missing.items():
        percentage = (count / len(types)) * 100 if types else 0
        console.print(f"  {field:25s}: {count:2d}/{len(types):2d} ({percentage:5.1f}% missing)")

def build_aircraft_types() -> List[Dict[str, Any]]:
    """
    Build aircraft types from various sources.
    
    Returns:
        List of aircraft type dictionaries
    """
    console.print("[bold blue]Building aircraft types...[/bold blue]")
    
    # Ensure fallback data is available
    ensure_fallbacks()
    
    aircraft_types = []
    processed_count = 0
    success_count = 0
    
    # Get candidates from planes.dat
    candidates = list(iter_icao_candidates())
    console.print(f"Found {len(candidates)} ICAO type candidates")
    
    # Process aircraft from planes.dat candidates
    console.print("Processing aircraft from planes.dat...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        # Process aircraft in smaller batches to avoid rate limiting
        max_candidates = min(50, len(candidates))  # Process 50 at a time
        task = progress.add_task("Processing aircraft from planes.dat...", total=max_candidates)

        for i, (icao_type, manufacturer_guess, model_guess) in enumerate(candidates[:max_candidates]):
            progress.update(task, description=f"Processing {icao_type} ({manufacturer_guess} {model_guess})")

            # Skip aircraft that are likely to fail
            if manufacturer_guess == "Unknown" or not model_guess:
                logger.debug(f"Skipping {icao_type} - no valid manufacturer/model")
                continue
                
            # Skip very old or obscure aircraft
            if any(skip in model_guess.lower() for skip in ["an-", "il-", "tu-", "yak-", "su-"]):
                logger.debug(f"Skipping {icao_type} - likely obscure aircraft")
                continue

            processed_count += 1

            # Skip API calls for now - use only cached data
            primary_spec = None
            secondary_spec = None
            
            # Try to get from cache first
            try:
                from .sources.api_ninjas import get_cached_json
                cache_key = f"ninjas_{manufacturer_guess.lower().replace(' ', '_')}_{model_guess.lower().replace(' ', '_')}"
                cached_data = get_cached_json(cache_key)
                if cached_data:
                    from .sources.api_ninjas import _parse_response
                    primary_spec = _parse_response(cached_data, manufacturer_guess, model_guess)
            except Exception as e:
                logger.debug(f"Cache lookup failed for {icao_type}: {e}")

            # Merge specifications
            merged_spec = None
            if primary_spec and secondary_spec:
                merged_spec = merge_typespec(primary_spec, secondary_spec)
            elif primary_spec:
                merged_spec = primary_spec
            elif secondary_spec:
                merged_spec = secondary_spec

            # Set ICAO type
            if merged_spec:
                merged_spec.icao_type = icao_type

                # Try to patch from 8643 data if still missing critical fields
                if not merged_spec.wake or merged_spec.engines.type == "OTHER":
                    icao_8643_data = lookup_8643_row(icao_type)
                    if icao_8643_data:
                        if not merged_spec.wake and icao_8643_data.get("wake"):
                            merged_spec.wake = icao_8643_data["wake"]

                        if merged_spec.engines.type == "OTHER" and icao_8643_data.get("engine_type"):
                            merged_spec.engines.type = normalize_engine_type(icao_8643_data["engine_type"])

                        if not merged_spec.engines.count and icao_8643_data.get("engines"):
                            try:
                                merged_spec.engines.count = int(icao_8643_data["engines"])
                            except (ValueError, TypeError):
                                pass
                
                # Finalize the specification
                merged_spec = finalize_typespec(merged_spec)
                
                # Apply derivation if enabled
                if os.getenv("DERIVE_MISSING", "1") != "0":
                    merged_spec = _fill_derived_fields(merged_spec)
                
                # Validate quality bar
                if _has_required_fields(merged_spec):
                    aircraft_types.append(merged_spec.model_dump())
                    success_count += 1
                    logger.debug(f"Successfully processed {icao_type}")
                else:
                    logger.debug(f"Failed quality bar for {icao_type}")
            else:
                logger.debug(f"No data found for {icao_type}")
            
            progress.advance(task)
    
    console.print(f"[green]Processed {processed_count} candidates, {success_count} successful[/green]")
    return aircraft_types

def _has_required_fields(spec: TypeSpec) -> bool:
    """
    Check if TypeSpec meets quality bar.
    
    Args:
        spec: TypeSpec to validate
        
    Returns:
        True if has required fields
    """
    return (
        spec.wake is not None and
        spec.engines.type is not None and
        spec.mtow_kg is not None
    )

def build_airlines() -> List[Dict[str, Any]]:
    """
    Build airlines data.
    
    Returns:
        List of airline dictionaries
    """
    console.print("[bold blue]Building airlines data...[/bold blue]")
    
    # Download airlines data if needed
    download_airlines_data()
    
    # Load airlines
    airlines = load_airlines()
    console.print(f"[green]Loaded {len(airlines)} airlines[/green]")
    
    return airlines

def build_meta(aircraft_types: List[Dict[str, Any]], airlines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build metadata about the build process.
    
    Args:
        aircraft_types: List of aircraft types
        airlines: List of airlines
        
    Returns:
        Metadata dictionary
    """
    return {
        "build_timestamp": str(Path().cwd()),
        "aircraft_types_count": len(aircraft_types),
        "airlines_count": len(airlines),
        "sources": {
            "api_ninjas": "Primary source for aircraft specifications",
            "aerodatabox": "Secondary source for aircraft specifications", 
            "icao_8643": "Fallback source for wake categories and engine info",
            "planes_dat": "Source for ICAO type candidates",
            "airlines_dat": "Source for airline information"
        },
        "quality_criteria": {
            "required_fields": ["wake", "engines.type", "mtow_kg"],
            "derived_fields": ["climb_rate_fpm", "wake (from mtow_kg)"]
        }
    }

def main():
    """Main entry point."""
    console.print("[bold green]Starting aircraft data pipeline...[/bold green]")
    
    # Create output directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    try:
        # Build aircraft types
        aircraft_types = build_aircraft_types()
        
        # Show missingness summary
        _summary(aircraft_types)
        
        # Build airlines
        airlines = build_airlines()
        
        # Build metadata
        meta = build_meta(aircraft_types, airlines)
        
        # Write outputs
        console.print("[bold blue]Writing output files...[/bold blue]")
        
        with open(dist_dir / "aircraft_types.json", 'w') as f:
            json.dump(aircraft_types, f, indent=2)
        
        with open(dist_dir / "airlines.json", 'w') as f:
            json.dump(airlines, f, indent=2)
        
        with open(dist_dir / "meta.json", 'w') as f:
            json.dump(meta, f, indent=2)
        
        console.print(f"[green]✓ Successfully built {len(aircraft_types)} aircraft types and {len(airlines)} airlines[/green]")
        console.print(f"[green]✓ Output files written to dist/[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Pipeline failed: {e}[/red]")
        logger.exception("Pipeline failed")
        raise

if __name__ == "__main__":
    main()
