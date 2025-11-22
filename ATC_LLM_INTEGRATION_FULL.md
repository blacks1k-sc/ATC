# ATC LLM Integration - Complete Production System Design

## Executive Summary

This document provides a complete, production-ready system design for integrating Large Language Model (LLM) controllers into the ATC system to manage airspace and ground operations. The architecture extends the existing KinematicsEngine (1 Hz deterministic physics) with two specialized LLM controllers: **Air LLM** (manages airborne aircraft through all phases) and **Ground LLM** (manages surface movements, gates, taxi routing, and runway crossings).

The system maintains PostgreSQL as the single source of truth, uses an event bus (Redis/NATS) for real-time coordination, and ensures LLM decisions are validated, structured, and executed by the deterministic engine.

---

## 1. Overall System Architecture

### 1.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ATC SYSTEM ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐         ┌──────────────┐        ┌──────────────┐   │
│  │   Air LLM    │         │ Ground LLM   │        │  Kinematics  │   │
│  │  Controller  │◄───────►│  Controller  │◄──────►│   Engine     │   │
│  │              │         │              │        │  (1 Hz Tick) │   │
│  └──────┬───────┘         └──────┬───────┘        └──────┬───────┘   │
│         │                        │                       │           │
│         │ Structured JSON        │ Structured JSON       │ Physics   │
│         │ Instructions           │ Instructions          │ Execution │
│         │                        │                       │           │
│         └────────┬───────────────┴──────────────┬────────┘           │
│                  │                              │                     │
│         ┌────────▼──────────────────────────────▼──────────┐         │
│         │          PostgreSQL Database                     │         │
│         │  (Single Source of Truth)                        │         │
│         │  • flights (aircraft_instances)                  │         │
│         │  • runway_ops                                    │         │
│         │  • clearances                                    │         │
│         │  • gates                                         │         │
│         │  • taxiway_graph                                 │         │
│         │  • events                                        │         │
│         └────────┬──────────────────────────────────────────┘         │
│                  │                                                    │
│         ┌────────▼──────────────────────────────────────────┐        │
│         │         Event Bus (Redis/NATS)                    │        │
│         │  • aircraft.position_updated                      │        │
│         │  • clearance.completed                            │        │
│         │  • zone.boundary_crossed                          │        │
│         │  • conflict.detected                              │        │
│         │  • runway.landed                                  │        │
│         │  • runway.vacated                                 │        │
│         │  • pushback.initiated                             │        │
│         │  • llm.decision_issued                            │        │
│         └────────┬──────────────────────────────────────────┘        │
│                  │                                                    │
│         ┌────────▼──────────────────────────────────────────┐        │
│         │      Static Airport Data                          │        │
│         │  • Waypoint catalog (STAR, SID, fixes)            │        │
│         │  • Runway configurations                          │        │
│         │  • Sector boundaries (lat/lon/alt)                │        │
│         │  • Gate compatibility rules                       │        │
│         │  • Taxiway routing graph                          │        │
│         └───────────────────────────────────────────────────┘        │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

#### **Kinematics Engine (1 Hz Tick)**
- Executes deterministic physics simulation for all aircraft
- Applies LLM-issued clearances (speed, heading, altitude, waypoints)
- Detects clearance completion conditions
- Emits events for zone boundaries, conflicts, landing, runway vacate, pushback
- Maintains aircraft state in PostgreSQL
- Publishes position updates to event bus every tick

#### **Air LLM Controller**
- Monitors airborne aircraft (phases: CRUISE, DESCENT, APPROACH, FINAL)
- Issues structured JSON instructions for:
  - STAR selection and waypoint sequencing
  - Vectoring (heading/speed assignments)
  - Descent profile management
  - Runway assignment
  - Landing clearance
  - Missed approach handling
- Subscribes to zone boundary events, conflict events, clearance completion events
- Syncs with Ground LLM for landing/takeoff coordination

#### **Ground LLM Controller**
- Manages surface operations (TAXI, GATE, PUSHBACK phases)
- Issues structured JSON instructions for:
  - Gate assignment (arrivals and departures)
  - Taxi routing (path through taxiway graph)
  - Runway-crossing approval
  - Pushback sequencing
- Subscribes to landing events, runway vacate events, pushback events
- Syncs with Air LLM for handoffs

#### **PostgreSQL Database**
- **Single source of truth** for all operational state
- Stores: flights, runway_ops, clearances, gates, taxiway_graph, events
- All LLM decisions are persisted as clearances before execution
- Engine writes state snapshots every tick

#### **Event Bus (Redis/NATS)**
- Real-time pub/sub for event-driven coordination
- LLM controllers subscribe to relevant events
- Engine publishes position updates, clearance completion, zone crossings
- Enables asynchronous, decoupled communication

#### **Static Airport Data**
- Read-only reference data (waypoints, runways, gates, taxiways)
- Loaded at startup, periodically refreshed
- Used by LLMs for decision context

---

## 2. LLM Decision Triggers

LLM controllers are **event-driven** and issue decisions when specific conditions occur. The engine detects these conditions and publishes events to the event bus.

### 2.1 Zone Boundary Crossings

**Event**: `zone.boundary_crossed`

**Trigger Conditions**:
- Aircraft enters/exits defined airspace zones (ENTRY, ENROUTE, APPROACH, RUNWAY)
- Zone boundaries defined by distance from airport, altitude bands, and lat/lon sectors

**Example**:
```json
{
  "type": "zone.boundary_crossed",
  "timestamp": "2024-01-15T14:23:45Z",
  "data": {
    "aircraft_id": 12345,
    "callsign": "ACA217",
    "from_zone": "ENROUTE",
    "to_zone": "APPROACH",
    "distance_nm": 9.8,
    "altitude_ft": 8500,
    "position": {"lat": 43.7234, "lon": -79.5891}
  }
}
```

**LLM Response**: Air LLM evaluates new zone context and issues clearance (e.g., transition to approach procedures, assign final approach course).

### 2.2 Clearance Completion

**Event**: `clearance.completed`

**Trigger Conditions**:
- Aircraft reaches target altitude within threshold (±100 ft)
- Aircraft reaches target heading within threshold (±5 degrees)
- Aircraft reaches target speed within threshold (±5 kts)
- Aircraft passes designated waypoint
- Aircraft completes descent to assigned altitude

**Example**:
```json
{
  "type": "clearance.completed",
  "timestamp": "2024-01-15T14:23:50Z",
  "data": {
    "aircraft_id": 12345,
    "callsign": "ACA217",
    "clearance_id": 789,
    "clearance_type": "DESCENT",
    "completed_item": "altitude",
    "target_altitude_ft": 5000,
    "actual_altitude_ft": 5010
  }
}
```

**LLM Response**: Air LLM issues next clearance in sequence (e.g., continue descent, intercept final approach course).

### 2.3 Conflict Detection

**Event**: `conflict.detected`

**Trigger Conditions**:
- Two aircraft projected to violate separation minima (horizontal < 5 NM, vertical < 1000 ft below FL290)
- Conflict prediction horizon: 2 minutes
- Wake turbulence separation violation

**Example**:
```json
{
  "type": "conflict.detected",
  "timestamp": "2024-01-15T14:23:55Z",
  "data": {
    "aircraft_id_1": 12345,
    "aircraft_id_2": 12346,
    "callsign_1": "ACA217",
    "callsign_2": "ACA318",
    "conflict_type": "horizontal",
    "projected_time_sec": 120,
    "min_separation_nm": 4.2,
    "required_separation_nm": 5.0
  }
}
```

**LLM Response**: Air LLM issues vectoring or altitude change to resolve conflict (e.g., "ACA217, turn right heading 090, descend and maintain 4000").

### 2.4 Landing Events

**Event**: `runway.landed`

**Trigger Conditions**:
- Aircraft altitude AGL < 50 ft AND position within runway threshold boundaries
- Engine detects touchdown based on altitude and runway geometry

**Example**:
```json
{
  "type": "runway.landed",
  "timestamp": "2024-01-15T14:24:00Z",
  "data": {
    "aircraft_id": 12345,
    "callsign": "ACA217",
    "runway": "05L",
    "position": {"lat": 43.6777, "lon": -79.6248},
    "touchdown_speed_kts": 145,
    "landing_rollout_ft": 0
  }
}
```

**LLM Response**: 
- Air LLM completes arrival sequence, marks aircraft as landed
- Ground LLM takes control, issues taxi clearance to gate

### 2.5 Runway Vacate Events

**Event**: `runway.vacated`

**Trigger Conditions**:
- Aircraft on ground exits runway geometry (position outside runway polygon)
- Detected by taxiway intersection or position change

**Example**:
```json
{
  "type": "runway.vacated",
  "timestamp": "2024-01-15T14:24:15Z",
  "data": {
    "aircraft_id": 12345,
    "callsign": "ACA217",
    "runway": "05L",
    "vacate_taxiway": "A1",
    "position": {"lat": 43.6780, "lon": -79.6250}
  }
}
```

**LLM Response**: Ground LLM issues full taxi clearance to assigned gate.

### 2.6 Pushback Events

**Event**: `pushback.initiated`

**Trigger Conditions**:
- Departure aircraft requests pushback (manual trigger or scheduled)
- Gate assigned, flight plan loaded, departure clearance issued

**Example**:
```json
{
  "type": "pushback.initiated",
  "timestamp": "2024-01-15T14:24:30Z",
  "data": {
    "aircraft_id": 12347,
    "callsign": "ACA501",
    "gate": "C32",
    "runway": "05R",
    "scheduled_departure": "2024-01-15T14:30:00Z"
  }
}
```

**LLM Response**: Ground LLM sequences pushback, issues initial taxi clearance, coordinates with Air LLM for departure slot.

### 2.7 Scheduled Events

**Events**: `scheduled.clearance_review`, `scheduled.flow_management`

**Trigger Conditions**:
- Periodic review (every 30 seconds): LLM re-evaluates all aircraft under its control
- Flow management: Adjust sequencing for runway capacity

**LLM Response**: LLM issues proactive clearances to optimize traffic flow, maintain separation, and meet scheduled times.

---

## 3. Air LLM Output: Structured JSON Instructions

The Air LLM outputs **strictly structured JSON** conforming to a defined schema. This ensures deterministic parsing and validation by the engine.

### 3.1 Clearance Schema

```json
{
  "clearance_type": "STAR_ASSIGNMENT" | "WAYPOINT_SEQUENCE" | "VECTORING" | "DESCENT_PROFILE" | 
                    "SPEED_ASSIGNMENT" | "RUNWAY_ASSIGNMENT" | "LANDING_CLEARANCE" | "MISSED_APPROACH",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "issued_at": "2024-01-15T14:23:45Z",
  "valid_until": "2024-01-15T14:28:45Z",
  "instructions": {
    // Type-specific fields (see below)
  },
  "priority": "NORMAL" | "URGENT" | "EXPEDITE",
  "reason": "Standard approach sequencing",
  "confidence": 0.95
}
```

### 3.2 STAR Selection

**Clearance Type**: `STAR_ASSIGNMENT`

```json
{
  "clearance_type": "STAR_ASSIGNMENT",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "issued_at": "2024-01-15T14:23:45Z",
  "instructions": {
    "star_name": "BOTTO",
    "entry_fix": "BOTTO",
    "transition": "BOTTO5",
    "runway": "05L",
    "initial_altitude_ft": 17000,
    "initial_speed_kts": 250,
    "waypoints": [
      {"name": "BOTTO", "altitude_ft": 17000, "speed_kts": 250},
      {"name": "VEVOD", "altitude_ft": 12000, "speed_kts": 220},
      {"name": "BAYYS", "altitude_ft": 5000, "speed_kts": 180}
    ]
  }
}
```

### 3.3 Waypoint Sequencing

**Clearance Type**: `WAYPOINT_SEQUENCE`

```json
{
  "clearance_type": "WAYPOINT_SEQUENCE",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "waypoints": [
      {"name": "BAYYS", "altitude_ft": 5000, "speed_kts": 180, "constraint": "AT_OR_ABOVE"},
      {"name": "DAVYS", "altitude_ft": 3000, "speed_kts": 160, "constraint": "AT_OR_ABOVE"},
      {"name": "FINAL", "altitude_ft": 2000, "speed_kts": 150, "constraint": "AT"}
    ],
    "maintain_separation": true
  }
}
```

### 3.4 Vectoring

**Clearance Type**: `VECTORING`

```json
{
  "clearance_type": "VECTORING",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "heading_deg": 090,
    "reason": "conflict_resolution",
    "intercept_waypoint": "DAVYS",
    "maintain_heading_until": "waypoint"
  }
}
```

### 3.5 Descent Profile

**Clearance Type**: `DESCENT_PROFILE`

```json
{
  "clearance_type": "DESCENT_PROFILE",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "target_altitude_ft": 5000,
    "vertical_speed_fpm": -1500,
    "descend_via": "STAR",
    "cross_fix": "BAYYS",
    "cross_altitude_ft": 5000,
    "maintain_until": "waypoint"
  }
}
```

### 3.6 Speed Assignment

**Clearance Type**: `SPEED_ASSIGNMENT`

```json
{
  "clearance_type": "SPEED_ASSIGNMENT",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "target_speed_kts": 180,
    "maintain_until": "waypoint",
    "waypoint": "BAYYS",
    "reason": "approach_sequencing"
  }
}
```

### 3.7 Runway Assignment

**Clearance Type**: `RUNWAY_ASSIGNMENT`

```json
{
  "clearance_type": "RUNWAY_ASSIGNMENT",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "runway": "05L",
    "approach_type": "ILS",
    "ils_frequency": 110.50,
    "final_approach_course": 050,
    "glideslope_angle_deg": 3.0
  }
}
```

### 3.8 Landing Clearance

**Clearance Type**: `LANDING_CLEARANCE`

```json
{
  "clearance_type": "LANDING_CLEARANCE",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "runway": "05L",
    "clearance_type": "CLEARED_TO_LAND",
    "wind": {"direction_deg": 050, "speed_kts": 12},
    "traffic_advisory": "Traffic on final, 5 miles",
    "expedite": false
  }
}
```

### 3.9 Missed Approach Handling

**Clearance Type**: `MISSED_APPROACH`

```json
{
  "clearance_type": "MISSED_APPROACH",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "climb_to_altitude_ft": 3000,
    "heading_deg": 050,
    "waypoint": "BAYYS",
    "hold_at": "BAYYS",
    "hold_entry": "DIRECT",
    "hold_altitude_ft": 3000,
    "hold_turns": "RIGHT",
    "hold_time_leg_min": 1.0,
    "expect_vectors_back": true
  }
}
```

---

## 4. Ground LLM Output: Structured JSON Instructions

The Ground LLM manages all surface operations with structured JSON clearances.

### 4.1 Gate Assignment

**Clearance Type**: `GATE_ASSIGNMENT`

```json
{
  "clearance_type": "GATE_ASSIGNMENT",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "gate": "C32",
    "assignment_reason": "airline_preference",
    "gate_type": "JET_BRIDGE",
    "terminal": "Terminal 1",
    "estimated_arrival": "2024-01-15T14:24:00Z",
    "estimated_vacate": "2024-01-15T15:45:00Z",
    "turnaround_time_min": 45
  }
}
```

### 4.2 Taxi Routing

**Clearance Type**: `TAXI_CLEARANCE`

```json
{
  "clearance_type": "TAXI_CLEARANCE",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "from": "runway_05L_vacate",
    "to": "gate_C32",
    "route": ["A1", "A", "B", "C", "C32"],
    "hold_short": [
      {"taxiway": "D", "reason": "crossing_runway_05R"},
      {"taxiway": "B", "reason": "traffic"}
    ],
    "max_speed_kts": 20,
    "follow_me_required": false
  }
}
```

### 4.3 Runway Crossing Approval

**Clearance Type**: `RUNWAY_CROSSING`

```json
{
  "clearance_type": "RUNWAY_CROSSING",
  "aircraft_id": 12345,
  "callsign": "ACA217",
  "instructions": {
    "runway": "05R",
    "crossing_taxiway": "D",
    "clearance": "CROSS_RUNWAY_05R",
    "traffic_advisory": "Departure on final, 2 miles",
    "expedite": true,
    "valid_until": "2024-01-15T14:24:30Z"
  }
}
```

### 4.4 Pushback Sequencing

**Clearance Type**: `PUSHBACK_CLEARANCE`

```json
{
  "clearance_type": "PUSHBACK_CLEARANCE",
  "aircraft_id": 12347,
  "callsign": "ACA501",
  "instructions": {
    "gate": "C32",
    "pushback_direction": "STRAIGHT",
    "tail_facing": "NORTH",
    "clearance": "PUSHBACK_APPROVED",
    "pushback_time": "2024-01-15T14:25:00Z",
    "initial_taxi_route": ["C32", "C", "B"],
    "hold_at": "B",
    "awaiting_departure_clearance": true
  }
}
```

---

## 5. Engine Execution and Clearance Completion Detection

The KinematicsEngine (1 Hz tick) applies LLM clearances and detects when clearances are completed.

### 5.1 Clearance Application

**Process**:
1. Engine queries PostgreSQL for active clearances for each aircraft
2. Applies clearance instructions to aircraft state:
   - `target_speed_kts` ← clearance speed
   - `target_heading_deg` ← clearance heading
   - `target_altitude_ft` ← clearance altitude
   - `waypoint_sequence` ← clearance waypoints
3. Kinematics module calculates motion toward targets (respects acceleration, bank angle, vertical speed limits)
4. Updates aircraft position, speed, heading, altitude

**Code Flow**:
```python
# Every tick (1 Hz)
for aircraft in active_aircraft:
    # Load active clearance from DB
    clearance = await db.get_active_clearance(aircraft_id)
    
    if clearance:
        # Apply clearance targets
        aircraft['target_speed_kts'] = clearance.instructions.target_speed_kts
        aircraft['target_heading_deg'] = clearance.instructions.heading_deg
        aircraft['target_altitude_ft'] = clearance.instructions.target_altitude_ft
        aircraft['waypoint_sequence'] = clearance.instructions.waypoints
    
    # Apply physics (toward targets)
    updated_aircraft = update_aircraft_state(aircraft, dt=1.0)
    
    # Check clearance completion
    if clearance:
        completion_status = check_clearance_completion(updated_aircraft, clearance)
        if completion_status.completed:
            # Emit event
            await event_bus.publish('clearance.completed', {
                'aircraft_id': aircraft_id,
                'clearance_id': clearance.id,
                'completed_item': completion_status.item
            })
            # Mark clearance as completed in DB
            await db.mark_clearance_completed(clearance.id)
```

### 5.2 Clearance Completion Detection

**Conditions**:

1. **Altitude Target**:
   - Within ±100 ft of target altitude AND vertical speed < 100 fpm

2. **Heading Target**:
   - Within ±5 degrees of target heading AND bank angle < 5 degrees

3. **Speed Target**:
   - Within ±5 kts of target speed AND acceleration < 0.1 kt/s

4. **Waypoint Passage**:
   - Distance to waypoint < 0.5 NM (crossed)

5. **Descent Completion**:
   - Reached target altitude AND vertical speed < 200 fpm (level flight)

**Detection Logic**:
```python
def check_clearance_completion(aircraft: dict, clearance: dict) -> CompletionStatus:
    """Check if clearance conditions are met."""
    
    if clearance['clearance_type'] == 'DESCENT_PROFILE':
        target_alt = clearance['instructions']['target_altitude_ft']
        current_alt = aircraft['position']['altitude_ft']
        vs = aircraft['vertical_speed_fpm']
        
        if abs(current_alt - target_alt) < 100 and abs(vs) < 100:
            return CompletionStatus(completed=True, item='altitude')
    
    elif clearance['clearance_type'] == 'VECTORING':
        target_hdg = clearance['instructions']['heading_deg']
        current_hdg = aircraft['position']['heading']
        bank = aircraft['bank_angle_deg']
        
        if abs(current_hdg - target_hdg) < 5 and abs(bank) < 5:
            return CompletionStatus(completed=True, item='heading')
    
    elif clearance['clearance_type'] == 'WAYPOINT_SEQUENCE':
        next_waypoint = clearance['instructions']['waypoints'][0]
        wp_lat, wp_lon = get_waypoint_position(next_waypoint['name'])
        distance_nm = calculate_distance(
            aircraft['position']['lat'], aircraft['position']['lon'],
            wp_lat, wp_lon
        )
        
        if distance_nm < 0.5:
            return CompletionStatus(completed=True, item='waypoint', waypoint=next_waypoint['name'])
    
    return CompletionStatus(completed=False)
```

### 5.3 Event Emission

**Events Published by Engine**:

1. `aircraft.position_updated` - Every tick for all active aircraft
2. `clearance.completed` - When clearance condition met
3. `zone.boundary_crossed` - When aircraft enters/exits zone
4. `conflict.detected` - When separation violation predicted
5. `runway.landed` - When touchdown detected
6. `runway.vacated` - When aircraft exits runway
7. `pushback.initiated` - When pushback starts

**Event Bus Integration**:
```python
# After each tick
for aircraft in updated_aircraft:
    # Position update
    await event_bus.publish('aircraft.position_updated', {
        'aircraft_id': aircraft['id'],
        'position': aircraft['position'],
        'tick': self.tick_count
    })
    
    # Zone boundary check
    new_zone = determine_zone(aircraft)
    if new_zone != aircraft['current_zone']:
        await event_bus.publish('zone.boundary_crossed', {
            'aircraft_id': aircraft['id'],
            'from_zone': aircraft['current_zone'],
            'to_zone': new_zone
        })
        aircraft['current_zone'] = new_zone
    
    # Conflict check
    conflicts = detect_conflicts(aircraft, all_aircraft)
    for conflict in conflicts:
        await event_bus.publish('conflict.detected', conflict)
```

---

## 6. PostgreSQL Database: Single Source of Truth

PostgreSQL stores all operational state and serves as the **single source of truth**. All LLM decisions are persisted as clearances before execution, and the engine writes state snapshots every tick.

### 6.1 Schema Design

#### **aircraft_instances** (Flights Table)

```sql
CREATE TABLE aircraft_instances (
    id SERIAL PRIMARY KEY,
    icao24 VARCHAR(6) UNIQUE NOT NULL,
    registration VARCHAR(10) UNIQUE NOT NULL,
    callsign VARCHAR(10) UNIQUE NOT NULL,
    aircraft_type_id INTEGER REFERENCES aircraft_types(id),
    airline_id INTEGER REFERENCES airlines(id),
    
    -- Position (JSONB)
    position JSONB NOT NULL,  -- {lat, lon, altitude_ft, heading, speed_kts}
    
    -- Flight Plan (JSONB)
    flight_plan JSONB,  -- {type: 'ARRIVAL'|'DEPARTURE', origin, destination, runway, entry_waypoint, sid}
    
    -- Control Fields
    controller VARCHAR(20) DEFAULT 'ENGINE',  -- 'ENGINE' | 'AIR_LLM' | 'GROUND_LLM'
    phase VARCHAR(20) DEFAULT 'CRUISE',  -- 'CRUISE' | 'DESCENT' | 'APPROACH' | 'FINAL' | 'TAXI' | 'GATE' | 'PUSHBACK'
    status VARCHAR(20) DEFAULT 'active',  -- 'active' | 'landed' | 'departed'
    
    -- Current Targets (from active clearance)
    target_speed_kts INTEGER,
    target_heading_deg INTEGER,
    target_altitude_ft INTEGER,
    vertical_speed_fpm INTEGER,
    waypoint_sequence JSONB,  -- [{name, altitude_ft, speed_kts, constraint}]
    
    -- State Tracking
    current_zone VARCHAR(20),  -- 'ENTRY' | 'ENROUTE' | 'APPROACH' | 'RUNWAY'
    distance_to_airport_nm DECIMAL(8,2),
    last_event_fired VARCHAR(100),
    squawk_code VARCHAR(4),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_aircraft_instances_controller ON aircraft_instances(controller);
CREATE INDEX idx_aircraft_instances_phase ON aircraft_instances(phase);
CREATE INDEX idx_aircraft_instances_status ON aircraft_instances(status);
CREATE INDEX idx_aircraft_instances_position ON aircraft_instances USING GIN(position);
```

#### **runway_ops** (Runway Operations)

```sql
CREATE TABLE runway_ops (
    id SERIAL PRIMARY KEY,
    aircraft_id INTEGER REFERENCES aircraft_instances(id),
    runway VARCHAR(10) NOT NULL,  -- '05L', '05R', '06L', '06R'
    operation_type VARCHAR(20) NOT NULL,  -- 'LANDING' | 'TAKEOFF' | 'CROSSING'
    scheduled_time TIMESTAMP,
    actual_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'PLANNED',  -- 'PLANNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
    assigned_by VARCHAR(20),  -- 'AIR_LLM' | 'GROUND_LLM'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_runway_ops_runway ON runway_ops(runway);
CREATE INDEX idx_runway_ops_status ON runway_ops(status);
CREATE INDEX idx_runway_ops_scheduled_time ON runway_ops(scheduled_time);
```

#### **clearances** (LLM-Issued Clearances)

```sql
CREATE TABLE clearances (
    id SERIAL PRIMARY KEY,
    aircraft_id INTEGER REFERENCES aircraft_instances(id),
    clearance_type VARCHAR(50) NOT NULL,  -- 'STAR_ASSIGNMENT' | 'VECTORING' | 'TAXI_CLEARANCE' | etc.
    issued_by VARCHAR(20) NOT NULL,  -- 'AIR_LLM' | 'GROUND_LLM'
    issued_at TIMESTAMP DEFAULT NOW(),
    valid_until TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- 'ACTIVE' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED'
    
    -- Structured Instructions (JSONB)
    instructions JSONB NOT NULL,
    
    -- Metadata
    priority VARCHAR(20) DEFAULT 'NORMAL',  -- 'NORMAL' | 'URGENT' | 'EXPEDITE'
    reason TEXT,
    confidence DECIMAL(3,2),  -- 0.00 - 1.00
    
    -- Completion Tracking
    completed_at TIMESTAMP,
    completed_item VARCHAR(50),  -- 'altitude' | 'heading' | 'waypoint' | etc.
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clearances_aircraft_id ON clearances(aircraft_id);
CREATE INDEX idx_clearances_status ON clearances(status);
CREATE INDEX idx_clearances_issued_by ON clearances(issued_by);
CREATE INDEX idx_clearances_valid_until ON clearances(valid_until);
```

#### **gates** (Gate Assignment and Status)

```sql
CREATE TABLE gates (
    id SERIAL PRIMARY KEY,
    gate_name VARCHAR(10) UNIQUE NOT NULL,  -- 'C32', 'A15', etc.
    terminal VARCHAR(50),
    gate_type VARCHAR(20),  -- 'JET_BRIDGE' | 'REMOTE' | 'CARGO'
    compatible_aircraft_types JSONB,  -- ['A320', 'B737', 'A321'] or null for all
    max_wingspan_ft FLOAT,
    status VARCHAR(20) DEFAULT 'AVAILABLE',  -- 'AVAILABLE' | 'OCCUPIED' | 'MAINTENANCE' | 'RESERVED'
    current_aircraft_id INTEGER REFERENCES aircraft_instances(id),
    position JSONB,  -- {lat, lon}
    taxiway_connection VARCHAR(10),  -- Connected taxiway name
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gates_status ON gates(status);
CREATE INDEX idx_gates_terminal ON gates(terminal);
```

#### **taxiway_graph** (Surface Routing Network)

```sql
CREATE TABLE taxiway_graph (
    id SERIAL PRIMARY KEY,
    node_name VARCHAR(20) UNIQUE NOT NULL,  -- 'A1', 'B', 'C32', etc.
    node_type VARCHAR(20),  -- 'TAXIWAY' | 'RUNWAY_EXIT' | 'GATE' | 'APRON'
    position JSONB NOT NULL,  -- {lat, lon}
    connected_nodes JSONB NOT NULL,  -- ['A', 'B', 'C32'] - adjacency list
    restrictions JSONB,  -- {max_aircraft_type: 'HEAVY', one_way: true, etc.}
    runway_crossings JSONB,  -- [{runway: '05R', requires_clearance: true}]
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_taxiway_graph_node_type ON taxiway_graph(node_type);
CREATE INDEX idx_taxiway_graph_position ON taxiway_graph USING GIN(position);
```

#### **events** (Event Log - Audit Trail)

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,  -- 'zone.boundary_crossed' | 'clearance.completed' | etc.
    level VARCHAR(10) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')),
    message TEXT NOT NULL,
    details JSONB,
    aircraft_id INTEGER REFERENCES aircraft_instances(id),
    sector VARCHAR(20),
    frequency VARCHAR(10),
    direction VARCHAR(10) CHECK (direction IN ('TX', 'RX', 'CPDLC', 'XFER', 'SYS')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_aircraft_id ON events(aircraft_id);
CREATE INDEX idx_events_sector ON events(sector);
```

### 6.2 Why PostgreSQL is the Single Source of Truth

1. **Persistence**: All state survives engine restarts, LLM controller restarts
2. **Atomicity**: Database transactions ensure consistency (e.g., clearance creation + aircraft update)
3. **Queryability**: LLMs query current state (active clearances, gate availability, runway occupancy)
4. **Audit Trail**: Events table provides complete history for debugging and compliance
5. **Multi-Actor Coordination**: Multiple LLM controllers read/write same database, avoiding race conditions
6. **Recovery**: If LLM makes bad decision, can query database to understand state at that time

### 6.3 State Synchronization Flow

```
LLM Controller:
  1. Query DB: get_active_aircraft(controller='AIR_LLM')
  2. Query DB: get_active_clearances(aircraft_ids)
  3. Query DB: get_gate_availability()
  4. Make decision based on state
  5. INSERT clearance into DB (transaction)
  6. UPDATE aircraft_instances.controller = 'AIR_LLM' (if handoff)
  7. Publish event: llm.decision_issued

Engine:
  1. Query DB: get_active_aircraft(controller IN ('AIR_LLM', 'GROUND_LLM'))
  2. Query DB: get_active_clearances(aircraft_ids)
  3. Apply clearances (physics)
  4. UPDATE aircraft_instances (position, targets)
  5. INSERT events (clearance completion, zone crossing)
  6. Publish to event bus
```

---

## 7. Ground LLM Event Subscription and Synchronization

The Ground LLM subscribes to events and synchronizes its decisions with the Air LLM state.

### 7.1 Event Subscription

**Ground LLM Subscribes To**:

1. `runway.landed` - Aircraft touchdown, take control for taxi
2. `runway.vacated` - Aircraft exited runway, issue full taxi clearance
3. `pushback.initiated` - Departure pushback started, sequence taxi
4. `clearance.completed` (ground clearances) - Taxi waypoint reached, continue routing
5. `aircraft.position_updated` (ground phase only) - Track surface movement

**Code Example**:
```python
class GroundLLMController:
    async def initialize(self):
        # Connect to event bus
        await self.event_bus.connect()
        
        # Subscribe to events
        await self.event_bus.subscribe('runway.landed', self.on_runway_landed)
        await self.event_bus.subscribe('runway.vacated', self.on_runway_vacated)
        await self.event_bus.subscribe('pushback.initiated', self.on_pushback_initiated)
        await self.event_bus.subscribe('clearance.completed', self.on_clearance_completed)
        await self.event_bus.subscribe('aircraft.position_updated', self.on_position_updated)
        
        # Connect to database
        await self.db.connect()
    
    async def on_runway_landed(self, event: dict):
        """Handle aircraft landing."""
        aircraft_id = event['data']['aircraft_id']
        callsign = event['data']['callsign']
        runway = event['data']['runway']
        
        # Query aircraft state from DB
        aircraft = await self.db.get_aircraft(aircraft_id)
        
        # Assign gate (if not already assigned)
        gate_assignment = await self.assign_gate(aircraft)
        
        # Issue taxi clearance
        taxi_clearance = await self.issue_taxi_clearance(
            aircraft_id=aircraft_id,
            from_location='runway_vacate',
            to_gate=gate_assignment['gate'],
            runway=runway
        )
        
        # Persist clearance to DB
        await self.db.create_clearance(taxi_clearance)
        
        # Update aircraft controller
        await self.db.update_aircraft(aircraft_id, {
            'controller': 'GROUND_LLM',
            'phase': 'TAXI'
        })
    
    async def on_runway_vacated(self, event: dict):
        """Handle aircraft vacating runway."""
        aircraft_id = event['data']['aircraft_id']
        vacate_taxiway = event['data']['vacate_taxiway']
        
        # Query current clearance
        active_clearance = await self.db.get_active_clearance(aircraft_id)
        
        if active_clearance and active_clearance['clearance_type'] == 'TAXI_CLEARANCE':
            # Update clearance route (remove runway vacate, continue to gate)
            # Ground LLM re-evaluates route and issues updated clearance
            await self.reissue_taxi_clearance(aircraft_id)
```

### 7.2 Synchronization with Air LLM

**Handoff Points**:

1. **Landing → Taxi**:
   - Air LLM completes landing clearance, aircraft lands
   - Engine emits `runway.landed` event
   - Ground LLM takes control, issues gate assignment + taxi clearance
   - Database updated: `aircraft_instances.controller = 'GROUND_LLM'`

2. **Pushback → Taxi → Takeoff**:
   - Ground LLM issues pushback clearance, sequences taxi
   - When aircraft reaches runway hold point, Ground LLM notifies Air LLM
   - Air LLM takes control, issues departure clearance
   - Database updated: `aircraft_instances.controller = 'AIR_LLM'`

**Synchronization Mechanism**:
```python
# Ground LLM coordinates with Air LLM
async def coordinate_departure(self, aircraft_id: int):
    """Coordinate departure sequence between Ground and Air LLMs."""
    
    # Query aircraft state
    aircraft = await self.db.get_aircraft(aircraft_id)
    
    # Ground LLM issues taxi to runway hold
    taxi_clearance = {
        'clearance_type': 'TAXI_CLEARANCE',
        'aircraft_id': aircraft_id,
        'instructions': {
            'from': aircraft['current_gate'],
            'to': f'runway_{aircraft["flight_plan"]["runway"]}_hold',
            'route': calculate_taxi_route(aircraft),
            'hold_short': [{'runway': aircraft['flight_plan']['runway']}]
        }
    }
    await self.db.create_clearance(taxi_clearance)
    
    # Notify Air LLM of pending departure
    await self.event_bus.publish('departure.ready_for_clearance', {
        'aircraft_id': aircraft_id,
        'runway': aircraft['flight_plan']['runway'],
        'estimated_time': calculate_estimated_arrival_at_hold()
    })
    
    # Air LLM subscribes to this event and issues departure clearance
```

### 7.3 Periodic State Review

**Every 30 seconds**, both LLMs perform a periodic review:

```python
async def periodic_review(self):
    """Re-evaluate all aircraft under control."""
    while self.running:
        # Query all aircraft under my control
        my_aircraft = await self.db.get_active_aircraft(controller='GROUND_LLM')
        
        for aircraft in my_aircraft:
            # Re-evaluate gate assignment (if needed)
            # Re-evaluate taxi route (if traffic changed)
            # Re-issue updated clearances if conditions changed
        
        await asyncio.sleep(30)
```

---

## 8. Information Required From ChatGPT to Finalize Integration

To generate the actual implementation code, the following information must be provided. Each item represents a critical design decision that affects the system architecture and LLM prompt engineering.

### 8.1 Airport Data Structures

#### 8.1.1 Taxiway Graph JSON Format

**Required**: Complete specification of taxiway graph data structure.

**Questions**:
- What is the exact JSON schema for taxiway nodes?
- How are edges represented (adjacency list, edge list, matrix)?
- What metadata is stored per node (position, restrictions, runway crossings)?
- Are there hierarchical relationships (taxiway → segment → intersection)?

**Example Template Needed**:
```json
{
  "taxiway_graph": {
    "nodes": [
      {
        "id": "A1",
        "type": "TAXIWAY",
        "position": {"lat": 43.6777, "lon": -79.6248},
        "connections": ["A", "B"],
        "restrictions": {"max_aircraft_type": "HEAVY", "one_way": false},
        "runway_crossings": [{"runway": "05R", "requires_clearance": true}]
      }
    ],
    "edges": [...]
  }
}
```

#### 8.1.2 Waypoint Catalog Structure

**Required**: Specification of waypoint data format.

**Questions**:
- How are waypoints stored (name, lat/lon, altitude constraints)?
- What waypoint types exist (fix, VOR, NDB, RNAV, STAR entry, SID exit)?
- How are STAR procedures defined (name, entry fix, transitions, waypoint sequences)?
- How are altitude/speed constraints stored per waypoint?

**Example Template Needed**:
```json
{
  "waypoints": [
    {
      "name": "BOTTO",
      "type": "FIX",
      "position": {"lat": 43.8500, "lon": -79.5000},
      "altitude_constraints": null
    }
  ],
  "stars": [
    {
      "name": "BOTTO5",
      "entry_fix": "BOTTO",
      "runway": "05L",
      "waypoints": [
        {"name": "BOTTO", "altitude_ft": 17000, "speed_kts": 250},
        {"name": "VEVOD", "altitude_ft": 12000, "speed_kts": 220}
      ]
    }
  ]
}
```

#### 8.1.3 Gate Compatibility Rules

**Required**: Rules for matching aircraft to gates.

**Questions**:
- What aircraft types can use which gates (size, weight, wingspan)?
- Are there airline-specific gate assignments?
- What is the turnaround time logic (depends on aircraft type, airline, gate type)?
- How are gate conflicts resolved (first-come-first-served, priority, schedule)?

**Example Template Needed**:
```json
{
  "gates": [
    {
      "gate_name": "C32",
      "compatible_aircraft_types": ["A320", "A321", "B737"],
      "max_wingspan_ft": 118,
      "airline_preferences": ["ACA", "AC"],
      "default_turnaround_min": 45
    }
  ],
  "turnaround_time_rules": {
    "A320": 45,
    "B737": 45,
    "A321": 50,
    "B787": 90
  }
}
```

### 8.2 Engine Integration Details

#### 8.2.1 Clearance Application Mechanism

**Required**: Exact mechanism for how engine applies clearances.

**Questions**:
- How does the engine currently apply `target_speed_kts`, `target_heading_deg`, `target_altitude_ft`?
- What are the acceleration/deceleration profiles (linear, exponential, lookup table)?
- How are waypoint sequences followed (direct-to, intercept course, fly-over vs fly-by)?
- What happens when a clearance expires before completion?

**Code Examples Needed**:
- Function signature: `apply_clearance(aircraft: dict, clearance: dict) -> dict`
- Kinematics update logic with clearance targets
- Waypoint sequencing algorithm

#### 8.2.2 Clearance Completion Detection Logic

**Required**: Exact thresholds and logic for detecting clearance completion.

**Questions**:
- What are the exact thresholds for altitude (±100 ft?), heading (±5 deg?), speed (±5 kts?).
- How is waypoint passage detected (distance threshold, crossed line, time-based)?
- What is the detection frequency (every tick, every N ticks)?
- How are false positives avoided (hysteresis, confirmation over multiple ticks)?

**Code Examples Needed**:
- Function signature: `check_clearance_completion(aircraft: dict, clearance: dict) -> CompletionStatus`
- Threshold values as constants
- Detection algorithm pseudocode

### 8.3 LLM Controller Specifications

#### 8.3.1 Air LLM Roles and Behaviors Per Zone

**Required**: Detailed behavior specification for each airspace zone.

**Questions**:
- **ENTRY Zone (60-80 NM)**: What decisions does Air LLM make? (STAR assignment, initial descent, speed reduction?)
- **ENROUTE Zone (10-60 NM)**: What decisions? (Waypoint sequencing, descent profile, conflict resolution?)
- **APPROACH Zone (3-10 NM)**: What decisions? (Final approach course, speed control, sequencing?)
- **RUNWAY Zone (0-3 NM)**: What decisions? (Landing clearance, missed approach handling?)

**Specification Template Needed**:
```yaml
AIR_LLM_BEHAVIORS:
  ENTRY_ZONE:
    responsibilities: [STAR_ASSIGNMENT, INITIAL_DESCENT, SPEED_REDUCTION]
    clearance_types: [STAR_ASSIGNMENT, DESCENT_PROFILE, SPEED_ASSIGNMENT]
    decision_frequency: "on_zone_entry + every_30_sec"
  
  APPROACH_ZONE:
    responsibilities: [FINAL_APPROACH_COURSE, SPEED_CONTROL, SEQUENCING]
    clearance_types: [VECTORING, SPEED_ASSIGNMENT, LANDING_CLEARANCE]
    decision_frequency: "on_clearance_completion + every_15_sec"
```

#### 8.3.2 Ground LLM Roles and Behaviors

**Required**: Detailed behavior specification for ground operations.

**Questions**:
- When does Ground LLM assign gates (on landing, on departure planning, pre-assignment)?
- How does Ground LLM calculate taxi routes (Dijkstra, A*, pre-defined, LLM-generated)?
- How are runway crossings coordinated (check runway occupancy, get clearance, timing)?
- What is pushback sequencing logic (first-come-first-served, schedule-based, priority)?

**Specification Template Needed**:
```yaml
GROUND_LLM_BEHAVIORS:
  GATE_ASSIGNMENT:
    trigger: "on_runway_landed + on_flight_scheduled"
    algorithm: "airline_preference + availability + turnaround_time"
    constraints: [aircraft_type_compatibility, gate_capacity]
  
  TAXI_ROUTING:
    algorithm: "Dijkstra_shortest_path + conflict_avoidance"
    constraints: [one_way_taxiways, runway_crossings, traffic_avoidance]
```

### 8.4 Data Schema Specifications

#### 8.4.1 Clearance JSON Schema

**Required**: Complete, validated JSON schema for all clearance types.

**Questions**:
- What fields are required vs optional for each clearance type?
- What are valid value ranges (altitude: 0-60000 ft, speed: 100-500 kts)?
- How are nested instructions structured?
- What validation rules apply (e.g., descent rate must be negative)?

**JSON Schema Needed**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "ClearanceBase": {
      "type": "object",
      "required": ["clearance_type", "aircraft_id", "instructions"],
      "properties": {
        "clearance_type": {"type": "string", "enum": [...]},
        "aircraft_id": {"type": "integer"},
        "instructions": {"type": "object"}
      }
    },
    "VECTORING": {...},
    "DESCENT_PROFILE": {...}
  }
}
```

### 8.5 Operational Constraints

#### 8.5.1 Runway Configuration

**Required**: Complete runway inventory.

**Questions**:
- How many runways exist? (e.g., CYYZ has 05L, 05R, 06L, 06R?)
- What are runway identifiers and orientations?
- What are runway-exit taxiway names and positions?
- Which runways are used for arrivals vs departures?

**Data Needed**:
```json
{
  "runways": [
    {"id": "05L", "heading_deg": 050, "length_ft": 11000, "width_ft": 200},
    {"id": "05R", "heading_deg": 050, "length_ft": 11000, "width_ft": 200}
  ],
  "runway_exits": [
    {"runway": "05L", "exit_taxiway": "A1", "position_ft": 3000},
    {"runway": "05L", "exit_taxiway": "A2", "position_ft": 5000}
  ]
}
```

#### 8.5.2 Performance and Latency Constraints

**Required**: System performance requirements.

**Questions**:
- What is the maximum acceptable latency from event → LLM decision → clearance in DB? (e.g., < 2 seconds?)
- How many concurrent aircraft can each LLM handle? (e.g., Air LLM: 50, Ground LLM: 20?)
- What is the maximum rate of clearance issuance? (e.g., 100 clearances/minute?)
- What are the LLM API rate limits? (Ollama local vs cloud API?)

**Specification Needed**:
```yaml
PERFORMANCE_REQUIREMENTS:
  event_to_decision_latency_ms: 2000
  decision_to_db_latency_ms: 500
  max_concurrent_aircraft_per_llm: 50
  max_clearances_per_minute: 100
  llm_api_timeout_sec: 10
  llm_api_retry_attempts: 3
```

#### 8.5.3 Concurrency and Race Conditions

**Required**: Handling of concurrent LLM decisions.

**Questions**:
- What happens if Air LLM and Ground LLM both try to control same aircraft?
- How are database write conflicts handled (optimistic locking, pessimistic locking)?
- What is the event processing order (FIFO, priority queue, timestamp-based)?
- How are stale clearances detected and cancelled?

**Specification Needed**:
```yaml
CONCURRENCY_CONTROL:
  aircraft_controller_lock: "database_transaction"
  clearance_conflict_resolution: "latest_wins + validation"
  event_processing_order: "FIFO_by_timestamp"
  stale_clearance_timeout_sec: 300
```

### 8.6 Event Bus Technology Choice

#### 8.6.1 Redis vs NATS Decision

**Required**: Final decision on event bus technology.

**Questions**:
- Should we use Redis Pub/Sub or NATS?
- What are the scalability requirements (number of subscribers, message rate)?
- Do we need message persistence (NATS JetStream) or is in-memory (Redis) sufficient?
- What is the deployment environment (local, cloud, hybrid)?

**Decision Matrix Needed**:
| Feature | Redis Pub/Sub | NATS | NATS JetStream |
|---------|--------------|------|----------------|
| Latency | < 1 ms | < 1 ms | < 1 ms |
| Persistence | No | No | Yes |
| Message Ordering | Per-channel | Per-subject | Per-stream |
| Scalability | High | Very High | Very High |

**Recommendation**: Based on requirements, choose one and specify configuration.

### 8.7 LLM Integration Details

#### 8.7.1 LLM API and Prompt Engineering

**Required**: LLM provider and prompt structure.

**Questions**:
- Which LLM provider? (Ollama local, OpenAI, Anthropic, self-hosted?)
- What is the exact prompt template for Air LLM? (include context: aircraft state, active clearances, conflicts, sector boundaries)
- What is the exact prompt template for Ground LLM? (include context: gate availability, taxiway traffic, runway occupancy)
- How is structured JSON output enforced? (function calling, JSON mode, prompt engineering?)

**Prompt Templates Needed**:
```
AIR_LLM_PROMPT_TEMPLATE: |
  You are an Air Traffic Controller managing aircraft in the {zone} zone.
  
  Current aircraft state:
  {aircraft_state_json}
  
  Active clearances:
  {active_clearances_json}
  
  Detected conflicts:
  {conflicts_json}
  
  Issue a clearance in the following JSON format:
  {clearance_schema_json}
  
  Response:
```

#### 8.7.2 LLM Response Validation

**Required**: Validation and error handling for LLM responses.

**Questions**:
- What happens if LLM returns invalid JSON?
- What happens if LLM returns clearance with invalid values (e.g., altitude > ceiling)?
- How are LLM confidence scores used (reject if < threshold)?
- What is the fallback behavior (default clearance, manual intervention, retry)?

**Validation Rules Needed**:
```python
def validate_clearance(clearance: dict, aircraft: dict) -> ValidationResult:
    """Validate LLM-issued clearance."""
    # Check JSON schema
    # Check value ranges
    # Check aircraft capabilities
    # Check safety constraints
    # Return ValidationResult(valid=True/False, errors=[...])
```

---

## 9. Implementation Checklist

Once all information from Section 8 is provided, the following implementation steps can proceed:

### Phase 1: Database Schema Extensions
- [ ] Add `clearances` table schema
- [ ] Add `runway_ops` table schema
- [ ] Add `gates` table schema
- [ ] Add `taxiway_graph` table schema
- [ ] Extend `aircraft_instances` with clearance fields
- [ ] Create database migration scripts
- [ ] Create seed data scripts (gates, taxiway graph, waypoints)

### Phase 2: Engine Integration
- [ ] Implement clearance loading from DB
- [ ] Implement clearance application logic
- [ ] Implement clearance completion detection
- [ ] Implement event emission (zone boundaries, conflicts, landing, vacate, pushback)
- [ ] Add unit tests for clearance completion detection

### Phase 3: Air LLM Controller
- [ ] Implement event subscription (zone boundaries, clearance completion, conflicts)
- [ ] Implement LLM API integration (Ollama/OpenAI)
- [ ] Implement prompt engineering (context building, structured output)
- [ ] Implement clearance issuance (validate, persist to DB)
- [ ] Implement periodic review loop (30-second intervals)
- [ ] Add unit tests for clearance generation

### Phase 4: Ground LLM Controller
- [ ] Implement event subscription (landing, vacate, pushback)
- [ ] Implement LLM API integration
- [ ] Implement gate assignment algorithm
- [ ] Implement taxi routing algorithm (Dijkstra/A*)
- [ ] Implement runway crossing coordination
- [ ] Implement pushback sequencing
- [ ] Add unit tests for ground operations

### Phase 5: Integration and Testing
- [ ] End-to-end test: arrival sequence (Air LLM)
- [ ] End-to-end test: landing → taxi → gate (Ground LLM)
- [ ] End-to-end test: pushback → taxi → takeoff (Ground + Air LLM)
- [ ] Performance testing (latency, throughput, concurrency)
- [ ] Stress testing (high traffic scenarios)

### Phase 6: Production Deployment
- [ ] Configuration management (environment variables, config files)
- [ ] Monitoring and logging (LLM decision logs, performance metrics)
- [ ] Error handling and recovery (LLM API failures, database errors)
- [ ] Documentation (operational runbook, troubleshooting guide)

---

## 10. Conclusion

This document provides a complete, production-ready system design for integrating LLM controllers into the ATC system. The architecture maintains the existing KinematicsEngine as the deterministic physics core, adds two specialized LLM controllers for airspace and ground operations, and uses PostgreSQL as the single source of truth with an event bus for real-time coordination.

**Key Design Principles**:
1. **Determinism**: Engine remains deterministic, LLMs only issue clearances
2. **Persistence**: All state in PostgreSQL, survives restarts
3. **Event-Driven**: LLMs react to events, not polling
4. **Structured Output**: LLMs output validated JSON, not free-form text
5. **Synchronization**: Ground and Air LLMs coordinate through events and database

**Next Steps**:
1. Gather all information listed in Section 8
2. Implement database schema extensions (Phase 1)
3. Implement engine integration (Phase 2)
4. Implement LLM controllers (Phases 3-4)
5. Integration testing and production deployment (Phases 5-6)

Once all information from Section 8 is provided, the implementation can proceed systematically through the phases outlined in Section 9.

