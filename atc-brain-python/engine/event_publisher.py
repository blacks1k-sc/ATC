"""
Event publisher for Redis pub/sub integration.
Publishes aircraft state updates and threshold events to the same channels used by Next.js.
"""

import redis.asyncio as redis
import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes events to Redis channels compatible with Next.js eventBus."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.channel = os.getenv("EVENT_CHANNEL", "atc:events")
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_config = {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD") or None,
            "db": 0,
            "decode_responses": True,
        }
    
    async def connect(self):
        """Initialize async Redis connection."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(**self.redis_config)
                # Test connection
                await self.redis_client.ping()
                logger.info(f"EventPublisher: Connected to Redis on channel '{self.channel}'")
            except Exception as e:
                logger.error(f"EventPublisher: Failed to connect to Redis: {e}")
                logger.warning(f"   Events will not be published.")
                self.redis_client = None
    
    async def disconnect(self):
        """Close async Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("EventPublisher: Redis connection closed")
    
    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Publish event to Redis channel (async).
        
        Args:
            event_type: Event type (e.g., "aircraft.position_updated")
            data: Event payload data
        
        Returns:
            True if published successfully, False otherwise
        """
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client:
            return False  # Redis unavailable
        
        try:
            message = {
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": data
            }
            
            message_json = json.dumps(message)
            await self.redis_client.publish(self.channel, message_json)
            
            return True
            
        except Exception as e:
            logger.error(f"EventPublisher: Failed to publish event: {e}")
            return False
    
    async def batch_publish_events(self, events: List[tuple[str, Dict[str, Any]]]) -> int:
        """
        Batch publish multiple events to Redis (async).
        
        Args:
            events: List of (event_type, data) tuples
        
        Returns:
            Number of events successfully published
        """
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client or not events:
            return 0
        
        success_count = 0
        
        try:
            # Use pipeline for batch operations
            pipe = self.redis_client.pipeline()
            
            for event_type, data in events:
                message = {
                    "type": event_type,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "data": data
                }
                message_json = json.dumps(message)
                pipe.publish(self.channel, message_json)
            
            # Execute all publishes at once
            await pipe.execute()
            success_count = len(events)
            
        except Exception as e:
            logger.error(f"EventPublisher: Failed to batch publish events: {e}")
        
        return success_count
    
    def prepare_aircraft_position_event(self, aircraft: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Prepare aircraft position update event data (non-blocking).
        Returns tuple for batch publishing.
        
        Args:
            aircraft: Aircraft data dictionary
        
        Returns:
            Tuple of (event_type, data)
        """
        position = aircraft.get("position", {})
        
        data = {
            "aircraft": {
                "id": aircraft.get("id"),
                "icao24": aircraft.get("icao24"),
                "callsign": aircraft.get("callsign"),
                "registration": aircraft.get("registration"),
                "position": position,
                "controller": aircraft.get("controller"),
                "phase": aircraft.get("phase"),
                "vertical_speed_fpm": aircraft.get("vertical_speed_fpm"),
                "distance_to_airport_nm": aircraft.get("distance_to_airport_nm"),
            },
            "position": position
        }
        
        return ("aircraft.position_updated", data)
    
    def prepare_threshold_event(self, event_name: str, aircraft: Dict[str, Any],
                                details: Optional[Dict[str, Any]] = None) -> tuple[str, Dict[str, Any]]:
        """
        Prepare threshold event data (non-blocking).
        Returns tuple for batch publishing.
        
        Args:
            event_name: Event name
            aircraft: Aircraft data
            details: Additional event details
        
        Returns:
            Tuple of (event_type, data)
        """
        position = aircraft.get("position", {})
        
        data = {
            "event_type": event_name,
            "aircraft": {
                "id": aircraft.get("id"),
                "icao24": aircraft.get("icao24"),
                "callsign": aircraft.get("callsign"),
                "lat": position.get("lat"),
                "lon": position.get("lon"),
                "altitude_ft": position.get("altitude_ft"),
                "speed_kts": position.get("speed_kts"),
                "heading": position.get("heading"),
                "controller": aircraft.get("controller"),
                "phase": aircraft.get("phase"),
                "distance_to_airport_nm": aircraft.get("distance_to_airport_nm"),
            }
        }
        
        if details:
            data.update(details)
        
        return ("aircraft.threshold_event", data)
    
    def prepare_state_snapshot_event(self, tick: int, aircraft_list: list[Dict[str, Any]]) -> tuple[str, Dict[str, Any]]:
        """
        Prepare state snapshot event data (non-blocking).
        Returns tuple for batch publishing.
        
        Args:
            tick: Current tick number
            aircraft_list: List of all active aircraft
        
        Returns:
            Tuple of (event_type, data)
        """
        data = {
            "tick": tick,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "aircraft_count": len(aircraft_list),
            "aircraft": [
                {
                    "id": ac.get("id"),
                    "callsign": ac.get("callsign"),
                    "position": ac.get("position"),
                    "controller": ac.get("controller"),
                    "phase": ac.get("phase"),
                    "distance_to_airport_nm": ac.get("distance_to_airport_nm"),
                }
                for ac in aircraft_list
            ]
        }
        
        return ("engine.state_snapshot", data)
    
    async def publish_system_status(self, status: Dict[str, Any]) -> bool:
        """
        Publish engine system status.
        
        Args:
            status: Status dictionary
        
        Returns:
            True if successful
        """
        return await self.publish_event("system.status", {"status": status})

