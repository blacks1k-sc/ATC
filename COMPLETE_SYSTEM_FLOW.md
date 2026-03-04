# Complete ATC System Flow with Mistral-7B LLM Integration

## 🎯 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATC-1 System Components                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Next.js UI   │    │ Python Engine│    │ LLM Dispatcher│   │
│  │  (Port 3000)  │    │  (Background)│    │  (Background) │   │
│  └──────┬────────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                     │                    │            │
│         │                     │                    │            │
│         └─────────────────────┴────────────────────┘            │
│                           │                                        │
│                           ▼                                        │
│              ┌────────────────────────┐                            │
│              │  PostgreSQL + Redis    │                            │
│              │  (Port 5432) (6379)    │                            │
│              └────────────────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Complete Flow: From Aircraft Creation to LLM Decisions

### **Phase 1: System Initialization**

#### Step 1: Start Infrastructure Services
```bash
# Terminal 1: Start PostgreSQL (if not running)
brew services start postgresql  # macOS
# or
sudo systemctl start postgresql  # Linux

# Terminal 2: Start Redis (if not running)
brew services start redis  # macOS
# or
sudo systemctl start redis  # Linux
```

**What happens:**
- PostgreSQL database `atc_system` is ready
- Redis server listening on port 6379
- Both services are persistent and run in background

---

#### Step 2: Start Python Engine
```bash
cd /Users/nrup/ATC-1/atc-brain-python
python -m engine.core_engine
# or
./scripts/start_engine.sh
```

**What happens:**
1. Engine initializes:
   - Connects to PostgreSQL database
   - Connects to Redis
   - Initializes `EventPublisher` for Redis events
   - Starts `SpawnListener` to listen for new aircraft
   - Loads active aircraft from database

2. Engine starts main loop:
   - **Tick loop runs at 1 Hz** (1 second per tick)
   - Each tick:
     - Updates all active aircraft positions (physics simulation)
     - Checks for zone boundary crossings
     - Checks for clearance completions
     - Publishes events to Redis
     - Updates database with new positions

3. Engine listens for:
   - `aircraft.created` events from Redis
   - When received, assigns `controller: "ENGINE"` to new arrivals

**Engine Status:**
```
Starting engine tick loop (1 Hz, dt=1.0s)
Running indefinitely (Ctrl+C to stop)
```

---

#### Step 3: Start LLM Dispatcher (NEW!)
```bash
cd /Users/nrup/ATC-1/atc-brain-python
python launch_llm.py
```

**What happens:**
1. LLM Dispatcher initializes:
   - Verifies Ollama is installed with Mistral model
   - Connects to PostgreSQL database
   - Connects to Redis
   - Initializes `SafetyValidator`
   - Initializes `AirLLMClient` and `GroundLLMClient`
   - Initializes `ContextBuilder` and `DecisionRouter`

2. LLM Dispatcher subscribes to Redis:
   - Channel: `atc:events`
   - Event types:
     - `zone.boundary_crossed` → Triggers Air LLM
     - `clearance.completed` → Triggers Air LLM
     - `runway.landed` → Triggers Ground LLM
     - `runway.vacated` → Triggers Ground LLM

3. Event processor starts:
   - Background task processes events from queue
   - Each event triggers LLM decision generation

**LLM Dispatcher Status:**
```
✓ Ollama installed with Mistral model
Connected to Redis on channel 'atc:events'
Connected to PostgreSQL database
LLM Dispatcher initialized with Mistral-7B via Ollama
Listening for events: zone.boundary_crossed, clearance.completed, runway.landed, runway.vacated
```

---

#### Step 4: Start Next.js Frontend
```bash
cd /Users/nrup/ATC-1/atc-nextjs
npm run dev
```

**What happens:**
- Next.js server starts on `http://localhost:3000`
- Frontend connects to PostgreSQL for data
- Frontend subscribes to Redis for real-time updates
- UI displays aircraft positions, flight strips, etc.

---

### **Phase 2: Aircraft Creation**

#### Step 5: Generate Aircraft via UI

**User Action:**
1. Open browser: `http://localhost:3000`
2. Click "Generate Aircraft" button
3. Select aircraft type (e.g., "A320") and airline (e.g., "UAL-United Airlines")
4. Click "Create"

**What happens:**

1. **Next.js API Route** (`/api/aircraft/generate`):
   - Generates unique identifiers:
     - `icao24`: 6-digit hex code
     - `callsign`: e.g., "UAL123"
     - `registration`: e.g., "N12345"
   - Generates realistic position:
     - Random lat/lon (far from airport)
     - Altitude: 10,000-40,000 ft
     - Speed: 250-500 kts
     - Heading: towards airport
     - Distance: 50-250 NM from airport
   - Calculates initial sector/zone based on distance
   - Creates aircraft record in PostgreSQL:
     ```sql
     INSERT INTO aircraft_instances (
       icao24, registration, callsign, aircraft_type_id, airline_id,
       position, status, flight_type, controller, phase, distance_to_airport_nm
     ) VALUES (...)
     ```
   - Creates event record in `events` table
   - Publishes to Redis:
     ```javascript
     await eventBus.publishAircraftCreated(aircraft)
     // Publishes: { type: "aircraft.created", data: { aircraft } }
     ```

2. **Engine SpawnListener receives event:**
   - Listens for `aircraft.created` on Redis
   - If `flight_type == "ARRIVAL"`:
     - Updates aircraft: `controller = "ENGINE"`
     - Updates aircraft: `phase = "CRUISE"`
     - Aircraft is now under engine control

3. **Engine picks up aircraft:**
   - On next tick, engine loads aircraft from database
   - Aircraft appears in engine's active aircraft list
   - Engine starts updating position every tick

---

### **Phase 3: Engine Tick Loop (Continuous)**

#### Step 6: Engine Updates Aircraft (Every 1 Second)

**Engine Tick Process:**

1. **Physics Update:**
   - For each active aircraft:
     - Updates position based on current heading/speed
     - Applies target altitude/speed/heading if set
     - Calculates distance to airport
     - Updates `current_zone` based on distance:
       - `ENTRY`: >50 NM
       - `ENROUTE_50`: 20-50 NM
       - `ENROUTE_20`: 5-20 NM
       - `APPROACH_5`: <5 NM
       - `RUNWAY`: On runway

2. **Event Detection:**
   - Checks if aircraft crossed zone boundary:
     - If `current_zone` changed → **Publishes `zone.boundary_crossed`**
   - Checks if clearance completed:
     - If target altitude/speed/heading reached → **Publishes `clearance.completed`**
   - Checks if aircraft landed:
     - If on runway and speed < 50 kts → **Publishes `runway.landed`**
   - Checks if aircraft vacated runway:
     - If left runway → **Publishes `runway.vacated`**

3. **Redis Publishing:**
   - Batches events every 20-50ms
   - Publishes to `atc:events` channel:
     ```json
     {
       "type": "zone.boundary_crossed",
       "timestamp": "2025-11-22T10:00:00Z",
       "data": {
         "aircraft_id": 123,
         "old_zone": "ENROUTE_50",
         "new_zone": "ENROUTE_20",
         "aircraft": { ... }
       }
     }
     ```

4. **Database Update:**
   - Updates `aircraft_instances` table with new position
   - Updates `distance_to_airport_nm`
   - Updates `current_zone`

---

### **Phase 4: LLM Decision Generation (NEW!)**

#### Step 7: LLM Dispatcher Receives Event

**Event Flow:**

1. **LLM Dispatcher receives event from Redis:**
   ```
   Event: zone.boundary_crossed
   Aircraft ID: 123
   New Zone: ENROUTE_20
   ```

2. **Context Building:**
   - `ContextBuilder.build_aircraft_context()`:
     - Fetches aircraft full state from database
     - Fetches nearby aircraft in same zone
     - Fetches active clearances
     - Builds context dictionary:
       ```python
       {
         "aircraft_id": 123,
         "event_type": "zone.boundary_crossed",
         "current_zone": "ENROUTE_20",
         "aircraft": {
           "callsign": "UAL123",
           "altitude_ft": 12000,
           "speed_kts": 280,
           "heading": 90,
           "distance_to_airport_nm": 15.5
         },
         "current_zone_aircraft": [
           {"callsign": "AAL456", "distance_nm": 14.2},
           {"callsign": "DAL789", "distance_nm": 16.8}
         ],
         "active_clearances": [...]
       }
       ```

3. **Prompt Generation:**
   - `build_air_prompt(context)` creates instruction:
     ```
     You are an Air Traffic Controller managing airborne aircraft.
     
     AIRCRAFT: UAL123
     CURRENT STATE:
     - Zone: ENROUTE_20
     - Position: 12000ft, 280kts, heading 90°
     - Distance to airport: 15.5NM
     - Nearby aircraft in zone: AAL456: 14.2NM; DAL789: 16.8NM
     
     HARD RULES (NEVER VIOLATE):
     1. Maintain minimum 3NM lateral OR 1000ft vertical separation
     2. Only ONE aircraft may occupy a runway at any time
     3. Do NOT invent waypoints, gates, or runways
     4. Output MUST be valid JSON only
     
     REQUIRED OUTPUT SCHEMA:
     {
       "action_type": "string",
       "target_altitude_ft": integer or null,
       "target_speed_kts": integer or null,
       "target_heading_deg": integer or null,
       "waypoints": array or null,
       "runway": "string" or null
     }
     
     Generate clearance JSON now:
     ```

4. **LLM Call:**
   - `AirLLMClient._call_ollama(prompt)`:
     - Runs: `ollama run mistral` (async subprocess)
     - Sends prompt via stdin
     - Waits for response (1-5 seconds)
     - Receives JSON output:
       ```json
       {
         "action_type": "VECTORING",
         "target_altitude_ft": 10000,
         "target_speed_kts": 250,
         "target_heading_deg": 85,
         "waypoints": null,
         "runway": null
       }
       ```

5. **JSON Parsing:**
   - Safely parses JSON (handles markdown code blocks)
   - If invalid, retries once with "fix JSON only" prompt
   - If still invalid, uses fallback decision

6. **Safety Validation:**
   - `SafetyValidator.validate_air_clearance()`:
     - Checks separation with nearby aircraft:
       - Lateral: >= 3NM OR Vertical: >= 1000ft
     - Checks runway exclusivity
     - Returns `True` if safe, `False` if violation

7. **Decision Application:**
   - If validated:
     - `DecisionRouter.apply_decision()`:
       - Updates database:
         ```sql
         UPDATE aircraft_instances
         SET target_altitude_ft = 10000,
             target_speed_kts = 250,
             target_heading_deg = 85,
             updated_at = NOW()
         WHERE id = 123
         ```
       - Stores clearance in `clearances` table
       - Logs: `Applied validated clearance to aircraft 123: VECTORING`
   - If NOT validated:
     - Skips database update
     - Stores failed clearance for audit
     - Logs: `Skipping database write: clearance did not pass validation`

8. **Engine Applies Clearance:**
   - On next tick, engine reads `target_altitude_ft`, `target_speed_kts`, `target_heading_deg`
   - Gradually adjusts aircraft to match targets
   - When targets reached, publishes `clearance.completed` → Triggers next LLM decision

---

### **Phase 5: Ground Operations**

#### Step 8: Aircraft Lands

**Event Flow:**

1. **Engine detects landing:**
   - Aircraft on runway, speed < 50 kts
   - Publishes: `runway.landed`

2. **LLM Dispatcher receives event:**
   - Calls `GroundLLMClient.generate_decision()`
   - Builds ground prompt:
     ```
     You are a Ground Controller managing surface aircraft operations.
     
     AIRCRAFT: UAL123
     EVENT: runway.landed
     PHASE: ROLLOUT
     
     HARD RULES:
     1. Each gate can only be assigned to ONE aircraft at a time
     2. Taxi routes must NOT conflict with active aircraft
     3. Do NOT invent gates, taxiways, or runways
     4. Output MUST be valid JSON only
     
     REQUIRED OUTPUT SCHEMA:
     {
       "action_type": "string",
       "assigned_gate": "string" or null,
       "taxi_route": array or null,
       "runway": "string" or null
     }
     ```

3. **LLM generates ground clearance:**
   ```json
   {
     "action_type": "GATE_ASSIGNMENT",
     "assigned_gate": "C32",
     "taxi_route": null,
     "runway": null
   }
   ```

4. **Validation:**
   - Checks gate availability
   - Checks taxi route conflicts
   - If validated, updates database

5. **Aircraft vacates runway:**
   - Engine detects runway vacated
   - Publishes: `runway.vacated`

6. **LLM generates taxi clearance:**
   ```json
   {
     "action_type": "TAXI_CLEARANCE",
     "assigned_gate": null,
     "taxi_route": ["A1", "A", "B", "C", "C32"],
     "runway": null
   }
   ```

7. **Aircraft taxis to gate:**
   - Engine follows taxi route
   - Updates position on ground

---

## 🔄 Complete Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Complete Event Flow                           │
└─────────────────────────────────────────────────────────────────┘

1. USER CREATES AIRCRAFT (Next.js UI)
   │
   ├─► POST /api/aircraft/generate
   │   ├─► Creates aircraft in PostgreSQL
   │   └─► Publishes: aircraft.created → Redis
   │
   ▼
2. ENGINE SPAWN LISTENER
   │
   ├─► Receives: aircraft.created
   │   └─► Sets controller = "ENGINE"
   │
   ▼
3. ENGINE TICK LOOP (Every 1 second)
   │
   ├─► Updates aircraft position (physics)
   │   ├─► Checks zone boundary crossing
   │   │   └─► Publishes: zone.boundary_crossed → Redis
   │   │
   │   ├─► Checks clearance completion
   │   │   └─► Publishes: clearance.completed → Redis
   │   │
   │   ├─► Checks landing
   │   │   └─► Publishes: runway.landed → Redis
   │   │
   │   └─► Checks runway vacated
   │       └─► Publishes: runway.vacated → Redis
   │
   ▼
4. LLM DISPATCHER
   │
   ├─► Receives event from Redis
   │   │
   │   ├─► zone.boundary_crossed → Air LLM
   │   ├─► clearance.completed → Air LLM
   │   ├─► runway.landed → Ground LLM
   │   └─► runway.vacated → Ground LLM
   │
   ├─► Builds context (database query)
   ├─► Generates prompt
   ├─► Calls Mistral-7B via Ollama
   ├─► Parses JSON response
   ├─► Validates safety (SafetyValidator)
   │
   └─► If validated:
       └─► Updates database (target_altitude_ft, target_speed_kts, etc.)
   │
   ▼
5. ENGINE APPLIES CLEARANCE (Next tick)
   │
   ├─► Reads target_altitude_ft, target_speed_kts, target_heading_deg
   ├─► Gradually adjusts aircraft
   └─► When reached → Publishes: clearance.completed → Redis
       │
       └─► Loop back to step 4
```

---

## 📊 Timeline Example

**Time 0:00** - System starts
- Engine running
- LLM Dispatcher running
- Next.js UI running

**Time 0:05** - User creates aircraft
- Aircraft UAL123 created at 200 NM, 35,000 ft
- Engine picks up aircraft
- Aircraft starts moving towards airport

**Time 0:50** - Aircraft crosses 50 NM boundary
- Engine publishes: `zone.boundary_crossed` (ENTRY → ENROUTE_50)
- LLM Dispatcher receives event
- LLM generates: `target_altitude_ft: 30000, target_speed_kts: 320`
- Validated and applied
- Engine adjusts aircraft

**Time 1:30** - Aircraft crosses 20 NM boundary
- Engine publishes: `zone.boundary_crossed` (ENROUTE_50 → ENROUTE_20)
- LLM generates: `target_altitude_ft: 10000, target_speed_kts: 250`
- Validated and applied

**Time 2:15** - Aircraft crosses 5 NM boundary
- Engine publishes: `zone.boundary_crossed` (ENROUTE_20 → APPROACH_5)
- LLM generates: `target_altitude_ft: 3000, target_heading_deg: 85`
- Validated and applied

**Time 2:45** - Aircraft lands
- Engine publishes: `runway.landed`
- Ground LLM generates: `assigned_gate: "C32"`
- Validated and applied

**Time 2:50** - Aircraft vacates runway
- Engine publishes: `runway.vacated`
- Ground LLM generates: `taxi_route: ["A1", "A", "B", "C", "C32"]`
- Validated and applied
- Aircraft taxis to gate

---

## 🚀 Quick Start Commands

### Terminal 1: PostgreSQL & Redis (if not running)
```bash
# Check if running
pg_isready
redis-cli ping

# Start if needed
brew services start postgresql
brew services start redis
```

### Terminal 2: Python Engine
```bash
cd /Users/nrup/ATC-1/atc-brain-python
python -m engine.core_engine
```

### Terminal 3: LLM Dispatcher
```bash
cd /Users/nrup/ATC-1/atc-brain-python
python launch_llm.py
```

### Terminal 4: Next.js Frontend
```bash
cd /Users/nrup/ATC-1/atc-nextjs
npm run dev
```

### Browser
```
http://localhost:3000
```

---

## ✅ Verification Checklist

- [ ] PostgreSQL running (port 5432)
- [ ] Redis running (port 6379)
- [ ] Engine running (tick loop active)
- [ ] LLM Dispatcher running (subscribed to Redis)
- [ ] Next.js frontend running (port 3000)
- [ ] Ollama installed with Mistral model
- [ ] Can create aircraft via UI
- [ ] Aircraft appears in engine
- [ ] Events published to Redis
- [ ] LLM Dispatcher receives events
- [ ] LLM generates clearances
- [ ] Clearances validated
- [ ] Database updated with targets
- [ ] Aircraft follows clearances

---

## 📝 Summary

**Complete Flow:**
1. **Start services** (PostgreSQL, Redis, Engine, LLM Dispatcher, Next.js)
2. **Create aircraft** via UI → Stored in database → Published to Redis
3. **Engine picks up** aircraft → Updates position every tick
4. **Engine publishes events** when boundaries crossed or clearances completed
5. **LLM Dispatcher receives** events → Calls Mistral-7B → Validates → Updates database
6. **Engine applies** clearances → Aircraft follows targets → Loop continues

**Key Points:**
- Engine runs at 1 Hz (1 tick per second)
- LLM calls are async (don't block engine)
- Only validated clearances update aircraft state
- All clearances (validated and failed) are logged
- System is event-driven and scalable

The Mistral-7B integration seamlessly fits into the existing event-driven architecture! 🎉

