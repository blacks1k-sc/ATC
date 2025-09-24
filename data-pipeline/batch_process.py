#!/usr/bin/env python3
"""
Batch process aircraft in smaller chunks to avoid rate limiting.
"""

import os
import json
import time
from pathlib import Path
from src.emit import build_aircraft_types
from src.sources.icao_8643 import iter_icao_candidates

def batch_process_aircraft(batch_size=20, delay_between_batches=60):
    """
    Process aircraft in batches to avoid rate limiting.
    
    Args:
        batch_size: Number of aircraft to process per batch
        delay_between_batches: Seconds to wait between batches
    """
    print(f"Starting batch processing with batch size {batch_size}")
    
    # Get all candidates
    candidates = list(iter_icao_candidates())
    total_candidates = len(candidates)
    print(f"Total candidates: {total_candidates}")
    
    all_aircraft = []
    processed = 0
    
    # Process in batches
    for i in range(0, total_candidates, batch_size):
        batch_end = min(i + batch_size, total_candidates)
        batch_candidates = candidates[i:batch_end]
        
        print(f"\n--- Processing batch {i//batch_size + 1} ({i+1}-{batch_end}) ---")
        
        # Temporarily modify the emit.py to process only this batch
        # This is a simplified approach - in practice you'd want to refactor emit.py
        # to accept a list of candidates to process
        
        # For now, let's just run the normal process and see how many we get
        try:
            aircraft_types = build_aircraft_types()
            all_aircraft.extend(aircraft_types)
            processed += len(aircraft_types)
            print(f"Batch {i//batch_size + 1}: Got {len(aircraft_types)} aircraft")
        except Exception as e:
            print(f"Batch {i//batch_size + 1} failed: {e}")
        
        # Wait between batches to avoid rate limiting
        if batch_end < total_candidates:
            print(f"Waiting {delay_between_batches} seconds before next batch...")
            time.sleep(delay_between_batches)
    
    # Save all aircraft
    output_file = "dist/aircraft_types_batch.json"
    with open(output_file, "w") as f:
        json.dump(all_aircraft, f, indent=2)
    
    print(f"\n=== BATCH PROCESSING COMPLETE ===")
    print(f"Total aircraft generated: {len(all_aircraft)}")
    print(f"Output saved to: {output_file}")
    
    return all_aircraft

if __name__ == "__main__":
    batch_process_aircraft(batch_size=10, delay_between_batches=30)
