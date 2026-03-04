"""
LLM Response Schemas: Minimal dataclass definitions for Air and Ground clearances.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class AirClearance:
    """
    Schema for Air controller clearance output.
    
    All LLM responses for airborne aircraft must match this structure exactly.
    """
    action_type: str  # e.g. "VECTORING", "DESCENT_PROFILE", "STAR_ASSIGNMENT", "LANDING_CLEARANCE"
    target_altitude_ft: Optional[int] = None
    target_speed_kts: Optional[int] = None
    target_heading_deg: Optional[int] = None
    waypoints: Optional[List[str]] = None  # List of waypoint names
    runway: Optional[str] = None  # e.g. "05L"
    
    def to_dict(self):
        """Convert to dictionary, filtering out None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class GroundClearance:
    """
    Schema for Ground controller clearance output.
    
    All LLM responses for ground/surface aircraft must match this structure exactly.
    """
    action_type: str  # e.g. "GATE_ASSIGNMENT", "TAXI_CLEARANCE", "PUSHBACK"
    assigned_gate: Optional[str] = None  # e.g. "C32"
    taxi_route: Optional[List[str]] = None  # List of taxiway segments e.g. ["A1", "A", "B", "C"]
    runway: Optional[str] = None  # e.g. "05L" for departure taxi
    
    def to_dict(self):
        """Convert to dictionary, filtering out None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}

