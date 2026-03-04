"""
LLM Prompt Templates: Build compact instruction prompts for Air and Ground LLMs.
"""

from typing import Dict, Any
import json


def build_air_prompt(context: Dict[str, Any]) -> str:
    """
    Build prompt for Air LLM (airborne aircraft controller).
    
    Args:
        context: Aircraft context including position, zone, nearby aircraft
        
    Returns:
        Compact instruction prompt requiring strict JSON output
    """
    aircraft = context.get("aircraft", {})
    callsign = aircraft.get("callsign", "UNKNOWN")
    zone = context.get("current_zone", "UNKNOWN")
    altitude_ft = aircraft.get("altitude_ft", 0)
    speed_kts = aircraft.get("speed_kts", 0)
    heading = aircraft.get("heading", 0)
    distance_nm = aircraft.get("distance_to_airport_nm", 0)
    
    # Nearby aircraft for separation awareness
    nearby_aircraft = context.get("current_zone_aircraft", [])
    nearby_summary = []
    for ac in nearby_aircraft[:5]:  # Limit to 5 for brevity
        nearby_summary.append(f"{ac.get('callsign', 'UNK')}: {ac.get('distance_nm', 0):.1f}NM")
    
    nearby_text = "; ".join(nearby_summary) if nearby_summary else "none"
    
    prompt = f"""You are an Air Traffic Controller managing airborne aircraft.

AIRCRAFT: {callsign}
CURRENT STATE:
- Zone: {zone}
- Position: {altitude_ft}ft, {speed_kts}kts, heading {heading}°
- Distance to airport: {distance_nm:.1f}NM
- Nearby aircraft in zone: {nearby_text}

HARD RULES (NEVER VIOLATE):
1. Maintain minimum 3NM lateral OR 1000ft vertical separation between ALL aircraft
2. Only ONE aircraft may occupy a runway at any time
3. Do NOT invent waypoints, gates, or runways - use only real identifiers or null
4. Output MUST be valid JSON only, matching the exact schema below

REQUIRED OUTPUT SCHEMA (JSON only, no explanation):
{{
  "action_type": "string (VECTORING|DESCENT_PROFILE|STAR_ASSIGNMENT|LANDING_CLEARANCE)",
  "target_altitude_ft": integer or null,
  "target_speed_kts": integer or null,
  "target_heading_deg": integer (0-359) or null,
  "waypoints": array of strings or null,
  "runway": "string (e.g. 05L)" or null
}}

Generate clearance JSON now:"""
    
    return prompt


def build_ground_prompt(context: Dict[str, Any]) -> str:
    """
    Build prompt for Ground LLM (surface operations controller).
    
    Args:
        context: Aircraft context including event type, position, gate status
        
    Returns:
        Compact instruction prompt requiring strict JSON output
    """
    aircraft = context.get("aircraft", {})
    callsign = aircraft.get("callsign", "UNKNOWN")
    event_type = context.get("event_type", "UNKNOWN")
    phase = aircraft.get("phase", "UNKNOWN")
    
    prompt = f"""You are a Ground Controller managing surface aircraft operations.

AIRCRAFT: {callsign}
EVENT: {event_type}
PHASE: {phase}

HARD RULES (NEVER VIOLATE):
1. Each gate can only be assigned to ONE aircraft at a time
2. Taxi routes must NOT conflict with active aircraft on the same taxiways
3. Do NOT invent gates, taxiways, or runways - use only real identifiers or null
4. Output MUST be valid JSON only, matching the exact schema below

REQUIRED OUTPUT SCHEMA (JSON only, no explanation):
{{
  "action_type": "string (GATE_ASSIGNMENT|TAXI_CLEARANCE|PUSHBACK)",
  "assigned_gate": "string (e.g. C32)" or null,
  "taxi_route": array of strings (e.g. ["A1", "A", "B"]) or null,
  "runway": "string (e.g. 05L)" or null
}}

Generate clearance JSON now:"""
    
    return prompt

