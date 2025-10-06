"""
Event publisher for Redis pub/sub integration.
Publishes aircraft state updates and threshold events to the same channels used by Next.js.
"""

import redis
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


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
    
    def connect(self):
        """Initialize Redis connection."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(**self.redis_config)
                # Test connection
                self.redis_client.ping()
                print(f"✅ EventPublisher: Connected to Redis on channel '{self.channel}'")
            except Exception as e:
                print(f"❌ EventPublisher: Failed to connect to Redis: {e}")
                print(f"   Events will not be published.")
                self.redis_client = None
    
    def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            self.redis_client.close()
            self.redis_client = None
            print("🔌 EventPublisher: Redis connection closed")
    
    def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Publish event to Redis channel.
        
        Args:
            event_type: Event type (e.g., "aircraft.position_updated")
            data: Event payload data
        
        Returns:
            True if published successfully, False otherwise
        """
        if not self.redis_client:
            self.connect()
        
        if not self.redis_client:
            return False  # Redis unavailable
        
        try:
            message = {
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": data
            }
            
            message_json = json.dumps(message)
            self.redis_client.publish(self.channel, message_json)
            
            return True
            
        except Exception as e:
            print(f"⚠️  EventPublisher: Failed to publish event: {e}")
            return False
    
    def publish_aircraft_position_updated(self, aircraft: Dict[str, Any]) -> bool:
        """
        Publish aircraft position update event.
        Compatible with Next.js eventBus.publishAircraftPositionUpdated()
        
        Args:
            aircraft: Aircraft data dictionary
        
        Returns:
            True if successful
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
        
        return self.publish_event("aircraft.position_updated", data)
    
    def publish_threshold_event(self, event_name: str, aircraft: Dict[str, Any],
                               details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Publish threshold event (ENTERED_ENTRY_ZONE, HANDOFF_READY, TOUCHDOWN).
        
        Args:
            event_name: Event name
            aircraft: Aircraft data
            details: Additional event details
        
        Returns:
            True if successful
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
        
        return self.publish_event("aircraft.threshold_event", data)
    
    def publish_state_snapshot(self, tick: int, aircraft_list: list[Dict[str, Any]]) -> bool:
        """
        Publish complete state snapshot for telemetry.
        
        Args:
            tick: Current tick number
            aircraft_list: List of all active aircraft
        
        Returns:
            True if successful
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
        
        return self.publish_event("engine.state_snapshot", data)
    
    def publish_system_status(self, status: Dict[str, Any]) -> bool:
        """
        Publish engine system status.
        
        Args:
            status: Status dictionary
        
        Returns:
            True if successful
        """
        return self.publish_event("system.status", {"status": status})

