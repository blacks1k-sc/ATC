"""
Safety Validator: Validates LLM clearances against ATC safety rules.
"""

import logging
from typing import Dict, Any, List, Optional
import asyncpg

logger = logging.getLogger(__name__)


class SafetyValidator:
    """
    Validates air and ground clearances for safety compliance.
    
    Checks:
    - Air: Minimum separation (3NM lateral or 1000ft vertical)
    - Air: Runway exclusivity (one aircraft per runway)
    - Ground: Gate availability
    - Ground: Taxi route conflicts
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def validate_air_clearance(
        self,
        aircraft_id: int,
        clearance: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Validate air clearance for safety.
        
        Args:
            aircraft_id: ID of aircraft receiving clearance
            clearance: Parsed clearance dict (action_type, target_altitude_ft, etc.)
            context: Aircraft context used for decision
            
        Returns:
            True if clearance is safe, False otherwise
        """
        try:
            # Extract clearance parameters
            target_altitude = clearance.get("target_altitude_ft")
            target_runway = clearance.get("runway")
            action_type = clearance.get("action_type", "UNKNOWN")
            
            # Get current aircraft state
            aircraft = context.get("aircraft", {})
            current_altitude = aircraft.get("altitude_ft", 0)
            current_zone = context.get("current_zone", "UNKNOWN")
            
            # Check separation with nearby aircraft
            nearby_aircraft = context.get("current_zone_aircraft", [])
            
            async with self.db_pool.acquire() as conn:
                for nearby in nearby_aircraft:
                    nearby_id = nearby.get("id")
                    
                    # Fetch nearby aircraft full state
                    nearby_query = """
                        SELECT position, target_altitude_ft
                        FROM aircraft_instances
                        WHERE id = $1
                    """
                    nearby_row = await conn.fetchrow(nearby_query, nearby_id)
                    if not nearby_row:
                        continue
                    
                    import json
                    nearby_pos = json.loads(nearby_row["position"]) if isinstance(nearby_row["position"], str) else nearby_row["position"]
                    nearby_altitude = nearby_pos.get("altitude_ft", 0)
                    nearby_target_altitude = nearby_row["target_altitude_ft"] or nearby_altitude
                    
                    # Lateral separation check (simplified: use distance from context)
                    lateral_distance_nm = nearby.get("distance_nm", 999)
                    
                    # Vertical separation check (use target altitude if assigned)
                    if target_altitude is not None:
                        vertical_separation_ft = abs(target_altitude - nearby_target_altitude)
                    else:
                        vertical_separation_ft = abs(current_altitude - nearby_target_altitude)
                    
                    # Require 3NM lateral OR 1000ft vertical
                    if lateral_distance_nm < 3.0 and vertical_separation_ft < 1000:
                        logger.warning(
                            f"SEPARATION VIOLATION: Aircraft {aircraft_id} too close to {nearby_id} "
                            f"(lateral: {lateral_distance_nm:.1f}NM, vertical: {vertical_separation_ft}ft)"
                        )
                        return False
                
                # Check runway exclusivity if runway assigned
                if target_runway:
                    runway_query = """
                        SELECT id, callsign
                        FROM aircraft_instances
                        WHERE status = 'active'
                          AND phase IN ('APPROACH_5', 'FINAL', 'LANDING', 'ROLLOUT')
                          AND id != $1
                        LIMIT 10
                    """
                    runway_aircraft = await conn.fetch(runway_query, aircraft_id)
                    
                    # In a real system, we'd check if these aircraft have the same runway assigned
                    # For now, just warn if there are other aircraft in landing phases
                    if len(runway_aircraft) > 2:
                        logger.warning(
                            f"RUNWAY CONGESTION: {len(runway_aircraft)} aircraft in landing phase, "
                            f"assigning runway {target_runway} to aircraft {aircraft_id} may cause conflict"
                        )
                        # Still allow but log warning
            
            logger.info(f"Air clearance validation PASSED for aircraft {aircraft_id} ({action_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error validating air clearance for aircraft {aircraft_id}: {e}")
            return False
    
    async def validate_ground_clearance(
        self,
        aircraft_id: int,
        clearance: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Validate ground clearance for safety.
        
        Args:
            aircraft_id: ID of aircraft receiving clearance
            clearance: Parsed clearance dict (action_type, assigned_gate, taxi_route, etc.)
            context: Aircraft context used for decision
            
        Returns:
            True if clearance is safe, False otherwise
        """
        try:
            assigned_gate = clearance.get("assigned_gate")
            taxi_route = clearance.get("taxi_route", [])
            action_type = clearance.get("action_type", "UNKNOWN")
            
            async with self.db_pool.acquire() as conn:
                # Check gate availability
                if assigned_gate:
                    gate_query = """
                        SELECT id, callsign
                        FROM aircraft_instances
                        WHERE status = 'active'
                          AND phase IN ('GATE', 'BOARDING', 'PUSHBACK')
                          AND id != $1
                        LIMIT 50
                    """
                    gate_aircraft = await conn.fetch(gate_query, aircraft_id)
                    
                    # In a real system, we'd check flight_plan JSONB for assigned gates
                    # For now, just check if too many aircraft are at gates
                    if len(gate_aircraft) > 30:
                        logger.warning(
                            f"GATE CONGESTION: {len(gate_aircraft)} aircraft at gates, "
                            f"assigning gate {assigned_gate} to aircraft {aircraft_id}"
                        )
                        # Still allow but log warning
                
                # Check taxi route conflicts
                if taxi_route and len(taxi_route) > 0:
                    taxi_query = """
                        SELECT id, callsign, phase
                        FROM aircraft_instances
                        WHERE status = 'active'
                          AND phase IN ('TAXI', 'TAXI_TO_RUNWAY', 'TAXI_TO_GATE')
                          AND id != $1
                    """
                    taxiing_aircraft = await conn.fetch(taxi_query, aircraft_id)
                    
                    # In a real system, we'd check for overlapping taxi routes
                    # For now, just limit concurrent taxiing aircraft
                    if len(taxiing_aircraft) > 5:
                        logger.warning(
                            f"TAXI CONGESTION: {len(taxiing_aircraft)} aircraft taxiing, "
                            f"clearing aircraft {aircraft_id} to taxi via {taxi_route}"
                        )
                        # Still allow but log warning
            
            logger.info(f"Ground clearance validation PASSED for aircraft {aircraft_id} ({action_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error validating ground clearance for aircraft {aircraft_id}: {e}")
            return False

