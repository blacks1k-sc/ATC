"""
Core kinematics engine with 1 Hz deterministic tick loop.
Orchestrates aircraft state updates, event emission, and database persistence.
"""

import asyncio
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

from .state_manager import StateManager
from .event_publisher import EventPublisher
from .spawn_listener import SpawnListener
from .kinematics import update_aircraft_state
from .airport_data import get_airport_data
from .constants import (
    DT,
    ENTRY_ZONE_THRESHOLD_NM,
    HANDOFF_READY_THRESHOLD_NM,
    TOUCHDOWN_ALTITUDE_FT,
    EVENT_ENTERED_ENTRY_ZONE,
    EVENT_HANDOFF_READY,
    EVENT_TOUCHDOWN,
    TICK_WARNING_THRESHOLD_SEC,
    CYYZ_ELEVATION_FT,
)
from .geo_utils import altitude_msl_to_agl

load_dotenv()


class KinematicsEngine:
    """Main kinematics engine controller."""
    
    def __init__(self):
        self.state_manager = StateManager()
        self.event_publisher = EventPublisher()
        self.spawn_listener = SpawnListener(self.state_manager, self.on_aircraft_spawned)
        
        self.airport = get_airport_data()
        
        self.tick_count = 0
        self.running = False
        self.start_time = 0.0
        
        # Telemetry
        self.telemetry_dir = os.getenv("TELEMETRY_DIR", "telemetry/phaseA")
        self.telemetry_buffer: List[Dict[str, Any]] = []
        
        # Statistics
        self.stats = {
            "aircraft_processed": 0,
            "events_fired": 0,
            "total_ticks": 0,
            "avg_tick_duration": 0.0,
        }
    
    async def initialize(self):
        """Initialize all subsystems."""
        print("🚀 Initializing Kinematics Engine...")
        
        # Connect to database
        await self.state_manager.connect()
        
        # Connect to Redis
        self.event_publisher.connect()
        self.spawn_listener.connect()
        
        # Load airport data
        print(f"✈️  Airport: {self.airport}")
        print(f"   Entry waypoints: {len(self.airport.entry_waypoints)}")
        
        # Create telemetry directory
        os.makedirs(self.telemetry_dir, exist_ok=True)
        
        print("✅ Kinematics Engine initialized")
    
    async def shutdown(self):
        """Shutdown all subsystems."""
        print("\n🛑 Shutting down Kinematics Engine...")
        
        self.running = False
        
        # Disconnect from database
        await self.state_manager.disconnect()
        
        # Disconnect from Redis
        self.event_publisher.disconnect()
        self.spawn_listener.disconnect()
        
        # Write final telemetry
        await self.flush_telemetry()
        
        # Print statistics
        self.print_statistics()
        
        print("✅ Kinematics Engine shutdown complete")
    
    async def on_aircraft_spawned(self, aircraft: Dict[str, Any]):
        """
        Callback when new aircraft is spawned.
        
        Args:
            aircraft: Aircraft data dictionary
        """
        callsign = aircraft.get("callsign", "UNKNOWN")
        aircraft_id = aircraft.get("id")
        print(f"   🎯 ENGINE now controlling: {callsign}")
        
        # Create database event for log display
        await self.state_manager.create_event({
            "level": "INFO",
            "type": "aircraft.engine_assigned",
            "message": f"ENGINE assigned control of {callsign}",
            "details": {
                "callsign": callsign,
                "controller": "ENGINE",
                "phase": "CRUISE"
            },
            "aircraft_id": aircraft_id,
            "sector": "ENGINE",
            "direction": "SYS"
        })
    
    async def tick(self):
        """
        Execute one engine tick (1 Hz).
        Fetches aircraft, applies kinematics, emits events, persists state.
        """
        tick_start = time.time()
        
        # Fetch active arrivals controlled by ENGINE
        aircraft_list = await self.state_manager.get_active_arrivals(controller="ENGINE")
        
        if not aircraft_list:
            # No aircraft to process this tick
            return
        
        events_this_tick = 0
        
        for aircraft in aircraft_list:
            try:
                await self.process_aircraft(aircraft)
                events_this_tick += 1
            except Exception as e:
                callsign = aircraft.get("callsign", "UNKNOWN")
                print(f"⚠️  Error processing {callsign}: {e}")
        
        # Update statistics
        self.stats["aircraft_processed"] += len(aircraft_list)
        self.stats["total_ticks"] += 1
        
        # Publish state snapshot periodically (every 10 ticks)
        if self.tick_count % 10 == 0:
            self.event_publisher.publish_state_snapshot(self.tick_count, aircraft_list)
            
            # Create database event for engine status
            await self.state_manager.create_event({
                "level": "INFO",
                "type": "engine.status",
                "message": f"Engine tick {self.tick_count}: processing {len(aircraft_list)} aircraft",
                "details": {
                    "tick_count": self.tick_count,
                    "aircraft_count": len(aircraft_list),
                    "stats": self.stats
                },
                "sector": "ENGINE",
                "direction": "SYS"
            })
        
        # Check tick duration
        tick_duration = time.time() - tick_start
        self.stats["avg_tick_duration"] = (
            (self.stats["avg_tick_duration"] * (self.tick_count - 1) + tick_duration) / self.tick_count
            if self.tick_count > 0 else tick_duration
        )
        
        if tick_duration > TICK_WARNING_THRESHOLD_SEC:
            print(f"⚠️  Tick {self.tick_count} took {tick_duration:.3f}s (threshold: {TICK_WARNING_THRESHOLD_SEC}s)")
    
    async def process_aircraft(self, aircraft: Dict[str, Any]):
        """
        Process one aircraft: update kinematics, check thresholds, emit events.
        
        Args:
            aircraft: Aircraft data dictionary
        """
        aircraft_id = aircraft["id"]
        callsign = aircraft.get("callsign", "UNKNOWN")
        
        # Apply kinematics formulas
        updated = update_aircraft_state(aircraft, DT)
        
        # Extract updated state
        position = updated["position"]
        distance_nm = updated.get("distance_to_airport_nm", 999.0)
        altitude_ft = position["altitude_ft"]
        altitude_agl = altitude_msl_to_agl(altitude_ft, CYYZ_ELEVATION_FT)
        
        # Determine phase
        phase = self.determine_phase(distance_nm, altitude_agl)
        updated["phase"] = phase
        
        # Check threshold events
        last_event = aircraft.get("last_event_fired", "")
        new_event = None
        
        if altitude_agl < TOUCHDOWN_ALTITUDE_FT and EVENT_TOUCHDOWN not in last_event:
            new_event = EVENT_TOUCHDOWN
            print(f"🛬 TOUCHDOWN: {callsign} at {altitude_agl:.0f} ft AGL")
            
            # Mark as landed
            await self.state_manager.mark_touchdown(aircraft_id)
            
            # Create database event
            await self.state_manager.create_event({
                "level": "INFO",
                "type": "aircraft.touchdown",
                "message": f"{callsign} touchdown at {altitude_agl:.0f} ft AGL",
                "details": {
                    "callsign": callsign,
                    "altitude_agl": altitude_agl,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "TWR",
                "direction": "SYS"
            })
            
            # Publish event
            self.event_publisher.publish_threshold_event(new_event, updated)
            self.stats["events_fired"] += 1
            
            # Stop processing this aircraft
            return
        
        elif distance_nm <= HANDOFF_READY_THRESHOLD_NM and EVENT_HANDOFF_READY not in last_event:
            new_event = EVENT_HANDOFF_READY
            print(f"🤝 HANDOFF_READY: {callsign} at {distance_nm:.1f} NM")
            
            # Create database event
            await self.state_manager.create_event({
                "level": "INFO",
                "type": "aircraft.handoff_ready",
                "message": f"{callsign} ready for handoff at {distance_nm:.1f} NM",
                "details": {
                    "callsign": callsign,
                    "distance_nm": distance_nm,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "APP",
                "direction": "SYS"
            })
            
            # Publish event
            self.event_publisher.publish_threshold_event(new_event, updated)
            self.stats["events_fired"] += 1
        
        elif distance_nm <= ENTRY_ZONE_THRESHOLD_NM and EVENT_ENTERED_ENTRY_ZONE not in last_event:
            new_event = EVENT_ENTERED_ENTRY_ZONE
            print(f"📍 ENTERED_ENTRY_ZONE: {callsign} at {distance_nm:.1f} NM")
            
            # Create database event
            await self.state_manager.create_event({
                "level": "INFO",
                "type": "aircraft.entered_entry_zone",
                "message": f"{callsign} entered entry zone at {distance_nm:.1f} NM",
                "details": {
                    "callsign": callsign,
                    "distance_nm": distance_nm,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "CTR",
                "direction": "SYS"
            })
            
            # Publish event
            self.event_publisher.publish_threshold_event(new_event, updated)
            self.stats["events_fired"] += 1
        
        # Update last_event_fired
        if new_event:
            if last_event:
                updated["last_event_fired"] = f"{last_event},{new_event}"
            else:
                updated["last_event_fired"] = new_event
        
        # Persist updated state to database
        updates = {
            "position": position,
            "vertical_speed_fpm": updated.get("vertical_speed_fpm"),
            "phase": phase,
        }
        
        if new_event:
            updates["last_event_fired"] = updated["last_event_fired"]
        
        await self.state_manager.update_aircraft_state(aircraft_id, updates)
        
        # Publish position update
        self.event_publisher.publish_aircraft_position_updated(updated)
        
        # Add to telemetry buffer
        self.add_telemetry_snapshot(updated)
    
    def determine_phase(self, distance_nm: float, altitude_agl: float) -> str:
        """
        Determine flight phase based on distance and altitude.
        
        Args:
            distance_nm: Distance to airport (nautical miles)
            altitude_agl: Altitude above ground (feet)
        
        Returns:
            Phase string
        """
        if altitude_agl < 500:
            return "FINAL"
        elif distance_nm < 10.0:
            return "APPROACH"
        elif distance_nm < 30.0:
            return "DESCENT"
        else:
            return "CRUISE"
    
    def add_telemetry_snapshot(self, aircraft: Dict[str, Any]):
        """
        Add aircraft snapshot to telemetry buffer.
        
        Args:
            aircraft: Aircraft data dictionary
        """
        position = aircraft.get("position", {})
        
        snapshot = {
            "tick": self.tick_count,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "id": aircraft.get("id"),
            "callsign": aircraft.get("callsign"),
            "lat": position.get("lat"),
            "lon": position.get("lon"),
            "altitude_ft": position.get("altitude_ft"),
            "speed_kts": position.get("speed_kts"),
            "heading": position.get("heading"),
            "vertical_speed_fpm": aircraft.get("vertical_speed_fpm"),
            "distance_to_airport_nm": aircraft.get("distance_to_airport_nm"),
            "controller": aircraft.get("controller"),
            "phase": aircraft.get("phase"),
        }
        
        self.telemetry_buffer.append(snapshot)
        
        # Flush buffer periodically
        if len(self.telemetry_buffer) >= 100:
            asyncio.create_task(self.flush_telemetry())
    
    async def flush_telemetry(self):
        """Write telemetry buffer to disk."""
        if not self.telemetry_buffer:
            return
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.telemetry_dir}/engine_{timestamp}.jsonl"
        
        try:
            with open(filename, 'a') as f:
                for snapshot in self.telemetry_buffer:
                    f.write(json.dumps(snapshot) + "\n")
            
            self.telemetry_buffer.clear()
        
        except Exception as e:
            print(f"⚠️  Failed to write telemetry: {e}")
    
    def print_statistics(self):
        """Print engine statistics."""
        runtime = time.time() - self.start_time if self.start_time else 0
        
        print("\n📊 Engine Statistics:")
        print(f"   Runtime: {runtime:.1f}s ({runtime/60:.1f}m)")
        print(f"   Total ticks: {self.stats['total_ticks']}")
        print(f"   Aircraft processed: {self.stats['aircraft_processed']}")
        print(f"   Events fired: {self.stats['events_fired']}")
        print(f"   Avg tick duration: {self.stats['avg_tick_duration']*1000:.2f}ms")
    
    async def run(self, duration_seconds: int = 0):
        """
        Run the main engine loop.
        
        Args:
            duration_seconds: Run for specified duration (0 = infinite)
        """
        await self.initialize()
        
        # Start spawn listener in background
        listener_task = self.spawn_listener.start_background_task()
        
        self.running = True
        self.start_time = time.time()
        
        print(f"\n🏁 Starting engine tick loop (1 Hz, Δt={DT}s)")
        if duration_seconds > 0:
            print(f"   Running for {duration_seconds}s")
        else:
            print(f"   Running indefinitely (Ctrl+C to stop)")
        print()
        
        try:
            target_interval = DT
            
            while self.running:
                self.tick_count += 1
                tick_start = time.time()
                
                # Execute tick
                await self.tick()
                
                # Drift compensation
                elapsed = time.time() - tick_start
                sleep_time = max(0, target_interval - elapsed)
                
                await asyncio.sleep(sleep_time)
                
                # Check duration limit
                if duration_seconds > 0 and (time.time() - self.start_time) >= duration_seconds:
                    print(f"\n⏱️  Reached duration limit ({duration_seconds}s)")
                    break
        
        except KeyboardInterrupt:
            print("\n\n⌨️  Keyboard interrupt received")
        
        finally:
            # Cancel listener task
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
            
            await self.shutdown()


async def main():
    """Main entry point for the kinematics engine."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ATC Kinematics Engine - Phase 1")
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Run duration in seconds (0 = infinite)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run 60-second test simulation",
    )
    
    args = parser.parse_args()
    
    duration = 60 if args.test else args.duration
    
    engine = KinematicsEngine()
    await engine.run(duration_seconds=duration)


if __name__ == "__main__":
    asyncio.run(main())

