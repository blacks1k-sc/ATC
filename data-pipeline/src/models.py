"""
Pydantic models for ATC data pipeline.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, validator


class EngineSpec(BaseModel):
    """Engine specification for aircraft types."""
    count: int = Field(..., ge=1, le=8, description="Number of engines")
    type: Literal["JET", "TURBOPROP", "PISTON", "ELECTRIC", "OTHER"] = Field(..., description="Engine type")


class Dimensions(BaseModel):
    """Aircraft dimensions in meters."""
    wingspan_m: float = Field(..., gt=0, description="Wingspan in meters")
    length_m: float = Field(..., gt=0, description="Length in meters")
    height_m: float = Field(..., gt=0, description="Height in meters")


class TypeSpec(BaseModel):
    """Aircraft type specification."""
    icao_type: str = Field(..., min_length=3, max_length=4, description="ICAO aircraft type code")
    wake: Optional[Literal["L", "M", "H", "J"]] = Field(None, description="Wake turbulence category")
    engines: Optional[EngineSpec] = Field(None, description="Engine specification")
    dimensions: Optional[Dimensions] = Field(None, description="Aircraft dimensions")
    mtow_kg: Optional[float] = Field(None, gt=0, description="Maximum takeoff weight in kg")
    climb_rate_fpm: Optional[int] = Field(None, ge=0, le=5000, description="Climb rate in feet per minute")
    notes: Optional[str] = Field(None, description="Additional notes or metadata")
    
    # NEW enriched fields from API Ninjas (all Optional)
    max_speed_kts: Optional[float] = Field(None, gt=0, description="Maximum speed in knots")
    cruise_speed_kts: Optional[float] = Field(None, gt=0, description="Cruise speed in knots")
    ceiling_ft: Optional[float] = Field(None, gt=0, description="Service ceiling in feet")
    range_nm: Optional[float] = Field(None, gt=0, description="Range in nautical miles")
    takeoff_ground_run_ft: Optional[float] = Field(None, gt=0, description="Takeoff ground run in feet")
    landing_ground_roll_ft: Optional[float] = Field(None, gt=0, description="Landing ground roll in feet")
    engine_thrust_lbf: Optional[float] = Field(None, gt=0, description="Engine thrust in pounds-force")


class Airline(BaseModel):
    """Airline information."""
    name: str = Field(..., min_length=1, description="Airline name")
    icao: str = Field(..., min_length=3, max_length=3, description="ICAO airline code")
    iata: Optional[str] = Field(None, min_length=2, max_length=2, description="IATA airline code")
    country: Optional[str] = Field(None, description="Country of origin")


class AircraftRecord(BaseModel):
    """Complete aircraft record for ATC simulation."""
    icao24: str = Field(..., min_length=6, max_length=6, description="24-bit ICAO address (hex)")
    registration: str = Field(..., min_length=3, description="Aircraft registration")
    callsign: str = Field(..., min_length=3, description="Flight callsign")
    airline: Airline = Field(..., description="Operating airline")
    flight_number: str = Field(..., min_length=1, description="Flight number")
    icao_type: str = Field(..., min_length=3, max_length=4, description="ICAO aircraft type")
    wake: Literal["L", "M", "H", "J"] = Field(..., description="Wake turbulence category")
    engines: EngineSpec = Field(..., description="Engine specification")
    dimensions: Optional[Dimensions] = Field(None, description="Aircraft dimensions")
    mtow_kg: Optional[float] = Field(None, gt=0, description="Maximum takeoff weight in kg")
    climb_rate_fpm: Optional[int] = Field(None, ge=0, le=5000, description="Climb rate in feet per minute")
    op_category: Literal["PASSENGER", "CARGO", "GA"] = Field(..., description="Operation category")
    
    # Enriched fields from API Ninjas
    max_speed_kts: Optional[float] = Field(None, gt=0, description="Maximum speed in knots")
    cruise_speed_kts: Optional[float] = Field(None, gt=0, description="Cruise speed in knots")
    ceiling_ft: Optional[float] = Field(None, gt=0, description="Service ceiling in feet")
    range_nm: Optional[float] = Field(None, gt=0, description="Range in nautical miles")
    takeoff_ground_run_ft: Optional[float] = Field(None, gt=0, description="Takeoff ground run in feet")
    landing_ground_roll_ft: Optional[float] = Field(None, gt=0, description="Landing ground roll in feet")
    engine_thrust_lbf: Optional[float] = Field(None, gt=0, description="Engine thrust in pounds-force")
    origin: str = Field(..., min_length=4, max_length=4, description="Origin airport ICAO code")
    destination: str = Field(..., min_length=4, max_length=4, description="Destination airport ICAO code")
    gate_assigned: Optional[str] = Field(None, description="Assigned gate")
    stand_type: Optional[Literal["TERMINAL", "REMOTE", "CARGO"]] = Field(None, description="Stand type")
    runway_assigned: Optional[str] = Field(None, description="Assigned runway")
    status: Literal["PARKED", "TAXI", "TAKEOFF", "ENROUTE", "APPROACH", "LANDING"] = Field(..., description="Flight status")
    phase: Literal["PARKED", "TAXI_OUT", "TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "APPROACH", "LANDING", "TAXI_IN"] = Field(..., description="Flight phase")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    altitude_ft: int = Field(..., ge=0, le=60000, description="Altitude in feet")
    heading_deg: int = Field(..., ge=0, le=359, description="Heading in degrees")
    speed_kts: int = Field(..., ge=0, le=1000, description="Speed in knots")
    squawk: str = Field(..., min_length=4, max_length=4, description="Transponder squawk code")
    assigned_sector: Optional[str] = Field(None, description="Assigned ATC sector")
    emergency_flag: Literal["NONE", "MINOR", "MAJOR", "EMERGENCY"] = Field(..., description="Emergency status")
    created_at: datetime = Field(..., description="Record creation timestamp")
    turnaround_time_min: Optional[int] = Field(None, ge=0, le=1440, description="Turnaround time in minutes")
    notes: str = Field("", description="Additional notes")

    @validator('icao24')
    def validate_icao24(cls, v):
        """Validate ICAO24 is valid hex."""
        try:
            int(v, 16)
            return v.upper()
        except ValueError:
            raise ValueError('ICAO24 must be valid hexadecimal')

    @validator('squawk')
    def validate_squawk(cls, v):
        """Validate squawk code is numeric."""
        if not v.isdigit():
            raise ValueError('Squawk code must be numeric')
        return v

    @validator('registration')
    def validate_registration(cls, v):
        """Validate registration format."""
        return v.upper()

    @validator('callsign')
    def validate_callsign(cls, v):
        """Validate callsign format."""
        return v.upper()

    @validator('origin', 'destination')
    def validate_airport_codes(cls, v):
        """Validate airport ICAO codes."""
        return v.upper()

    @validator('icao_type')
    def validate_icao_type(cls, v):
        """Validate ICAO aircraft type code."""
        return v.upper()
