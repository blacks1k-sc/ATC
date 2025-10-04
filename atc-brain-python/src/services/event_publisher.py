"""
Redis event publisher for real-time communication with Next.js frontend
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import redis.asyncio as redis
from config.settings import Settings

logger = logging.getLogger(__name__)

class EventPublisher:
    """Publishes events to Redis for real-time updates"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event to Redis"""
        try:
            if not self.redis_client:
                logger.error("Redis client not connected")
                return
            
            event_data = {
                "type": event_type,
                "data": data,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Publish to Redis channel
            await self.redis_client.publish("atc_events", json.dumps(event_data))
            logger.debug(f"Published event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
    
    async def publish_aircraft_spawned(self, aircraft_data: Dict[str, Any]):
        """Publish aircraft spawned event"""
        await self.publish_event("aircraft:spawned", {
            "aircraft": aircraft_data,
            "message": f"Aircraft {aircraft_data.get('callsign', 'Unknown')} spawned"
        })
    
    async def publish_aircraft_position_update(self, aircraft_id: int, position_data: Dict[str, Any]):
        """Publish aircraft position update"""
        await self.publish_event("aircraft:position_update", {
            "aircraft_id": aircraft_id,
            "position": position_data,
            "message": f"Aircraft {aircraft_id} position updated"
        })
    
    async def publish_aircraft_phase_change(self, aircraft_id: int, old_phase: str, new_phase: str):
        """Publish aircraft phase change"""
        await self.publish_event("aircraft:phase_change", {
            "aircraft_id": aircraft_id,
            "old_phase": old_phase,
            "new_phase": new_phase,
            "message": f"Aircraft {aircraft_id} phase changed from {old_phase} to {new_phase}"
        })
    
    async def publish_aircraft_completed(self, aircraft_data: Dict[str, Any]):
        """Publish aircraft completed event"""
        await self.publish_event("aircraft:completed", {
            "aircraft": aircraft_data,
            "message": f"Aircraft {aircraft_data.get('callsign', 'Unknown')} completed flight"
        })
    
    async def publish_atc_command(self, aircraft_id: int, command: str, details: Dict[str, Any]):
        """Publish ATC command to aircraft"""
        await self.publish_event("atc:command", {
            "aircraft_id": aircraft_id,
            "command": command,
            "details": details,
            "message": f"ATC command '{command}' issued to aircraft {aircraft_id}"
        })
    
    async def publish_system_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Publish system alert"""
        await self.publish_event("system:alert", {
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": asyncio.get_event_loop().time()
        })
