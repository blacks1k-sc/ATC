from typing import Optional
from ..models import TypeSpec, EngineSpec, Dimensions, EngineType
from .derive import wake_from_mtow, estimate_climb_rate

def merge_typespec(primary: TypeSpec, secondary: TypeSpec) -> TypeSpec:
    """
    Merge two TypeSpec objects, filling None fields from secondary.
    
    Args:
        primary: Primary TypeSpec (takes precedence)
        secondary: Secondary TypeSpec (fills gaps)
        
    Returns:
        Merged TypeSpec
    """
    # Merge dimensions
    merged_dimensions = None
    if primary.dimensions or secondary.dimensions:
        merged_dimensions = Dimensions(
            length_m=primary.dimensions.length_m if primary.dimensions and primary.dimensions.length_m is not None 
                    else (secondary.dimensions.length_m if secondary.dimensions else None),
            wingspan_m=primary.dimensions.wingspan_m if primary.dimensions and primary.dimensions.wingspan_m is not None 
                     else (secondary.dimensions.wingspan_m if secondary.dimensions else None),
            height_m=primary.dimensions.height_m if primary.dimensions and primary.dimensions.height_m is not None 
                    else (secondary.dimensions.height_m if secondary.dimensions else None)
        )
    
    # Merge engine spec
    merged_engines = EngineSpec(
        count=primary.engines.count if primary.engines.count is not None else secondary.engines.count,
        type=primary.engines.type if primary.engines.type != "OTHER" else secondary.engines.type
    )
    
    return TypeSpec(
        icao_type=primary.icao_type,
        wake=primary.wake,
        engines=merged_engines,
        dimensions=merged_dimensions,
        mtow_kg=primary.mtow_kg if primary.mtow_kg is not None else secondary.mtow_kg,
        cruise_speed_kts=primary.cruise_speed_kts if primary.cruise_speed_kts is not None else secondary.cruise_speed_kts,
        max_speed_kts=primary.max_speed_kts if primary.max_speed_kts is not None else secondary.max_speed_kts,
        range_nm=primary.range_nm if primary.range_nm is not None else secondary.range_nm,
        ceiling_ft=primary.ceiling_ft if primary.ceiling_ft is not None else secondary.ceiling_ft,
        climb_rate_fpm=primary.climb_rate_fpm if primary.climb_rate_fpm is not None else secondary.climb_rate_fpm,
        takeoff_ground_run_ft=primary.takeoff_ground_run_ft if primary.takeoff_ground_run_ft is not None else secondary.takeoff_ground_run_ft,
        landing_ground_roll_ft=primary.landing_ground_roll_ft if primary.landing_ground_roll_ft is not None else secondary.landing_ground_roll_ft,
        engine_thrust_lbf=primary.engine_thrust_lbf if primary.engine_thrust_lbf is not None else secondary.engine_thrust_lbf,
        notes=primary.notes if primary.notes else secondary.notes
    )

def finalize_typespec(ts: TypeSpec) -> TypeSpec:
    """
    Finalize TypeSpec by deriving missing fields.
    
    Args:
        ts: TypeSpec to finalize
        
    Returns:
        Finalized TypeSpec
    """
    # Derive wake category if missing
    if ts.wake is None and ts.mtow_kg is not None:
        ts.wake = wake_from_mtow(ts.mtow_kg, ts.icao_type)
    
    # Derive climb rate if missing
    if ts.climb_rate_fpm is None and ts.engines.type and ts.mtow_kg is not None:
        ts.climb_rate_fpm = estimate_climb_rate(ts.engines.type, ts.mtow_kg)
    
    # Ensure engine type has a default
    if ts.engines.type is None:
        ts.engines.type = "OTHER"
    
    return ts
