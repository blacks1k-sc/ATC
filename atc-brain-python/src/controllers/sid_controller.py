"""
SID (Standard Instrument Departure) Controller
Handles departure procedures for aircraft
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from database.connection import DatabaseManager
from services.event_publisher import EventPublisher
from core.navigation import NavigationUtils

logger = logging.getLogger(__name__)

class SIDController:
    """Controller for Standard Instrument Departure procedures"""
    
    def __init__(self, db_manager: DatabaseManager, event_publisher: EventPublisher):
        self.db_manager = db_manager
        self.event_publisher = event_publisher
        
        # Cached procedures and waypoints
        self.procedures: Dict[str, Dict[str, Any]] = {}
        self.waypoints: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SID Controller initialized")
    
    async def process_aircraft(self, aircraft: Dict[str, Any]):
        """Process aircraft through SID procedure"""
        aircraft_id = aircraft['id']
        flight_phase = aircraft.get('flight_phase', 'UNKNOWN')
        
        try:
            if flight_phase == 'SPAWNING':
                await self._handle_spawning_aircraft(aircraft)
            elif flight_phase == 'DEPARTURE':
                await self._handle_departure_aircraft(aircraft)
            else:
                logger.warning(f"SID Controller received aircraft {aircraft_id} in phase {flight_phase}")
                
        except Exception as e:
            logger.error(f"Error processing aircraft {aircraft_id} in SID Controller: {e}")
    
    async def _handle_spawning_aircraft(self, aircraft: Dict[str, Any]):
        """Handle aircraft that just spawned (departure)"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        logger.info(f"Handling spawning departure aircraft {callsign} (ID: {aircraft_id})")
        
        # Assign departure procedure
        assigned_procedure = await self._assign_departure_procedure(aircraft)
        if not assigned_procedure:
            logger.error(f"Could not assign departure procedure for aircraft {aircraft_id}")
            return
        
        # Load procedure waypoints
        waypoints = await self._load_procedure_waypoints(assigned_procedure)
        if not waypoints:
            logger.error(f"Could not load waypoints for procedure {assigned_procedure['name']}")
            return
        
        # Transition to DEPARTURE phase
        await self.db_manager.update_aircraft_phase(aircraft_id, 'DEPARTURE')
        
        # Issue initial departure clearance
        await self._issue_departure_clearance(aircraft, assigned_procedure, waypoints)
        
        logger.info(f"Aircraft {callsign} assigned to {assigned_procedure['name']} departure")
    
    async def _handle_departure_aircraft(self, aircraft: Dict[str, Any]):
        """Handle aircraft in departure phase"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        # Get assigned procedure
        procedure_id = aircraft.get('assigned_procedure_id')
        if not procedure_id:
            logger.error(f"Aircraft {aircraft_id} has no assigned procedure")
            return
        
        procedure = await self._get_procedure_by_id(procedure_id)
        if not procedure:
            logger.error(f"Procedure {procedure_id} not found for aircraft {aircraft_id}")
            return
        
        # Get current waypoint index
        current_waypoint_index = aircraft.get('current_waypoint_index', 0)
        waypoint_sequence = procedure.get('waypoint_sequence', [])
        
        if current_waypoint_index >= len(waypoint_sequence):
            # Procedure complete, transition to ENROUTE
            await self._complete_departure_procedure(aircraft)
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
    
    async def _assign_departure_procedure(self, aircraft: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assign appropriate SID procedure to aircraft"""
        try:
            # Get available SID procedures for CYYZ
            procedures = await self.db_manager.get_procedures_by_airport('CYYZ')
            sid_procedures = [p for p in procedures if p['type'] == 'SID']
            
            if not sid_procedures:
                logger.error("No SID procedures found for CYYZ")
                return None
            
            # Simple assignment logic - could be more sophisticated
            # For now, assign first available SID
            assigned_procedure = sid_procedures[0]
            
            # Update aircraft with assigned procedure
            await self.db_manager.execute(
                "UPDATE aircraft_instances SET assigned_procedure_id = $1 WHERE id = $2",
                assigned_procedure['id'], aircraft['id']
            )
            
            return assigned_procedure
            
        except Exception as e:
            logger.error(f"Error assigning departure procedure: {e}")
            return None
    
    async def _load_procedure_waypoints(self, procedure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load waypoints for a procedure"""
        try:
            waypoint_sequence = procedure.get('waypoint_sequence', [])
            waypoints = []
            
            for waypoint_name in waypoint_sequence:
                waypoint = await self._get_waypoint_by_name(waypoint_name)
                if waypoint:
                    waypoints.append(waypoint)
                else:
                    logger.error(f"Waypoint {waypoint_name} not found")
            
            return waypoints
            
        except Exception as e:
            logger.error(f"Error loading procedure waypoints: {e}")
            return []
    
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
    
    async def _issue_departure_clearance(self, aircraft: Dict[str, Any], 
                                        procedure: Dict[str, Any], waypoints: List[Dict[str, Any]]):
        """Issue departure clearance to aircraft"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        # Issue clearance
        clearance_details = {
            'procedure': procedure['name'],
            'first_waypoint': waypoints[0]['name'] if waypoints else 'Unknown',
            'altitude': '8000',  # Initial altitude
            'speed': '250'  # Initial speed
        }
        
        await self.event_publisher.publish_atc_command(
            aircraft_id, 'departure_clearance', clearance_details
        )
        
        logger.info(f"Departure clearance issued to {callsign}: {procedure['name']}")
    
    async def _navigate_to_waypoint(self, aircraft: Dict[str, Any], waypoint: Dict[str, Any]):
        """Navigate aircraft to waypoint"""
        aircraft_id = aircraft['id']
        
        # Calculate bearing to waypoint
        bearing = NavigationUtils.calculate_bearing(
            aircraft['lat'], aircraft['lon'],
            waypoint['lat'], waypoint['lon']
        )
        
        # Calculate new position (simulate movement)
        speed_kts = aircraft.get('speed', 250)
        distance_per_update = (speed_kts * self.db_manager.settings.ATC_BRAIN_UPDATE_INTERVAL) / 3600  # nm
        
        new_lat, new_lon = NavigationUtils.calculate_new_position(
            aircraft['lat'], aircraft['lon'], bearing, distance_per_update
        )
        
        # Update aircraft position
        await self.db_manager.update_aircraft_position(
            aircraft_id, new_lat, new_lon,
            aircraft.get('altitude', 8000), bearing, speed_kts
        )
        
        # Publish position update
        await self.event_publisher.publish_aircraft_position_update(
            aircraft_id, {
                'lat': new_lat,
                'lon': new_lon,
                'altitude': aircraft.get('altitude', 8000),
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
            # Procedure complete
            await self._complete_departure_procedure(aircraft)
        else:
            # Update waypoint index
            await self.db_manager.execute(
                "UPDATE aircraft_instances SET current_waypoint_index = $1 WHERE id = $2",
                next_index, aircraft_id
            )
            
            next_waypoint = waypoint_sequence[next_index]
            logger.info(f"Aircraft {callsign} reached waypoint, proceeding to {next_waypoint}")
    
    async def _complete_departure_procedure(self, aircraft: Dict[str, Any]):
        """Complete departure procedure and transition to ENROUTE"""
        aircraft_id = aircraft['id']
        callsign = aircraft.get('callsign', 'Unknown')
        
        # Transition to ENROUTE phase
        await self.db_manager.update_aircraft_phase(aircraft_id, 'ENROUTE')
        
        # Publish phase change
        await self.event_publisher.publish_aircraft_phase_change(
            aircraft_id, 'DEPARTURE', 'ENROUTE'
        )
        
        logger.info(f"Aircraft {callsign} completed departure procedure, now ENROUTE")
