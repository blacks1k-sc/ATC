"""
Quick validation test for refactored KinematicsEngine.
Tests that the async workers and batching system work correctly.
"""

import asyncio
import sys
from engine.config import config
from engine.state_manager import StateManager
from engine.event_publisher import EventPublisher


async def test_state_manager_batch():
    """Test StateManager batch operations."""
    print("Testing StateManager batch operations...")
    
    state_manager = StateManager()
    
    try:
        await state_manager.connect()
        
        # Test batch update (will fail if no aircraft exist, which is OK for syntax test)
        updates = [
            {
                "aircraft_id": 1,
                "position": {"lat": 43.0, "lon": -79.0, "altitude_ft": 10000, "speed_kts": 250, "heading": 180},
                "phase": "CRUISE",
                "distance_to_airport_nm": 50.0
            }
        ]
        
        count = await state_manager.batch_update_aircraft_states(updates)
        print(f"   Batch update executed (updated {count} aircraft)")
        
        # Test batch event creation
        events = [
            {
                "level": "INFO",
                "type": "test.event",
                "message": "Test event",
                "details": {"test": True},
                "sector": "TEST",
                "direction": "SYS"
            }
        ]
        
        count = await state_manager.batch_create_events(events)
        print(f"   Batch event creation executed (created {count} events)")
        
        await state_manager.disconnect()
        print("   StateManager tests passed")
        return True
        
    except Exception as e:
        print(f"   StateManager test failed: {e}")
        await state_manager.disconnect()
        return False


async def test_event_publisher():
    """Test EventPublisher async operations."""
    print("\nTesting EventPublisher async operations...")
    
    event_publisher = EventPublisher()
    
    try:
        await event_publisher.connect()
        
        # Test single event publish
        result = await event_publisher.publish_event("test.event", {"test": True})
        print(f"   Single event publish: {result}")
        
        # Test batch event publish
        events = [
            ("test.event1", {"test": 1}),
            ("test.event2", {"test": 2}),
        ]
        count = await event_publisher.batch_publish_events(events)
        print(f"   Batch event publish executed ({count} events)")
        
        # Test event preparation (non-blocking)
        aircraft = {
            "id": 1,
            "callsign": "TEST123",
            "icao24": "ABC123",
            "position": {"lat": 43.0, "lon": -79.0, "altitude_ft": 10000, "speed_kts": 250, "heading": 180},
            "controller": "ENGINE",
            "phase": "CRUISE",
            "vertical_speed_fpm": -500,
            "distance_to_airport_nm": 50.0
        }
        
        event = event_publisher.prepare_aircraft_position_event(aircraft)
        print(f"   Event preparation (non-blocking): {event[0]}")
        
        await event_publisher.disconnect()
        print("   EventPublisher tests passed")
        return True
        
    except Exception as e:
        print(f"   EventPublisher test failed: {e}")
        await event_publisher.disconnect()
        return False


async def test_config():
    """Test configuration."""
    print("\nTesting Configuration...")
    
    try:
        print(f"   Mode: {'DEV' if config.DEV_MODE else 'PROD'}")
        print(f"   DB Batch Interval: {config.DB_BATCH_INTERVAL_SEC}s")
        print(f"   Redis Batch Interval: {config.REDIS_BATCH_INTERVAL_SEC}s")
        print(f"   Telemetry Interval: {config.TELEMETRY_INTERVAL_SEC}s")
        print(f"   Queue Max Size: {config.IO_QUEUE_MAX_SIZE}")
        print("   Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"   Configuration test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("KinematicsEngine Refactor Validation Tests")
    print("=" * 60)
    
    results = []
    
    # Test configuration
    results.append(await test_config())
    
    # Test StateManager
    results.append(await test_state_manager_batch())
    
    # Test EventPublisher
    results.append(await test_event_publisher())
    
    print("\n" + "=" * 60)
    if all(results):
        print("All tests passed! Refactor validation successful.")
        print("=" * 60)
        return 0
    else:
        print("Some tests failed. Review errors above.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

