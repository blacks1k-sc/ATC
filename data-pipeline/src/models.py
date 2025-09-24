from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any

Wake = Literal["L", "M", "H", "J"]
EngineType = Literal["JET", "TURBOPROP", "PISTON", "ELECTRIC", "OTHER"]

class Dimensions(BaseModel):
    length_m: Optional[float] = None
    wingspan_m: Optional[float] = None
    height_m: Optional[float] = None

class EngineSpec(BaseModel):
    count: Optional[int] = None
    type: Optional[EngineType] = None

class TypeSpec(BaseModel):
    icao_type: str
    wake: Optional[Wake] = None
    engines: EngineSpec
    dimensions: Optional[Dimensions] = None
    mtow_kg: Optional[float] = None
    cruise_speed_kts: Optional[float] = None
    max_speed_kts: Optional[float] = None
    range_nm: Optional[float] = None
    ceiling_ft: Optional[float] = None
    climb_rate_fpm: Optional[float] = None
    takeoff_ground_run_ft: Optional[float] = None
    landing_ground_roll_ft: Optional[float] = None
    engine_thrust_lbf: Optional[float] = None
    notes: Optional[Dict[str, Any]] = None
