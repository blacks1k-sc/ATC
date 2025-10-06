# Phase A - Kinematics Engine Architecture

## Overview

The Kinematics Engine is a deterministic 1 Hz simulation service that autonomously controls arrival aircraft from generation until ATC takeover. It implements realistic physics-based motion using aviation formulas and emits real-time events via Redis pub/sub.

## System Architecture

```
┌─────────────────┐
│  Next.js API    │
│ (aircraft gen)  │
└────────┬────────┘
         │
         ├─────────────┐
         │             │
         ▼             ▼
   ┌──────────┐   ┌──────────┐
   │PostgreSQL│   │  Redis   │
   │   (DB)   │   │ (Events) │
   └────┬─────┘   └─────┬────┘
        │               │
        └───┬───────────┘
            │
      ┌─────▼──────────┐
      │  Python Engine │
      │  (atc-brain)   │
      └────────────────┘
```

## Component Diagram

```
engine/
 ├── core_engine.py ──────► Main orchestrator
 │   ├── StateManager ────► Database queries
 │   ├── EventPublisher ──► Redis publishing
 │   ├── SpawnListener ───► Redis subscribing
 │   └── Kinematics ──────► Physics formulas
 │
 ├── kinematics.py ───────► Motion calculations
 │   ├── update_speed()
 │   ├── update_heading()
 │   ├── update_altitude()
 │   └── update_position()
 │
 ├── geo_utils.py ────────► Geographic calculations
 │   ├── distance_to_airport()
 │   ├── update_position()
 │   └── bearing_to_point()
 │
 ├── state_manager.py ────► Database integration
 │   ├── get_active_arrivals()
 │   ├── update_aircraft_state()
 │   └── mark_touchdown()
 │
 ├── event_publisher.py ──► Redis event emission
 │   ├── publish_aircraft_position_updated()
 │   ├── publish_threshold_event()
 │   └── publish_state_snapshot()
 │
 ├── spawn_listener.py ───► New aircraft detection
 │   └── listen for aircraft.created
 │
 ├── airport_data.py ─────► Airport reference data
 │   ├── coordinates
 │   ├── runways
 │   └── entry waypoints
 │
 └── constants.py ────────► Physical constants
     ├── acceleration limits
     ├── bank angle limits
     └── vertical speed limits
```

## Data Flow

### 1. Aircraft Spawn Flow

```
User clicks "ADD AIRCRAFT"
         │
         ▼
Next.js API generates aircraft
 (with flight_type=ARRIVAL)
         │
         ├────────────────┐
         │                │
         ▼                ▼
   PostgreSQL       Redis Publish
(aircraft_instances)  (aircraft.created)
         │                │
         │                ▼
         │     SpawnListener detects
         │     arrival and marks
         │     controller='ENGINE'
         │                │
         └────────────────┘
                  │
                  ▼
       Aircraft now controlled
           by ENGINE
```

### 2. Engine Tick Flow (1 Hz)

```
Every 1 second:
  │
  ├─► StateManager.get_active_arrivals()
  │   (controller='ENGINE' AND flight_type='ARRIVAL')
  │
  ├─► For each aircraft:
  │   │
  │   ├─► Apply kinematics formulas
  │   │   ├── update_speed()
  │   │   ├── update_heading()
  │   │   ├── update_altitude()
  │   │   └── update_position()
  │   │
  │   ├─► Calculate distance_to_airport()
  │   │
  │   ├─► Check threshold events:
  │   │   ├── ≤ 30 NM → ENTERED_ENTRY_ZONE
  │   │   ├── ≤ 20 NM → HANDOFF_READY
  │   │   └── < 50 ft AGL → TOUCHDOWN
  │   │
  │   ├─► StateManager.update_aircraft_state()
  │   │   (persist to PostgreSQL)
  │   │
  │   ├─► EventPublisher.publish_aircraft_position_updated()
  │   │   (emit to Redis)
  │   │
  │   └─► Add to telemetry buffer
  │
  └─► Flush telemetry every 100 snapshots
```

### 3. Event Flow

```
Engine updates aircraft
         │
         ▼
EventPublisher publishes to Redis
  channel: "atc:events"
         │
         ├────────────────────────┐
         │                        │
         ▼                        ▼
  Next.js EventBus         Other subscribers
  (SSE to clients)         (future ATCs)
         │
         ▼
   UI updates in
   real-time
```

## Database Schema Extensions

### Added Fields to `aircraft_instances`

```sql
controller VARCHAR(20) DEFAULT 'ENGINE'
  -- Who controls the aircraft (ENGINE, ENTRY_ATC, etc.)

target_speed_kts FLOAT
  -- Target speed for tracking

target_heading_deg FLOAT
  -- Target heading for turns

target_altitude_ft FLOAT
  -- Target altitude for climb/descent

vertical_speed_fpm FLOAT DEFAULT 0
  -- Current vertical speed (feet per minute)

flight_type VARCHAR(10)
  -- ARRIVAL or DEPARTURE

phase VARCHAR(20)
  -- Current flight phase (CRUISE, DESCENT, APPROACH, FINAL)

last_event_fired VARCHAR(50)
  -- Comma-separated list of fired events
```

## Redis Event Types

### Published by Engine

1. **aircraft.position_updated**
   - Published every tick for each aircraft
   - Contains full aircraft state + position

2. **aircraft.threshold_event**
   - Published when crossing distance thresholds
   - Event types: ENTERED_ENTRY_ZONE, HANDOFF_READY, TOUCHDOWN

3. **engine.state_snapshot**
   - Published every 10 ticks
   - Contains all active aircraft summaries

4. **system.status**
   - Published on engine start/stop
   - Contains engine health and statistics

### Subscribed by Engine

1. **aircraft.created**
   - Listens for new aircraft generation
   - Filters for flight_type=ARRIVAL
   - Marks for ENGINE control

## Performance Characteristics

- **Tick Rate**: 1 Hz (1 tick per second)
- **Tick Latency**: < 100ms typical, < 200ms warning threshold
- **Aircraft Capacity**: Up to 100 active aircraft per tick
- **Database Queries**: 1 read + N writes per tick (N = active aircraft)
- **Redis Publications**: N+1 per tick (N positions + 1 snapshot every 10 ticks)
- **Memory Usage**: ~10 MB + (1 KB × active aircraft)

## Error Handling

### Database Errors
- Automatic retry with exponential backoff
- Graceful degradation: skip aircraft if update fails
- Continue processing other aircraft

### Redis Errors
- Non-blocking: engine continues if Redis unavailable
- Events not published but logged locally
- Reconnection attempts every 5 seconds

### Aircraft State Errors
- Validation before applying formulas
- Skip aircraft with invalid data
- Log error and continue to next aircraft

## Telemetry and Logging

### Telemetry Files
- **Location**: `telemetry/phaseA/`
- **Format**: JSON Lines (.jsonl)
- **Naming**: `engine_YYYYMMDD_HHMMSS.jsonl`
- **Buffer Size**: 100 snapshots before flush
- **Fields**: tick, timestamp, id, callsign, lat, lon, altitude, speed, heading, vs, distance, controller, phase

### Logging
- **Console**: Real-time engine status and events
- **Level**: INFO for normal, WARN for delays, ERROR for failures
- **Statistics**: Printed on shutdown

## Security Considerations

- **Database**: Uses connection pooling with password authentication
- **Redis**: Optional password authentication
- **Environment Variables**: All credentials in .env file
- **No Exposed Ports**: Engine operates as background service

## Future Extensions (Phase 2+)

1. **ATC Takeover**: Entry ATC can request control via API endpoint
2. **Target Commands**: ATCs set target_speed, target_heading, target_altitude
3. **Conflict Detection**: Check for aircraft proximity and separation
4. **Departure Support**: Extend to control departures (ignored in Phase 1)
5. **Weather Integration**: Apply wind vectors to ground speed/track
6. **Performance Models**: Aircraft-specific performance envelopes

## Dependencies

- **Python**: 3.11+
- **asyncpg**: PostgreSQL async driver
- **redis**: Redis client for pub/sub
- **python-dotenv**: Environment configuration

## Configuration

All configuration via environment variables in `.env`:

- Database: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
- Redis: REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
- Engine: ENGINE_TICK_RATE, TELEMETRY_DIR
- Airport: AIRPORT_ICAO, AIRPORT_DATA_PATH

## Testing Strategy

1. **Unit Tests**: kinematics formulas, geographic calculations
2. **Integration Tests**: database operations, Redis pub/sub
3. **Acceptance Tests**: 60-second simulation with validation
4. **Deterministic Replay**: Same random seed produces identical results

## Monitoring and Observability

- **Statistics**: aircraft_processed, events_fired, avg_tick_duration
- **Real-time Console**: Aircraft events as they happen
- **Telemetry Files**: Permanent record for analysis
- **Health Checks**: Database and Redis connection status

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-05  
**Author**: ATC System Team

