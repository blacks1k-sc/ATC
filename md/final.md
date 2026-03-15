# ATC System - Complete Project Architecture & Engine Documentation

## Executive Summary

This document provides a comprehensive overview of the **AI Air Traffic Control (ATC) Simulation System** - a production-grade, real-time simulation platform that recreates authentic air traffic control operations. The system combines a deterministic 1 Hz physics engine (Python) with a modern web interface (Next.js/React) to deliver real-time aircraft tracking, radar displays, and operational management.

**Key Characteristics**:
- **Real-Time**: 1 Hz deterministic physics simulation with sub-second latency to UI
- **Production-Ready**: Non-blocking architecture, batched I/O, graceful error handling
- **Scalable**: Async workers, connection pooling, efficient event streaming
- **Live Updates**: Real-time UI updates via Redis pub/sub and Server-Sent Events (SSE)
- **Persistent**: PostgreSQL as single source of truth, complete audit trail

---

## 1. Project Overview

### 1.1 What Is This System?

The ATC System is a **full-stack, real-time aircraft simulation and management platform** that simulates air traffic control operations at Toronto Pearson International Airport (CYYZ). It demonstrates:

- **Physics-Based Aircraft Movement**: Deterministic kinematics using real aviation formulas
- **Real-Time Radar Display**: Live aircraft positions with radar sweep animations
- **Multi-Sector Airspace**: Entry, Enroute, Approach, and Runway sectors with automatic transitions
- **Ground Operations**: Taxi routing, gate assignments, runway operations
- **Event-Driven Architecture**: Redis-based event bus for decoupled, scalable communication
- **Persistent State**: PostgreSQL database with complete audit logging

### 1.2 System Components

The project consists of **three main subsystems**:

1. **Frontend + API Layer** (`atc-nextjs/`)
   - Next.js 14 + React + TypeScript web application
   - Real-time radar display with interactive maps
   - REST API routes for data access
   - Server-Sent Events (SSE) for live updates

2. **Physics Engine** (`atc-brain-python/`)
   - Python 3.11+ with asyncio
   - Deterministic 1 Hz tick loop
   - Aircraft kinematics calculations
   - Async I/O workers for non-blocking operations

3. **Data Pipeline** (`data-pipeline/`)
   - Aircraft type and airline data collection
   - Multi-source API aggregation
   - Data validation and normalization

---

## 2. Complete System Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ATC SYSTEM ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      FRONTEND LAYER (Next.js)                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │   Radar      │  │    Ground    │  │  Engine Ops  │             │   │
│  │  │   Display    │  │  Operations  │  │    Monitor   │             │   │
│  │  │              │  │              │  │              │             │   │
│  │  │  Live SSE    │  │  Live SSE    │  │  Live SSE    │             │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │   │
│  └─────────┼──────────────────┼──────────────────┼─────────────────────┘   │
│            │                  │                  │                          │
│  ┌─────────▼──────────────────▼──────────────────▼─────────────────────┐   │
│  │                    API LAYER (Next.js API Routes)                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │   REST API   │  │  SSE Stream  │  │  Event Bus   │             │   │
│  │  │   /api/*     │  │  /api/events │  │  Subscriber  │             │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │   │
│  └─────────┼──────────────────┼──────────────────┼─────────────────────┘   │
│            │                  │                  │                          │
│  ┌─────────▼──────────────────▼──────────────────▼─────────────────────┐   │
│  │                      EVENT BUS (Redis)                               │   │
│  │  Channel: atc:events                                                 │   │
│  │  • aircraft.position_updated                                         │   │
│  │  • aircraft.created                                                  │   │
│  │  • aircraft.status_changed                                           │   │
│  │  • zone.boundary_crossed                                             │   │
│  │  • clearance.completed                                               │   │
│  └─────────┬──────────────────┬──────────────────┬─────────────────────┘   │
│            │                  │                  │                          │
│  ┌─────────▼──────────────────▼──────────────────▼─────────────────────┐   │
│  │                   PHYSICS ENGINE (Python)                            │   │
│  │  ┌─────────────────────────────────────────────────────┐           │   │
│  │  │         KinematicsEngine (1 Hz Tick Loop)           │           │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│           │   │
│  │  │  │  Physics    │  │   State     │  │   Event     ││           │   │
│  │  │  │  Module     │  │  Manager    │  │  Publisher  ││           │   │
│  │  │  └─────────────┘  └──────┬──────┘  └──────┬──────┘│           │   │
│  │  │                          │                 │        │           │   │
│  │  │  ┌─────────────┐  ┌──────▼────────────────▼──────┐│           │   │
│  │  │  │ Async       │  │    Worker Buffers             ││           │   │
│  │  │  │ Workers:    │  │  • db_updates_buffer          ││           │   │
│  │  │  │ • db_worker │  │  • redis_events_buffer        ││           │   │
│  │  │  │ • redis_    │  │  • telemetry_buffer           ││           │   │
│  │  │  │   worker    │  │  • pending_db_events          ││           │   │
│  │  │  │ • telemetry │  │                              ││           │   │
│  │  │  │   worker    │  └──────────────────────────────┘│           │   │
│  │  │  └─────────────┘                                   │           │   │
│  │  └─────────────────────────────────────────────────────┘           │   │
│  └─────────┬──────────────────┬──────────────────┬─────────────────────┘   │
│            │                  │                  │                          │
│  ┌─────────▼──────────────────▼──────────────────▼─────────────────────┐   │
│  │                  DATABASE (PostgreSQL)                               │   │
│  │  • aircraft_instances  • events  • aircraft_types  • airlines       │   │
│  │  Single Source of Truth - All state persisted                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

#### **Frontend Layer (Next.js)**
- **Radar Display**: Interactive radar map with live aircraft positions
- **Ground Operations**: Airport layout, gates, taxiways, runway visualization
- **Engine Ops Monitor**: Real-time engine state, aircraft list, sector filtering
- **Communications Log**: ATC message logs with filtering and search
- **Control Panels**: Flight strips, weather data, system status

#### **API Layer (Next.js API Routes)**
- **REST Endpoints**: `/api/aircraft`, `/api/events`, `/api/airport/[icao]`
- **SSE Stream**: `/api/events/stream` - Server-Sent Events for real-time updates
- **Event Bus Integration**: Subscribes to Redis, forwards events to SSE clients
- **Database Access**: Connection pooling, transaction management

#### **Event Bus (Redis)**
- **Pub/Sub Channel**: `atc:events`
- **Message Format**: JSON with `type`, `data`, `timestamp`
- **Decoupled Communication**: Engine publishes, Next.js subscribes
- **Scalability**: Multiple subscribers, low latency (<1ms)

#### **Physics Engine (Python)**
- **1 Hz Tick Loop**: Deterministic physics simulation
- **Aircraft Kinematics**: Speed, heading, altitude calculations
- **State Management**: Database persistence via async workers
- **Event Emission**: Real-time events to Redis
- **Non-Blocking I/O**: All I/O delegated to async workers

#### **Database (PostgreSQL)**
- **Single Source of Truth**: All operational state
- **Tables**: `aircraft_instances`, `events`, `aircraft_types`, `airlines`
- **Audit Trail**: Complete event history
- **Indexes**: Optimized for real-time queries

---

## 3. Engine Architecture (Detailed)

### 3.1 Core Design Principles

The KinematicsEngine is designed with **three fundamental principles**:

1. **Determinism**: Physics loop runs at exactly 1 Hz with predictable results
2. **Non-Blocking**: All I/O (database, Redis, telemetry) is asynchronous
3. **Single Source of Truth**: Database is authoritative, Redis is for real-time distribution

### 3.2 Engine Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    KinematicsEngine Architecture                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │               MAIN TICK LOOP (1 Hz, Synchronous)              │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │  async def tick(self):                                  │ │ │
│  │  │    1. Fetch active aircraft from DB                     │ │ │
│  │  │    2. For each aircraft:                                │ │ │
│  │  │       a. Apply physics (process_aircraft_sync)          │ │ │
│  │  │       b. Queue updates to buffers (non-blocking)        │ │ │
│  │  │    3. Sleep until next second                           │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────┬──────────────────────────────────────────┘ │
│                         │                                             │
│                         ▼                                             │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │          WORKER BUFFERS (In-Memory Queues)                    │ │
│  │  • db_updates_buffer: List[Dict]                              │ │
│  │  • redis_events_buffer: List[Tuple[str, Dict]]                │ │
│  │  • telemetry_buffer: List[Dict]                               │ │
│  │  • pending_db_events: List[Dict]                              │ │
│  └──────────────────────┬──────────────────────────────────────────┘ │
│                         │                                             │
│         ┌───────────────┼───────────────┐                           │
│         │               │               │                           │
│         ▼               ▼               ▼                           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                      │
│  │   DB     │   │  Redis   │   │Telemetry │                      │
│  │  Worker  │   │  Worker  │   │  Worker  │                      │
│  │          │   │          │   │          │                      │
│  │ Every 1s │   │ 20-50ms  │   │ Every 10s│                      │
│  │  Batch   │   │  Batch   │   │  Flush   │                      │
│  │  Write   │   │ Publish  │   │  File    │                      │
│  └──────────┘   └──────────┘   └──────────┘                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Tick Loop Execution Flow

**Every Second (1 Hz)**:

```python
async def tick(self):
    """Main physics loop - runs every second."""
    tick_start = time.time()
    self.tick_count += 1
    
    # 1. Fetch active aircraft from database
    aircraft_list = await self.state_manager.get_active_arrivals("ENGINE")
    
    # 2. Process each aircraft (pure computation, no I/O)
    for aircraft in aircraft_list:
        # Apply physics formulas
        updated_aircraft = self.process_aircraft_sync(aircraft)
        
        # Queue updates to buffers (non-blocking)
        self.db_updates_buffer.append({
            'id': updated_aircraft['id'],
            'update': updated_aircraft
        })
        
        # Queue Redis event (non-blocking)
        self.redis_events_buffer.append((
            'aircraft.position_updated',
            {
                'aircraft': updated_aircraft,
                'tick': self.tick_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        ))
    
    # 3. Wait until next second
    elapsed = time.time() - tick_start
    sleep_time = max(0, 1.0 - elapsed)
    await asyncio.sleep(sleep_time)
```

**Key Points**:
- **Deterministic**: Physics calculations are pure functions
- **Non-Blocking**: All I/O is queued to buffers
- **Bounded Time**: Tick duration must be < 1 second
- **Target**: Tick duration < 50ms (leaves 950ms for worker I/O)

### 3.4 Async Workers Architecture

#### **DB Worker** (Batches every 1 second)

```python
async def db_worker(self):
    """Batches database writes every 1 second."""
    while self.running:
        await asyncio.sleep(1.0)  # Wait 1 second
        
        if self.db_updates_buffer:
            # Batch update all aircraft states
            updates = list(self.db_updates_buffer)
            self.db_updates_buffer.clear()
            
            await self.state_manager.batch_update_aircraft_states(updates)
            await self.state_manager.batch_create_events(self.pending_db_events)
            self.pending_db_events.clear()
            
            self.stats['db_writes'] += len(updates)
```

**Performance**:
- **Before**: N database queries per tick (one per aircraft)
- **After**: 1 batch query per second
- **Reduction**: N:1 ratio (e.g., 50 aircraft = 50x reduction)

#### **Redis Worker** (Batches every 20-50ms)

```python
async def redis_worker(self):
    """Batches Redis publishes every 20-50ms for real-time UI updates."""
    batch_interval = 0.05  # 50ms in PROD, 100ms in DEV
    
    while self.running:
        await asyncio.sleep(batch_interval)
        
        if self.redis_events_buffer:
            # Batch publish all events
            events = list(self.redis_events_buffer)
            self.redis_events_buffer.clear()
            
            await self.event_publisher.batch_publish_events(events)
            
            self.stats['redis_publishes'] += len(events)
```

**Performance**:
- **Before**: 1 Redis publish per aircraft per tick
- **After**: 20-50 events per batch
- **Latency**: < 50ms to UI (vs < 1ms unbatched, but CPU-intensive)
- **Balance**: Low latency + CPU efficiency

#### **Telemetry Worker** (Flushes every 10 seconds)

```python
async def telemetry_worker(self):
    """Writes telemetry to disk every 10 seconds."""
    while self.running:
        await asyncio.sleep(10.0)  # Wait 10 seconds
        
        if self.telemetry_buffer:
            # Write telemetry snapshot
            snapshot = {
                'tick': self.tick_count,
                'timestamp': datetime.utcnow().isoformat(),
                'aircraft': list(self.telemetry_buffer)
            }
            
            telemetry_file = os.path.join(
                self.telemetry_dir,
                f'telemetry_{int(time.time())}.json'
            )
            
            with open(telemetry_file, 'w') as f:
                json.dump(snapshot, f)
            
            self.telemetry_buffer.clear()
            self.stats['telemetry_writes'] += 1
```

**Purpose**: Historical flight data for analysis and debugging

### 3.5 Physics Calculations (Kinematics Module)

The `kinematics.py` module implements **realistic aircraft motion** using aviation formulas:

```python
def update_aircraft_state(aircraft: dict, dt: float) -> dict:
    """Apply physics-based motion to aircraft."""
    
    # 1. Update speed toward target
    current_speed = aircraft['position']['speed_kts']
    target_speed = aircraft.get('target_speed_kts', current_speed)
    
    if target_speed != current_speed:
        # Apply acceleration/deceleration
        accel = A_ACC_MAX if target_speed > current_speed else -A_DEC_MAX
        new_speed = current_speed + (accel * dt)
        new_speed = max(MIN_SPEED, min(MAX_SPEED, new_speed))
    else:
        new_speed = current_speed
    
    # 2. Update heading toward target
    current_heading = aircraft['position']['heading']
    target_heading = aircraft.get('target_heading_deg', current_heading)
    
    if target_heading != current_heading:
        # Calculate turn rate (based on speed and bank angle)
        turn_rate = calculate_turn_rate(new_speed, PHI_MAX_DEG)
        new_heading = turn_toward(current_heading, target_heading, turn_rate, dt)
    else:
        new_heading = current_heading
    
    # 3. Update altitude toward target
    current_alt = aircraft['position']['altitude_ft']
    target_alt = aircraft.get('target_altitude_ft', current_alt)
    
    if target_alt != current_alt:
        # Calculate vertical speed
        vertical_speed = calculate_vertical_speed(current_alt, target_alt, dt)
        new_alt = current_alt + (vertical_speed * dt)
    else:
        new_alt = current_alt
    
    # 4. Update position (lat/lon)
    new_lat, new_lon = update_position(
        aircraft['position']['lat'],
        aircraft['position']['lon'],
        new_heading,
        new_speed,
        dt
    )
    
    return {
        **aircraft,
        'position': {
            'lat': new_lat,
            'lon': new_lon,
            'altitude_ft': new_alt,
            'heading': new_heading,
            'speed_kts': new_speed
        },
        'vertical_speed_fpm': vertical_speed
    }
```

**Key Formulas**:
- **Turn Rate**: Based on speed and bank angle (maximum 25° bank)
- **Acceleration**: ±0.6 kt/s (accel), ±0.8 kt/s (deceleration)
- **Vertical Speed**: ±2500 fpm (climb), ±3000 fpm (descent)
- **Position Update**: Great circle distance calculations

### 3.6 Event Detection and Emission

The engine detects various conditions and emits events:

**Zone Boundary Crossings**:
```python
# Check if aircraft crossed sector boundary
new_zone = determine_zone(distance_nm, altitude_ft)
if new_zone != aircraft['current_zone']:
    self.redis_events_buffer.append((
        'zone.boundary_crossed',
        {
            'aircraft_id': aircraft['id'],
            'from_zone': aircraft['current_zone'],
            'to_zone': new_zone,
            'distance_nm': distance_nm
        }
    ))
```

**Clearance Completion**:
```python
# Check if aircraft reached target altitude
if abs(current_alt - target_alt) < 100 and abs(vertical_speed) < 100:
    self.redis_events_buffer.append((
        'clearance.completed',
        {
            'aircraft_id': aircraft['id'],
            'clearance_id': clearance['id'],
            'completed_item': 'altitude'
        }
    ))
```

**Touchdown Detection**:
```python
# Check if aircraft landed
altitude_agl = altitude_msl_to_agl(altitude_ft, AIRPORT_ELEVATION)
if altitude_agl < 50 and on_runway(position, runway):
    self.redis_events_buffer.append((
        'runway.landed',
        {
            'aircraft_id': aircraft['id'],
            'runway': runway,
            'touchdown_speed_kts': speed_kts
        }
    ))
```

---

## 4. Live UI Update Mechanism

### 4.1 Data Flow: Engine → UI

The live update system uses a **three-layer architecture**:

```
Engine (1 Hz Tick)
    │
    │ [Publish to Redis]
    ▼
Redis Pub/Sub (atc:events)
    │
    │ [Subscribe]
    ▼
Next.js EventBus (lib/eventBus.ts)
    │
    │ [Forward to SSE Stream]
    ▼
SSE API Route (/api/events/stream)
    │
    │ [Server-Sent Events]
    ▼
React Components (RadarDisplay, EngineOps, etc.)
    │
    │ [State Update]
    ▼
UI Renders (Live Aircraft Positions)
```

### 4.2 Step-by-Step Flow

#### **Step 1: Engine Publishes to Redis**

Every tick, the engine publishes aircraft position updates:

```python
# In KinematicsEngine.redis_worker()
await self.event_publisher.batch_publish_events([
    (
        'aircraft.position_updated',
        {
            'type': 'aircraft.position_updated',
            'data': {
                'aircraft': {
                    'id': 12345,
                    'callsign': 'ACA217',
                    'position': {
                        'lat': 43.7234,
                        'lon': -79.5891,
                        'altitude_ft': 12500,
                        'heading': 180,
                        'speed_kts': 280
                    }
                },
                'tick': 150,
                'timestamp': '2024-01-15T14:23:45Z'
            }
        }
    )
])
```

**Redis Message Format**:
```json
{
  "type": "aircraft.position_updated",
  "data": {
    "aircraft": {...},
    "tick": 150,
    "timestamp": "2024-01-15T14:23:45Z"
  },
  "timestamp": "2024-01-15T14:23:45Z"
}
```

**Channel**: `atc:events`

#### **Step 2: Next.js EventBus Subscribes to Redis**

The Next.js EventBus class (`lib/eventBus.ts`) subscribes to Redis on startup:

```typescript
class EventBus {
  private redis: Redis | null;
  private subscribers: Map<EventType, Set<Function>>;
  
  constructor(redis: Redis | null, redisPublisher: Redis | null) {
    this.redis = redis;
    this.subscribers = new Map();
    
    if (this.redis) {
      this.setupSubscriber();
    }
  }
  
  private async setupSubscriber() {
    await this.redis.subscribe('atc:events');
    
    this.redis.on('message', (channel, message) => {
      if (channel === 'atc:events') {
        const eventMessage: EventBusMessage = JSON.parse(message);
        this.notifySubscribers(eventMessage);
      }
    });
  }
  
  subscribe(eventType: EventType, callback: Function): () => void {
    const callbacks = this.subscribers.get(eventType) || new Set();
    callbacks.add(callback);
    this.subscribers.set(eventType, callbacks);
    
    // Return unsubscribe function
    return () => {
      callbacks.delete(callback);
    };
  }
}
```

**Features**:
- **Type-Safe**: Only subscribes to specific event types
- **Multiple Subscribers**: Multiple components can listen to same event
- **Clean Unsubscribe**: Components can unsubscribe on unmount

#### **Step 3: SSE API Route Streams Events to Clients**

The SSE route (`/api/events/stream`) creates a persistent connection and streams events:

```typescript
export async function GET(request: NextRequest) {
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      
      // Subscribe to EventBus
      const handleMessage = (message: any) => {
        const payload = {
          type: message.type,
          data: message.data,
          timestamp: message.timestamp
        };
        
        const data = `data: ${JSON.stringify(payload)}\n\n`;
        controller.enqueue(encoder.encode(data));
      };
      
      const unsubscribe = eventBus.subscribe(
        EVENT_TYPES.AIRCRAFT_POSITION_UPDATED,
        handleMessage
      );
      
      // Cleanup on disconnect
      request.signal?.addEventListener('abort', () => {
        unsubscribe();
        controller.close();
      });
    }
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    }
  });
}
```

**SSE Format**:
```
data: {"type":"aircraft.position_updated","data":{"aircraft":{...},"tick":150}}

data: {"type":"aircraft.position_updated","data":{"aircraft":{...},"tick":151}}

...
```

**Client Connection**:
```typescript
const eventSource = new EventSource('/api/events/stream?type=aircraft.position_updated');
```

#### **Step 4: React Components Receive Updates**

React components subscribe to SSE and update state:

```typescript
export default function RadarDisplay() {
  const [liveAircraft, setLiveAircraft] = useState<Map<string, LiveAircraft>>(new Map());
  
  useEffect(() => {
    // Connect to SSE stream
    const eventSource = new EventSource(
      '/api/events/stream?type=aircraft.position_updated&type=aircraft.created'
    );
    
    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      
      if (payload.type === 'aircraft.position_updated') {
        const aircraft = payload.data.aircraft;
        
        // Update live aircraft state
        setLiveAircraft(prev => {
          const updated = new Map(prev);
          updated.set(aircraft.icao24, {
            id: aircraft.id,
            callsign: aircraft.callsign,
            position: aircraft.position,
            updatedAt: Date.now()
          });
          return updated;
        });
      }
    };
    
    return () => {
      eventSource.close();
    };
  }, []);
  
  // Render aircraft on radar
  return (
    <RadarMap>
      {Array.from(liveAircraft.values()).map(aircraft => (
        <AircraftMarker
          key={aircraft.id}
          position={aircraft.position}
          callsign={aircraft.callsign}
        />
      ))}
    </RadarMap>
  );
}
```

**Key Features**:
- **Real-Time Updates**: UI updates within 50-100ms of engine tick
- **Efficient Rendering**: Only re-renders when aircraft data changes
- **Connection Management**: Automatically reconnects on disconnect
- **Type Filtering**: Subscribes only to relevant event types

### 4.3 Performance Characteristics

**Latency Breakdown**:
- **Engine Tick**: 0-50ms (physics calculation)
- **Redis Publish**: < 1ms (in-memory)
- **EventBus Forward**: < 1ms (local subscription)
- **SSE Stream**: < 10ms (HTTP streaming)
- **React Render**: 10-50ms (depending on aircraft count)
- **Total**: **50-100ms from engine tick to UI update**

**Throughput**:
- **Engine**: 1 update per aircraft per second (1 Hz)
- **Redis**: Handles thousands of messages per second
- **SSE**: Supports hundreds of concurrent connections
- **UI**: Renders 50-100 aircraft smoothly at 60 FPS

**Scalability**:
- **Horizontal Scaling**: Multiple Next.js instances can subscribe to same Redis
- **Load Balancing**: SSE connections distributed across instances
- **Database**: Connection pooling handles concurrent queries

---

## 5. Database Schema & Persistence

### 5.1 Core Tables

#### **aircraft_instances** (Operational State)

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
    flight_plan JSONB,  -- {type: 'ARRIVAL'|'DEPARTURE', origin, destination, runway}
    
    -- Control Fields
    controller VARCHAR(20) DEFAULT 'ENGINE',  -- 'ENGINE' | 'AIR_LLM' | 'GROUND_LLM'
    phase VARCHAR(20) DEFAULT 'CRUISE',  -- 'CRUISE' | 'DESCENT' | 'APPROACH' | 'TAXI'
    status VARCHAR(20) DEFAULT 'active',  -- 'active' | 'landed' | 'departed'
    
    -- Targets (from clearances)
    target_speed_kts INTEGER,
    target_heading_deg INTEGER,
    target_altitude_ft INTEGER,
    vertical_speed_fpm INTEGER,
    
    -- State Tracking
    current_zone VARCHAR(20),  -- 'ENTRY' | 'ENROUTE' | 'APPROACH' | 'RUNWAY'
    distance_to_airport_nm DECIMAL(8,2),
    last_event_fired VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Indexes**:
- `idx_aircraft_instances_controller` - Filter by controller
- `idx_aircraft_instances_phase` - Filter by phase
- `idx_aircraft_instances_status` - Filter by status
- `idx_aircraft_instances_position` - GIN index for JSONB queries

#### **events** (Audit Trail)

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    level VARCHAR(10) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')),
    type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    aircraft_id INTEGER REFERENCES aircraft_instances(id) ON DELETE SET NULL,
    sector VARCHAR(20),
    frequency VARCHAR(10),
    direction VARCHAR(10) CHECK (direction IN ('TX', 'RX', 'CPDLC', 'XFER', 'SYS')),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose**: Complete audit trail of all system events

#### **aircraft_types** (Reference Data)

```sql
CREATE TABLE aircraft_types (
    id SERIAL PRIMARY KEY,
    icao_type VARCHAR(10) UNIQUE NOT NULL,  -- 'A320', 'B738', etc.
    wake VARCHAR(1) NOT NULL,  -- 'L' | 'M' | 'H' | 'J' (Light/Medium/Heavy/Super)
    engines JSONB NOT NULL,  -- {count: 2, type: 'TURBOFAN'}
    dimensions JSONB,  -- {length_ft: 123, wingspan_ft: 117}
    cruise_speed_kts FLOAT NOT NULL,
    max_speed_kts FLOAT NOT NULL,
    ceiling_ft FLOAT NOT NULL,
    climb_rate_fpm FLOAT NOT NULL,
    -- ... more performance characteristics
);
```

**Source**: Populated by `data-pipeline/` from multiple APIs

### 5.2 Batch Operations

The engine uses **batch operations** for efficiency:

```python
# Instead of:
for aircraft in aircraft_list:
    await db.execute("UPDATE aircraft_instances SET position = $1 WHERE id = $2", ...)

# We do:
updates = [
    {'id': 12345, 'position': {...}},
    {'id': 12346, 'position': {...}},
    # ... 50 aircraft
]
await db.executemany("""
    UPDATE aircraft_instances 
    SET position = $2, updated_at = NOW() 
    WHERE id = $1
""", updates)
```

**Performance**: 50x faster for 50 aircraft

---

## 6. Key Features & Capabilities

### 6.1 Real-Time Aircraft Tracking

- **Live Positions**: Updates every second from engine
- **Multi-Aircraft**: Supports 50-100+ concurrent aircraft
- **Sector Awareness**: Automatic zone detection and transitions
- **Phase Tracking**: CRUISE → DESCENT → APPROACH → TAXI → GATE

### 6.2 Airspace Management

- **Multi-Sector**: Entry (60-80 NM), Enroute (10-60 NM), Approach (3-10 NM), Runway (0-3 NM)
- **Boundary Detection**: Automatic sector transitions with hysteresis
- **Entry Fixes**: 8 cardinal/intercardinal entry points
- **Handoff Logic**: Ready for ATC controller integration

### 6.3 Ground Operations

- **Gate Management**: Gate assignment, compatibility rules
- **Taxi Routing**: Taxiway graph, route calculation
- **Runway Operations**: Landing, takeoff, crossing coordination
- **Visualization**: Interactive airport map with OpenStreetMap data

### 6.4 Event System

- **Comprehensive Logging**: All events logged to database
- **Real-Time Distribution**: Redis pub/sub for live updates
- **Filterable Streams**: SSE clients can filter by type, sector, aircraft
- **Audit Trail**: Complete history for debugging and compliance

### 6.5 Performance & Scalability

- **Non-Blocking Architecture**: Async workers handle all I/O
- **Batch Operations**: Database and Redis batching for efficiency
- **Connection Pooling**: Database connections shared across requests
- **Horizontal Scaling**: Multiple Next.js instances supported

---

## 7. Technology Stack

### 7.1 Frontend & API

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type safety and developer experience
- **React 18**: UI library with hooks and concurrent rendering
- **Tailwind CSS**: Utility-first CSS (if used)
- **Leaflet**: Interactive maps for radar display

### 7.2 Backend Engine

- **Python 3.11+**: Core language
- **asyncio**: Asynchronous I/O and concurrency
- **asyncpg**: High-performance PostgreSQL driver
- **redis.asyncio**: Async Redis client
- **Ray** (optional): Distributed computing for physics

### 7.3 Data & Infrastructure

- **PostgreSQL 12+**: Relational database
- **Redis 6+**: Pub/sub event bus
- **Docker** (optional): Containerization
- **Nginx** (optional): Reverse proxy

### 7.4 Data Pipeline

- **Python 3.11+**: Data collection scripts
- **Requests**: HTTP client for APIs
- **Beautiful Soup**: HTML parsing (if needed)
- **Pandas**: Data processing (if needed)

---

## 8. Deployment & Operations

### 8.1 Local Development

```bash
# Start PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:14

# Start Redis
docker run -d -p 6379:6379 redis:7

# Start Engine
cd atc-brain-python
python3 -m engine.core_engine

# Start Next.js
cd atc-nextjs
npm run dev
```

### 8.2 Production Deployment

**Recommended Architecture**:
- **Engine**: Single instance (deterministic, doesn't scale horizontally)
- **Next.js**: Multiple instances behind load balancer
- **PostgreSQL**: Primary-replica setup
- **Redis**: Single instance or cluster (if high throughput)

**Monitoring**:
- **Engine Metrics**: Tick duration, aircraft count, worker queue sizes
- **Database Metrics**: Query latency, connection pool usage
- **Redis Metrics**: Pub/sub throughput, memory usage
- **UI Metrics**: SSE connection count, event processing latency

---

## 9. Future Enhancements

### 9.1 LLM Integration (Planned)

See `ATC_LLM_INTEGRATION_FULL.md` for complete design:
- **Air LLM**: Manages airborne aircraft (STAR selection, vectoring, approach sequencing)
- **Ground LLM**: Manages surface operations (gate assignment, taxi routing)
- **Structured Output**: LLMs output validated JSON clearances
- **Event-Driven**: LLMs react to events, issue clearances, engine executes

### 9.2 Advanced Features

- **Conflict Detection**: Automatic separation violation detection
- **Weather Integration**: Wind, visibility, ceiling effects on operations
- **Scheduling System**: Flight schedule management, slot allocation
- **ML-Based Optimization**: Predictive sequencing, delay minimization

---

## 10. Conclusion

The ATC System is a **production-ready, real-time simulation platform** that demonstrates:

1. **Deterministic Physics**: 1 Hz tick loop with predictable, reproducible results
2. **Non-Blocking Architecture**: Async workers enable efficient I/O handling
3. **Live UI Updates**: Sub-second latency from engine to UI via Redis + SSE
4. **Scalable Design**: Horizontal scaling for frontend, efficient batch operations
5. **Complete Persistence**: PostgreSQL as single source of truth with full audit trail

**Key Achievement**: The system successfully maintains **deterministic physics** while delivering **real-time UI updates** with **production-grade performance**.

---

## Appendix A: File Structure

```
/Users/nrup/ATC-1/
├── atc-nextjs/                    # Next.js frontend + API
│   ├── src/
│   │   ├── app/                   # App Router pages
│   │   │   ├── page.tsx           # Main ATC interface
│   │   │   ├── engine-ops/        # Engine monitoring page
│   │   │   ├── ground/            # Ground operations page
│   │   │   ├── logs/              # Communications log page
│   │   │   └── api/               # API routes
│   │   │       ├── events/
│   │   │       │   └── stream/    # SSE endpoint
│   │   │       ├── aircraft/      # Aircraft REST API
│   │   │       └── airport/       # Airport data API
│   │   ├── components/            # React components
│   │   │   ├── RadarDisplay.tsx   # Live radar display
│   │   │   ├── ATCSystem.tsx      # Main state management
│   │   │   └── ...
│   │   └── lib/                   # Utility libraries
│   │       ├── eventBus.ts        # Redis event bus
│   │       └── database.ts        # PostgreSQL client
│   └── database/
│       └── schema.sql             # Database schema
│
├── atc-brain-python/              # Physics engine
│   ├── engine/
│   │   ├── core_engine.py         # Main engine (1 Hz tick)
│   │   ├── kinematics.py          # Physics calculations
│   │   ├── state_manager.py       # Database integration
│   │   ├── event_publisher.py     # Redis publisher
│   │   ├── airspace.py            # Sector management
│   │   ├── constants.py           # Physical constants
│   │   └── config.py              # Configuration
│   └── airspace/
│       └── yyz_sectors.json       # Sector definitions
│
└── data-pipeline/                 # Data collection
    └── src/                       # Collection scripts
```

---

## Appendix B: Key Constants

```python
# Time Step
DT = 1.0  # seconds - 1 Hz tick rate

# Performance Limits
A_ACC_MAX = 0.6  # kt/s - maximum acceleration
A_DEC_MAX = 0.8  # kt/s - maximum deceleration
PHI_MAX_DEG = 25.0  # degrees - maximum bank angle
H_DOT_CLIMB_MAX = 2500.0  # fpm - maximum climb rate
H_DOT_DESCENT_MAX = 3000.0  # fpm - maximum descent rate

# Sector Boundaries
ENTRY_ZONE_THRESHOLD_NM = 60.0
HANDOFF_READY_THRESHOLD_NM = 20.0
TOUCHDOWN_ALTITUDE_FT = 50.0  # AGL

# Airport Reference (CYYZ)
CYYZ_LAT = 43.6777
CYYZ_LON = -79.6248
CYYZ_ELEVATION_FT = 569.0
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Author**: ATC System Development Team

