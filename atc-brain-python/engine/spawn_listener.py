"""
Spawn listener that subscribes to aircraft.created events from Redis.
Detects new arrivals and marks them for ENGINE control.
"""

import redis
import json
import asyncio
import os
from typing import Optional, Callable
from dotenv import load_dotenv

load_dotenv()


class SpawnListener:
    """Listens for new aircraft creation events and assigns ENGINE control."""
    
    def __init__(self, state_manager, callback: Optional[Callable] = None):
        """
        Initialize spawn listener.
        
        Args:
            state_manager: StateManager instance for database updates
            callback: Optional callback function when new aircraft detected
        """
        self.state_manager = state_manager
        self.callback = callback
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.channel = os.getenv("EVENT_CHANNEL", "atc:events")
        self.running = False
        
        self.redis_config = {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD") or None,
            "db": 0,
            "decode_responses": True,
        }
    
    def connect(self):
        """Initialize Redis connection and subscription."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(**self.redis_config)
                self.pubsub = self.redis_client.pubsub()
                self.pubsub.subscribe(self.channel)
                
                # Consume the subscription confirmation message
                self.pubsub.get_message()
                
                print(f"✅ SpawnListener: Subscribed to Redis channel '{self.channel}'")
            except Exception as e:
                print(f"❌ SpawnListener: Failed to connect to Redis: {e}")
                self.redis_client = None
                self.pubsub = None
    
    def disconnect(self):
        """Close Redis connection."""
        self.running = False
        
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
            self.pubsub = None
        
        if self.redis_client:
            self.redis_client.close()
            self.redis_client = None
        
        print("🔌 SpawnListener: Redis connection closed")
    
    async def process_aircraft_created_event(self, event_data: dict):
        """
        Process aircraft.created event.
        If it's an arrival, mark for ENGINE control.
        
        Args:
            event_data: Event payload from Redis
        """
        try:
            aircraft = event_data.get("aircraft", {})
            aircraft_id = aircraft.get("id")
            flight_type = aircraft.get("flight_type")
            callsign = aircraft.get("callsign", "UNKNOWN")
            
            # Only handle arrivals
            if flight_type != "ARRIVAL":
                return
            
            print(f"🛬 SpawnListener: New arrival detected: {callsign} (ID: {aircraft_id})")
            
            # Mark for ENGINE control
            success = await self.state_manager.update_aircraft_state(aircraft_id, {
                "controller": "ENGINE",
                "phase": "CRUISE"
            })
            
            if success:
                print(f"   ✅ Assigned ENGINE control to {callsign}")
                
                # Call optional callback
                if self.callback:
                    await self.callback(aircraft)
            else:
                print(f"   ⚠️  Failed to assign ENGINE control to {callsign}")
        
        except Exception as e:
            print(f"❌ SpawnListener: Error processing aircraft.created event: {e}")
    
    async def listen_async(self):
        """
        Async listen loop for Redis messages.
        Runs in background task.
        """
        if not self.pubsub:
            self.connect()
        
        if not self.pubsub:
            print("❌ SpawnListener: Cannot start - Redis unavailable")
            return
        
        self.running = True
        print("👂 SpawnListener: Started listening for aircraft.created events")
        
        while self.running:
            try:
                # Non-blocking get with timeout
                message = self.pubsub.get_message(timeout=0.1)
                
                if message and message["type"] == "message":
                    try:
                        # Parse JSON message
                        payload = json.loads(message["data"])
                        event_type = payload.get("type")
                        
                        # Filter for aircraft.created events
                        if event_type == "aircraft.created":
                            data = payload.get("data", {})
                            await self.process_aircraft_created_event(data)
                    
                    except json.JSONDecodeError:
                        pass  # Ignore malformed messages
                
                # Small sleep to prevent busy loop
                await asyncio.sleep(0.1)
            
            except Exception as e:
                print(f"⚠️  SpawnListener: Error in listen loop: {e}")
                await asyncio.sleep(1.0)  # Back off on error
        
        print("👂 SpawnListener: Stopped listening")
    
    def start_background_task(self) -> asyncio.Task:
        """
        Start listener as background asyncio task.
        
        Returns:
            Asyncio Task object
        """
        return asyncio.create_task(self.listen_async())

