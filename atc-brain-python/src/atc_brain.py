"""
Main ATC Brain orchestrator - coordinates all aircraft control activities
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from database.connection import DatabaseManager
from services.event_publisher import EventPublisher
from config.settings import Settings
from core.navigation import NavigationUtils
from controllers.sid_controller import SIDController
from controllers.star_controller import STARController

logger = logging.getLogger(__name__)

class ATCBrain:
    """Main ATC Brain orchestrator for automated aircraft control"""
    
    def __init__(self, db_manager: DatabaseManager, event_publisher: EventPublisher, settings: Settings):
        self.db_manager = db_manager
        self.event_publisher = event_publisher
        self.settings = settings
        
        # Control state
        self.is_running = False
        self.control_task: Optional[asyncio.Task] = None
        
        # Controllers
        self.sid_controller = SIDController(db_manager, event_publisher)
        self.star_controller = STARController(db_manager, event_publisher)
        
        # Aircraft tracking
        self.aircraft_states: Dict[int, Dict[str, Any]] = {}
        
        logger.info("ATC Brain initialized")
    
    async def start(self):
        """Start the ATC Brain control loop"""
        if self.is_running:
            logger.warning("ATC Brain is already running")
            return
        
        self.is_running = True
        self.control_task = asyncio.create_task(self._control_loop())
        logger.info("ATC Brain started")
    
    async def stop(self):
        """Stop the ATC Brain control loop"""
        if not self.is_running:
            logger.warning("ATC Brain is not running")
            return
        
        self.is_running = False
        
        if self.control_task:
            self.control_task.cancel()
            try:
                await self.control_task
            except asyncio.CancelledError:
                pass
        
        logger.info("ATC Brain stopped")
    
    def is_running(self) -> bool:
        """Check if ATC Brain is currently running"""
        return self.is_running
    
    async def get_active_aircraft_count(self) -> int:
        """Get count of active aircraft"""
        try:
            aircraft = await self.db_manager.get_active_aircraft()
            return len(aircraft)
        except Exception as e:
            logger.error(f"Failed to get active aircraft count: {e}")
            return 0
    
    async def _control_loop(self):
        """Main control loop - runs every update_interval seconds"""
        logger.info("Starting ATC Brain control loop")
        
        while self.is_running:
            try:
                await self._process_aircraft()
                await asyncio.sleep(self.settings.ATC_BRAIN_UPDATE_INTERVAL)
            except asyncio.CancelledError:
                logger.info("Control loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in control loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_aircraft(self):
        """Process all active aircraft"""
        try:
            # Get all active aircraft
            aircraft_list = await self.db_manager.get_active_aircraft()
            
            if not aircraft_list:
                return
            
            logger.debug(f"Processing {len(aircraft_list)} active aircraft")
            
            # Process each aircraft
            for aircraft in aircraft_list:
                await self._process_single_aircraft(aircraft)
                
        except Exception as e:
            logger.error(f"Error processing aircraft: {e}")
    
    async def _process_single_aircraft(self, aircraft: Dict[str, Any]):
        """Process a single aircraft"""
        aircraft_id = aircraft['id']
        flight_phase = aircraft.get('flight_phase', 'UNKNOWN')
        
        try:
            # Update aircraft state tracking
            self.aircraft_states[aircraft_id] = {
                'aircraft': aircraft,
                'last_update': datetime.now(),
                'phase': flight_phase
            }
            
            # Route to appropriate controller based on flight phase
            if flight_phase in ['SPAWNING', 'DEPARTURE']:
                await self.sid_controller.process_aircraft(aircraft)
            elif flight_phase in ['ARRIVAL', 'APPROACH', 'FINAL']:
                await self.star_controller.process_aircraft(aircraft)
            elif flight_phase == 'ENROUTE':
                await self._process_enroute_aircraft(aircraft)
            elif flight_phase == 'LANDING':
                await self._process_landing_aircraft(aircraft)
            elif flight_phase == 'TAKEOFF':
                await self._process_takeoff_aircraft(aircraft)
            else:
                logger.warning(f"Unknown flight phase: {flight_phase} for aircraft {aircraft_id}")
                
        except Exception as e:
            logger.error(f"Error processing aircraft {aircraft_id}: {e}")
    
    async def _process_enroute_aircraft(self, aircraft: Dict[str, Any]):
        """Process aircraft in ENROUTE phase"""
        aircraft_id = aircraft['id']
        
        # For now, just maintain current heading and altitude
        # In a full implementation, this would handle:
        # - Route following
        # - Altitude changes
        # - Speed adjustments
        # - Traffic separation
        
        logger.debug(f"Processing enroute aircraft {aircraft_id}")
    
    async def _process_landing_aircraft(self, aircraft: Dict[str, Any]):
        """Process aircraft in LANDING phase"""
        aircraft_id = aircraft['id']
        
        # Handle landing sequence
        # - Final approach
        # - Touchdown
        # - Rollout
        # - Taxi to gate
        
        logger.debug(f"Processing landing aircraft {aircraft_id}")
    
    async def _process_takeoff_aircraft(self, aircraft: Dict[str, Any]):
        """Process aircraft in TAKEOFF phase"""
        aircraft_id = aircraft['id']
        
        # Handle takeoff sequence
        # - Rollout
        # - Rotation
        # - Initial climb
        # - Departure procedure
        
        logger.debug(f"Processing takeoff aircraft {aircraft_id}")
    
    async def _update_aircraft_position(self, aircraft_id: int, lat: float, lon: float,
                                      altitude: int, heading: float, speed: float):
        """Update aircraft position in database and publish event"""
        try:
            # Update database
            await self.db_manager.update_aircraft_position(
                aircraft_id, lat, lon, altitude, heading, speed
            )
            
            # Publish position update event
            await self.event_publisher.publish_aircraft_position_update(
                aircraft_id, {
                    'lat': lat,
                    'lon': lon,
                    'altitude': altitude,
                    'heading': heading,
                    'speed': speed
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to update aircraft {aircraft_id} position: {e}")
    
    async def _transition_aircraft_phase(self, aircraft_id: int, new_phase: str):
        """Transition aircraft to new flight phase"""
        try:
            # Get current phase
            aircraft = await self.db_manager.get_aircraft_by_id(aircraft_id)
            if not aircraft:
                logger.error(f"Aircraft {aircraft_id} not found")
                return
            
            old_phase = aircraft.get('flight_phase', 'UNKNOWN')
            
            # Update database
            await self.db_manager.update_aircraft_phase(aircraft_id, new_phase)
            
            # Publish phase change event
            await self.event_publisher.publish_aircraft_phase_change(
                aircraft_id, old_phase, new_phase
            )
            
            logger.info(f"Aircraft {aircraft_id} phase changed: {old_phase} -> {new_phase}")
            
        except Exception as e:
            logger.error(f"Failed to transition aircraft {aircraft_id} to {new_phase}: {e}")
    
    async def _issue_atc_command(self, aircraft_id: int, command: str, details: Dict[str, Any]):
        """Issue an ATC command to an aircraft"""
        try:
            await self.event_publisher.publish_atc_command(aircraft_id, command, details)
            logger.info(f"ATC command '{command}' issued to aircraft {aircraft_id}")
        except Exception as e:
            logger.error(f"Failed to issue ATC command to aircraft {aircraft_id}: {e}")
    
    async def _check_for_conflicts(self, aircraft_list: List[Dict[str, Any]]):
        """Check for potential conflicts between aircraft"""
        # This is a placeholder for conflict detection
        # In a full implementation, this would:
        # - Check for separation violations
        # - Detect potential collisions
        # - Issue resolution commands
        
        if len(aircraft_list) < 2:
            return
        
        # Simple conflict detection based on distance
        for i, aircraft1 in enumerate(aircraft_list):
            for aircraft2 in aircraft_list[i+1:]:
                distance = NavigationUtils.haversine_distance(
                    aircraft1['lat'], aircraft1['lon'],
                    aircraft2['lat'], aircraft2['lon']
                )
                
                # Alert if aircraft are too close
                if distance < 5.0:  # 5 nautical miles
                    await self.event_publisher.publish_system_alert(
                        "conflict_warning",
                        f"Aircraft {aircraft1['id']} and {aircraft2['id']} are too close: {distance:.1f}nm",
                        "warning"
                    )
