# Phase A - Data Contracts and Event Schemas

## Database Schemas

### Aircraft Instance (Extended)

```typescript
interface AircraftInstance {
  // Existing fields
  id: number;
  icao24: string;                // 6-char hex identifier
  registration: string;          // Aircraft registration
  callsign: string;              // Flight callsign
  aircraft_type_id: number;      // FK to aircraft_types
  airline_id: number;            // FK to airlines
  status: string;                // 'active' | 'landed' | 'departed'
  squawk_code: string;           // 4-digit transponder code
  created_at: timestamp;
  updated_at: timestamp;
  
  // Position (JSONB)
  position: {
    lat: number;                 // degrees
    lon: number;                 // degrees
    altitude_ft: number;         // feet MSL
    speed_kts: number;           // knots (ground speed)
    heading: number;             // degrees (0-360)
  };
  
  // Flight Plan (JSONB)
  flight_plan: {
    type: 'ARRIVAL' | 'DEPARTURE';
    origin: string;              // ICAO code
    destination: string;         // ICAO code
    entry_waypoint?: string;     // for arrivals
    runway: string;              // e.g., "05L"
    sid?: string;                // for departures
  };
  
  // NEW: Engine Control Fields
  controller: string;            // 'ENGINE' | 'ENTRY_ATC' | 'TOWER' | ...
  target_speed_kts: number | null;
  target_heading_deg: number | null;
  target_altitude_ft: number | null;
  vertical_speed_fpm: number;    // current vertical speed
  flight_type: 'ARRIVAL' | 'DEPARTURE';
  phase: string;                 // 'CRUISE' | 'DESCENT' | 'APPROACH' | 'FINAL' | 'TOUCHDOWN'
  last_event_fired: string;      // comma-separated event names
}
```

## Redis Event Schemas

All events published to channel: `atc:events`

### Event Wrapper

```typescript
interface EventBusMessage {
  type: string;                  // event type identifier
  timestamp: string;             // ISO 8601 UTC timestamp
  data: any;                     // event-specific payload
}
```

### 1. aircraft.created

**Published by**: Next.js API  
**Subscribed by**: Engine SpawnListener

```typescript
{
  type: "aircraft.created",
  timestamp: "2025-10-05T12:00:00.000Z",
  data: {
    aircraft: {
      id: 123,
      icao24: "A1B2C3",
      callsign: "ACA217",
      registration: "ACA2170",
      aircraft_type_id: 45,
      airline_id: 12,
      position: {
        lat: 43.85,
        lon: -79.80,
        altitude_ft: 18000,
        speed_kts: 280,
        heading: 230
      },
      flight_type: "ARRIVAL",
      flight_plan: {
        type: "ARRIVAL",
        origin: "KJFK",
        destination: "CYYZ",
        entry_waypoint: "LINNG",
        runway: "23L"
      },
      status: "active",
      squawk_code: "1234",
      created_at: "2025-10-05T12:00:00.000Z"
    }
  }
}
```

### 2. aircraft.position_updated

**Published by**: Engine EventPublisher  
**Subscribed by**: Next.js SSE clients

```typescript
{
  type: "aircraft.position_updated",
  timestamp: "2025-10-05T12:00:01.000Z",
  data: {
    aircraft: {
      id: 123,
      icao24: "A1B2C3",
      callsign: "ACA217",
      registration: "ACA2170",
      position: {
        lat: 43.8498,
        lon: -79.7998,
        altitude_ft: 17950,
        speed_kts: 279,
        heading: 230
      },
      controller: "ENGINE",
      phase: "DESCENT",
      vertical_speed_fpm: -500,
      distance_to_airport_nm: 42.1
    },
    position: {
      lat: 43.8498,
      lon: -79.7998,
      altitude_ft: 17950,
      speed_kts: 279,
      heading: 230
    }
  }
}
```

### 3. aircraft.threshold_event

**Published by**: Engine EventPublisher  
**Subscribed by**: Next.js SSE clients, Future ATCs

```typescript
{
  type: "aircraft.threshold_event",
  timestamp: "2025-10-05T12:05:00.000Z",
  data: {
    event_type: "ENTERED_ENTRY_ZONE" | "HANDOFF_READY" | "TOUCHDOWN",
    aircraft: {
      id: 123,
      icao24: "A1B2C3",
      callsign: "ACA217",
      lat: 43.75,
      lon: -79.70,
      altitude_ft: 12000,
      speed_kts: 250,
      heading: 230,
      controller: "ENGINE",
      phase: "DESCENT",
      distance_to_airport_nm: 29.8
    }
  }
}
```

### 4. engine.state_snapshot

**Published by**: Engine EventPublisher (every 10 ticks)  
**Subscribed by**: Monitoring systems, telemetry collectors

```typescript
{
  type: "engine.state_snapshot",
  timestamp: "2025-10-05T12:00:10.000Z",
  data: {
    tick: 10,
    timestamp: "2025-10-05T12:00:10.000Z",
    aircraft_count: 5,
    aircraft: [
      {
        id: 123,
        callsign: "ACA217",
        position: { lat: 43.85, lon: -79.80, altitude_ft: 17500, ... },
        controller: "ENGINE",
        phase: "DESCENT",
        distance_to_airport_nm: 38.5
      },
      // ... more aircraft
    ]
  }
}
```

### 5. system.status

**Published by**: Engine on start/stop  
**Subscribed by**: Monitoring systems

```typescript
{
  type: "system.status",
  timestamp: "2025-10-05T12:00:00.000Z",
  data: {
    status: {
      state: "running" | "stopped" | "error",
      engine_version: "1.0.0",
      tick_count: 0,
      aircraft_count: 0,
      uptime_seconds: 0,
      avg_tick_duration_ms: 0
    }
  }
}
```

## Telemetry File Format

**Format**: JSON Lines (.jsonl)  
**Location**: `telemetry/phaseA/engine_YYYYMMDD_HHMMSS.jsonl`

Each line is a complete JSON object:

```json
{"tick":1,"timestamp":"2025-10-05T12:00:01.000Z","id":123,"callsign":"ACA217","lat":43.85,"lon":-79.80,"altitude_ft":17950,"speed_kts":279,"heading":230,"vertical_speed_fpm":-500,"distance_to_airport_nm":42.1,"controller":"ENGINE","phase":"DESCENT"}
{"tick":2,"timestamp":"2025-10-05T12:00:02.000Z","id":123,"callsign":"ACA217","lat":43.8498,"lon":-79.7998,"altitude_ft":17942,"speed_kts":278,"heading":230,"vertical_speed_fpm":-508,"distance_to_airport_nm":42.0,"controller":"ENGINE","phase":"DESCENT"}
...
```

## API Contracts (Future)

### Engine Control API (Phase 2)

```http
POST /api/engine/set-target
Content-Type: application/json

{
  "aircraft_id": 123,
  "controller": "ENTRY_ATC",  // request control transfer
  "target_speed_kts": 250,
  "target_heading_deg": 180,
  "target_altitude_ft": 10000
}

Response:
{
  "success": true,
  "message": "Targets set for ACA217",
  "aircraft_id": 123,
  "controller": "ENTRY_ATC"
}
```

```http
GET /api/engine/status

Response:
{
  "state": "running",
  "tick_count": 12450,
  "uptime_seconds": 12450,
  "active_aircraft": 7,
  "aircraft_by_controller": {
    "ENGINE": 5,
    "ENTRY_ATC": 2
  },
  "avg_tick_duration_ms": 45,
  "events_fired": 134
}
```

## Event Deduplication Rules

Events fire only once per aircraft based on `last_event_fired` field:

```python
# Example logic
if "ENTERED_ENTRY_ZONE" not in aircraft.last_event_fired:
    if distance <= 30.0:
        fire_event("ENTERED_ENTRY_ZONE")
        aircraft.last_event_fired += ",ENTERED_ENTRY_ZONE"
```

## Validation Rules

### Aircraft Position
- `lat`: -90 to 90
- `lon`: -180 to 180
- `altitude_ft`: 0 to 60000
- `speed_kts`: 0 to 600
- `heading`: 0 to 360

### Speed Changes
- Acceleration: ≤ 0.6 kt/s
- Deceleration: ≤ 0.8 kt/s

### Heading Changes
- Turn rate: ≤ g·tan(25°)/V_m rad/s
- Must take shortest path (e.g., 350° → 10° turns right through 0°)

### Altitude Changes
- Climb: ≤ 2500 fpm (cruise) or 1800 fpm (approach)
- Descent: ≤ 3000 fpm (cruise) or 1800 fpm (approach)

### Distance Thresholds
- ENTERED_ENTRY_ZONE: ≤ 30 NM
- HANDOFF_READY: ≤ 20 NM
- TOUCHDOWN: altitude < 50 ft AGL

## Error Codes

### Database Errors
- `DB_CONNECTION_FAILED`: Cannot connect to PostgreSQL
- `DB_QUERY_FAILED`: Query execution failed
- `DB_AIRCRAFT_NOT_FOUND`: Aircraft ID not in database

### Redis Errors
- `REDIS_CONNECTION_FAILED`: Cannot connect to Redis
- `REDIS_PUBLISH_FAILED`: Event publication failed

### Validation Errors
- `INVALID_POSITION`: Position outside valid range
- `INVALID_SPEED`: Speed outside valid range
- `INVALID_HEADING`: Heading outside 0-360

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-05  
**Status**: Phase A - Arrivals Only

