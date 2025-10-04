"""
STAR (Standard Terminal Arrival Route) Controller
Handles arrival procedures for aircraft
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from database.connection import DatabaseManager
from services.event_publisher import EventPublisher
from core.navigation import NavigationUtils

logger = logging.getLogger(__name__)

class STARController:
    """Controller for Standard Terminal Arrival Route procedures"""
    
    def __init__(self, db_manager: DatabaseManager, event_publisher: EventPublisher):
        self.db_manager = db_manager
        self.event_publisher = event_publisher
        
        # Cached procedures and waypoints
        self.procedures: Dict[str, Dict[str, Any]] = {}
        self.waypoints: Dict[str, Dict[str, Any]] = {}
        
        logger.info("STAR Controller initialized")
    
    async def process_aircraft(self, aircraft: Dict[str, Any]):
        """Process aircraft through STAR procedure"""
        aircraft_id = aircraft['id']
        flight_phase = aircraft.get('flight_phase', 'UNKNOWN')
        
        try:
            if flight_phase == 'ARRIVAL':
                await self._handle_arrival_aircraft(aircraft)
            elif flight_phase == 'APPROACH':
                await self._handle_approach_aircraft(aircraft)
            elif flight_phase == 'FINAL':
                await self._handle_final_aircraft(aircraft)
            else:
                logger.warning(f"STAR Controller received aircraft {aircraft_id} in phase {flight_phase}")
                
        except Exception as e:
            logger.error(f"Error processing aircraft {aircraft_id} in STAR Controller: {e}")
    
    async def _handle_arrival_aircraft(self, aircraft: Dict[str, Any]):
        """Handle aircraft in arrival phase"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        logger.info(f"Handling arrival aircraft {callsign} (ID: {aircraft_id})")
        
        # Assign arrival procedure if not already assigned
        if not aircraft.get('assigned_procedure_id'):
            assigned_procedure = await self._assign_arrival_procedure(aircraft)
            if not assigned_procedure:
                logger.error(f"Could not assign arrival procedure for aircraft {aircraft_id}")
                return
        
        # Get assigned procedure
        procedure_id = aircraft.get('assigned_procedure_id')
        procedure = await self._get_procedure_by_id(procedure_id)
        if not procedure:
            logger.error(f"Procedure {procedure_id} not found for aircraft {aircraft_id}")
            return
        
        # Get current waypoint index
        current_waypoint_index = aircraft.get('current_waypoint_index', 0)
        waypoint_sequence = procedure.get('waypoint_sequence', [])
        
        if current_waypoint_index >= len(waypoint_sequence):
            # Procedure complete, transition to APPROACH
            await self._complete_arrival_procedure(aircraft)
            return
        
        # Get current waypoint
        current_waypoint_name = waypoint_sequence[current_waypoint_index]
        current_waypoint = await self._get_waypoint_by_name(current_waypoint_name)
        
        if not current_waypoint:
            logger.error(f"Waypoint {current_waypoint_name} not found")
            return
        
        # Check if aircraft has reached current waypoint
        distance_to_waypoint = NavigationUtils.haversine_distance(
            aircraft['lat'], aircraft['lon'],
            current_waypoint['lat'], current_waypoint['lon']
        )
        
        if distance_to_waypoint <= 2.0:  # Within 2nm of waypoint
            # Waypoint reached, move to next
            await self._waypoint_reached(aircraft, current_waypoint_index, waypoint_sequence)
        else:
            # Continue to waypoint
            await self._navigate_to_waypoint(aircraft, current_waypoint)
    
    async def _handle_approach_aircraft(self, aircraft: Dict[str, Any]):
        """Handle aircraft in approach phase"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        logger.debug(f"Handling approach aircraft {callsign} (ID: {aircraft_id})")
        
        # For approach phase, we need to:
        # 1. Descend to approach altitude
        # 2. Reduce speed
        # 3. Align with runway
        # 4. Transition to FINAL when ready
        
        # Simple approach logic - descend and slow down
        current_altitude = aircraft.get('altitude', 10000)
        target_altitude = 3000  # Approach altitude
        
        if current_altitude > target_altitude:
            # Descend
            new_altitude = max(target_altitude, current_altitude - 1000)
            await self._update_aircraft_altitude(aircraft, new_altitude)
        
        # Check if ready for final approach
        if current_altitude <= target_altitude:
            # Transition to FINAL
            await self.db_manager.update_aircraft_phase(aircraft_id, 'FINAL')
            await self.event_publisher.publish_aircraft_phase_change(
                aircraft_id, 'APPROACH', 'FINAL'
            )
            logger.info(f"Aircraft {callsign} transitioning to FINAL approach")
    
    async def _handle_final_aircraft(self, aircraft: Dict[str, Any]):
        """Handle aircraft in final approach phase"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        logger.debug(f"Handling final approach aircraft {callsign} (ID: {aircraft_id})")
        
        # For final approach, we need to:
        # 1. Maintain approach path
        # 2. Continue descent
        # 3. Prepare for landing
        
        # Simple final approach logic
        current_altitude = aircraft.get('altitude', 3000)
        target_altitude = 0  # Ground level
        
        if current_altitude > 500:
            # Continue descent
            new_altitude = max(0, current_altitude - 500)
            await self._update_aircraft_altitude(aircraft, new_altitude)
        else:
            # Landing complete
            await self._complete_landing(aircraft)
    
    async def _assign_arrival_procedure(self, aircraft: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assign appropriate STAR procedure to aircraft"""
        try:
            # Get available STAR procedures for CYYZ
            procedures = await self.db_manager.get_procedures_by_airport('CYYZ')
            star_procedures = [p for p in procedures if p['type'] == 'STAR']
            
            if not star_procedures:
                logger.error("No STAR procedures found for CYYZ")
                return None
            
            # Simple assignment logic - could be more sophisticated
            # For now, assign first available STAR
            assigned_procedure = star_procedures[0]
            
            # Update aircraft with assigned procedure
            await self.db_manager.execute(
                "UPDATE aircraft_instances SET assigned_procedure_id = $1 WHERE id = $2",
                assigned_procedure['id'], aircraft['id']
            )
            
            return assigned_procedure
            
        except Exception as e:
            logger.error(f"Error assigning arrival procedure: {e}")
            return None
    
    async def _get_procedure_by_id(self, procedure_id: int) -> Optional[Dict[str, Any]]:
        """Get procedure by ID"""
        try:
            query = "SELECT * FROM procedures WHERE id = $1"
            return await self.db_manager.fetch_one(query, procedure_id)
        except Exception as e:
            logger.error(f"Error getting procedure {procedure_id}: {e}")
            return None
    
    async def _get_waypoint_by_name(self, waypoint_name: str) -> Optional[Dict[str, Any]]:
        """Get waypoint by name"""
        try:
            query = "SELECT * FROM waypoints WHERE name = $1"
            return await self.db_manager.fetch_one(query, waypoint_name)
        except Exception as e:
            logger.error(f"Error getting waypoint {waypoint_name}: {e}")
            return None
    
    async def _navigate_to_waypoint(self, aircraft: Dict[str, Any], waypoint: Dict[str, Any]):
        """Navigate aircraft to waypoint"""
        aircraft_id = aircraft['id']
        
        # Calculate bearing to waypoint
        bearing = NavigationUtils.calculate_bearing(
            aircraft['lat'], aircraft['lon'],
            waypoint['lat'], waypoint['lon']
        )
        
        # Calculate new position (simulate movement)
        speed_kts = aircraft.get('speed', 300)
        distance_per_update = (speed_kts * self.db_manager.settings.ATC_BRAIN_UPDATE_INTERVAL) / 3600  # nm
        
        new_lat, new_lon = NavigationUtils.calculate_new_position(
            aircraft['lat'], aircraft['lon'], bearing, distance_per_update
        )
        
        # Update aircraft position
        await self.db_manager.update_aircraft_position(
            aircraft_id, new_lat, new_lon,
            aircraft.get('altitude', 10000), bearing, speed_kts
        )
        
        # Publish position update
        await self.event_publisher.publish_aircraft_position_update(
            aircraft_id, {
                'lat': new_lat,
                'lon': new_lon,
                'altitude': aircraft.get('altitude', 10000),
                'heading': bearing,
                'speed': speed_kts
            }
        )
    
    async def _waypoint_reached(self, aircraft: Dict[str, Any], current_index: int, 
                              waypoint_sequence: List[str]):
        """Handle aircraft reaching a waypoint"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        # Move to next waypoint
        next_index = current_index + 1
        
        if next_index >= len(waypoint_sequence):
            # Procedure complete, transition to APPROACH
            await self._complete_arrival_procedure(aircraft)
        else:
            # Update waypoint index
            await self.db_manager.execute(
                "UPDATE aircraft_instances SET current_waypoint_index = $1 WHERE id = $2",
                next_index, aircraft_id
            )
            
            next_waypoint = waypoint_sequence[next_index]
            logger.info(f"Aircraft {callsign} reached waypoint, proceeding to {next_waypoint}")
    
    async def _complete_arrival_procedure(self, aircraft: Dict[str, Any]):
        """Complete arrival procedure and transition to APPROACH"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        # Transition to APPROACH phase
        await self.db_manager.update_aircraft_phase(aircraft_id, 'APPROACH')
        
        # Publish phase change
        await self.event_publisher.publish_aircraft_phase_change(
            aircraft_id, 'ARRIVAL', 'APPROACH'
        )
        
        logger.info(f"Aircraft {callsign} completed arrival procedure, now APPROACH")
    
    async def _update_aircraft_altitude(self, aircraft: Dict[str, Any], new_altitude: int):
        """Update aircraft altitude"""
        aircraft_id = aircraft['id']
        
        # Update database
        await self.db_manager.execute(
            "UPDATE aircraft_instances SET altitude = $1 WHERE id = $2",
            new_altitude, aircraft_id
        )
        
        # Publish altitude change
        await self.event_publisher.publish_atc_command(
            aircraft_id, 'altitude_change', {'altitude': new_altitude}
        )
    
    async def _complete_landing(self, aircraft: Dict[str, Any]):
        """Complete aircraft landing"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        # Transition to LANDING phase
        await self.db_manager.update_aircraft_phase(aircraft_id, 'LANDING')
        
        # Publish phase change
        await self.event_publisher.publish_aircraft_phase_change(
            aircraft_id, 'FINAL', 'LANDING'
        )
        
        logger.info(f"Aircraft {callsign} completed landing")
