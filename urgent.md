# URGENT: ATC-1 Simplification & ML Strategy

## Current State Summary

ATC-1 is an air traffic control simulation with 3 major pieces:
- **Python Engine** (`atc-brain-python/`) - 1 Hz physics tick loop, ~3,000 lines
- **Next.js Frontend** (`atc-nextjs/`) - Radar display, flight strips, maps
- **Data Pipeline** (`data-pipeline/`) - Aircraft/airline reference data generation

Core logic is solid. The physics are correct, the event-driven architecture works. But there's ~30% unnecessary code that makes the system harder to work with.

---

## What's Over-Engineered (Kill List)

### 1. Ray Distributed Computing — REMOVE
**Files:** `kinematics_ray.py`, Ray init code in `core_engine.py`

The engine tries to farm out physics calculations to a remote ASUS cluster via Ray. This is absurd for the workload — basic vector math for 100 aircraft at 1 Hz. A single thread handles this in <1ms. The Ray setup adds connection failures, import guards, and a second physics file that duplicates formulas.

**Action:** Delete `kinematics_ray.py`. Strip all Ray imports and initialization from `core_engine.py`. Use local `kinematics.py` only.

### 2. Three-Tier Async Worker Architecture — SIMPLIFY
**Location:** `core_engine.py` (~400 lines of queue/worker code)

There are 3 separate async workers (db_worker, redis_worker, telemetry_worker) consuming from queues with different batch intervals (1s, 50ms, 10s). For a 1 Hz loop processing 100 aircraft, this is way too much machinery.

**Action:** Replace with a simple end-of-tick pattern:
```
tick():
    update all aircraft positions
    write to DB (single batch UPDATE)
    publish events to Redis
    done
```

### 3. Dead/Bloated Modules — DELETE
| File | Lines | Why Remove |
|------|-------|------------|
| `airspace.py` | 346 | Barely used, sector logic not connected to anything |
| `zone_detector.py` | 65 | Simple if-elif, inline it into the tick loop |
| `kinematics_ray.py` | 48 | Duplicate physics (see #1) |
| Telemetry worker | ~100 | JSONL dumps nobody reads (1000+ orphaned files in git) |

### 4. Frontend Map Redundancy — CONSOLIDATE
Three separate map/display components doing similar things:
- `RadarDisplay.tsx` — aircraft blips on radar
- `GroundMapYYZ.tsx` — Leaflet airport map
- `RunwayDisplay.tsx` — SVG runway view

**Action:** Merge into one `MapView` component with display modes (radar/ground/runway).

### 5. JSONB Overuse in Database
5+ JSONB columns (`position`, `flight_plan`, `notes`, `engines`, `dimensions`). Position data should be flat columns — you query it every single tick.

**Action:** Flatten `position` into `lat`, `lon`, `altitude_ft`, `heading_deg`, `speed_kts` columns. Keep `flight_plan` as JSONB (queried infrequently). Drop `notes`, `engines`, `dimensions` JSONB — promote to columns or remove if unused.

---

## ML Decision System — Current State & What To Do

### How It Works Now

The LLM Dispatcher subscribes to Redis events. When an aircraft crosses a zone boundary, it:
1. Builds a text prompt with aircraft state + nearby traffic
2. Shells out to `ollama run mistral` (Mistral-7B)
3. Parses the JSON response
4. Runs a safety validator (3NM lateral / 1000ft vertical separation)
5. Updates the DB with new targets (altitude, speed, heading)

### Problems With This Approach

1. **Ollama subprocess per decision** — spawns a new process every time. Slow (1-5s), unreliable, no connection pooling.
2. **No feedback loop** — the LLM never learns if its decisions were good or bad. Same mistakes repeat.
3. **Prompt is static** — one prompt template for all situations. No differentiation between a routine descent and a conflict resolution.
4. **Safety validator is a band-aid** — 20 lines of real logic wrapped in 191 lines of code. The LLM should be generating safe clearances, not relying on a post-hoc filter.
5. **No fallback** — if Ollama is down or returns garbage, the aircraft just keeps flying with no guidance.

### Recommended ML Strategy

#### Option A: Rule-Based + LLM Assist (Simplest, Recommended for Now)

Replace the current "LLM decides everything" approach with:

```
Phase-based rule engine (deterministic):
  ENTRY (>50NM)  → assign STAR, descend to FL180, 280kts
  ENROUTE (20-50NM) → follow STAR waypoints, descend to FL120
  APPROACH (<20NM) → intercept ILS, descend 3° glideslope
  FINAL (<5NM) → landing clearance, reduce to Vref
  GROUND → gate assignment, taxi route

LLM override (optional):
  When conflicts detected → ask LLM for vectoring solution
  When unusual situation → ask LLM for creative routing
```

**Why:** 90% of ATC is procedural. Aircraft follow STARs, descend on profile, land on the ILS. The LLM should only intervene when rules can't handle it (conflicts, emergencies, weather deviations).

**Implementation:**
- Create `rule_engine.py` (~200 lines) with phase-based decision tables
- Keep `llm_dispatcher.py` but only invoke it for conflict resolution
- Use Ollama HTTP API (`POST localhost:11434/api/generate`) instead of subprocess
- Add a `clearances` table to track decision quality

#### Option B: Reinforcement Learning (Future, If You Want True ML)

Train a model to optimize for:
- **Reward:** safe separation maintained + fuel efficiency + on-time arrival
- **State:** all aircraft positions, speeds, altitudes, zones
- **Action:** target altitude, speed, heading for each aircraft

Stack:
- Use the existing physics engine as the RL environment
- Stable Baselines3 (PPO or SAC) for the policy
- Train offline on recorded scenarios, fine-tune online

**Timeline:** This is a multi-month project. Get Option A working first.

#### Option C: Hybrid (Best Long-Term)

1. Rule engine handles standard operations (Option A)
2. RL model handles conflict resolution and optimization
3. LLM generates natural language radio communications
4. Safety validator remains as final gate

---

## Simplified Architecture (Target)

```
┌──────────────────────────────────────────────┐
│              Next.js Frontend                  │
│  (RadarView + FlightStrips + Communications)  │
└──────────────────┬───────────────────────────┘
                   │ Redis pub/sub
┌──────────────────▼───────────────────────────┐
│              Python Engine                     │
│                                                │
│  tick() every 1s:                              │
│    1. Fetch active aircraft                    │
│    2. Update positions (kinematics.py)         │
│    3. Detect zone changes                      │
│    4. Rule engine assigns clearances           │
│    5. (Optional) LLM resolves conflicts        │
│    6. Safety validator checks all              │
│    7. Batch write to PostgreSQL                │
│    8. Publish events to Redis                  │
│                                                │
│  Single process. No Ray. No async workers.     │
└──────────────────┬───────────────────────────┘
                   │
            ┌──────▼──────┐
            │  PostgreSQL  │
            │  + Redis     │
            └─────────────┘
```

**What changes:**
- Engine becomes a single synchronous loop (no worker queues)
- Rule engine replaces LLM for routine decisions
- LLM only called for conflicts (saves 90% of Ollama calls)
- Remove Ray, remove telemetry worker, remove dead modules
- Flatten DB position columns for faster queries

**What stays the same:**
- Physics formulas (kinematics.py) — they're correct
- Redis event bus — works well for frontend updates
- PostgreSQL schema (mostly) — just flatten position
- Frontend components — just consolidate maps
- Data pipeline — untouched

---

## Execution Order

### Phase 1: Strip Complexity (Do This First)
- [ ] Delete `kinematics_ray.py` and all Ray imports
- [ ] Delete `airspace.py` (unused)
- [ ] Inline `zone_detector.py` into tick loop
- [ ] Remove telemetry worker and phaseA/ dumps
- [ ] Replace 3 async workers with synchronous end-of-tick writes
- [ ] Clean up 15+ doc files → keep only README.md + this file

### Phase 2: Rule Engine
- [ ] Create `rule_engine.py` with phase-based decision tables
- [ ] Wire it into the tick loop (after zone detection)
- [ ] Keep LLM dispatcher but only call it for separation conflicts
- [ ] Switch Ollama from subprocess to HTTP API
- [ ] Add `clearances` table for audit trail

### Phase 3: Frontend Cleanup
- [ ] Merge map components into single `MapView`
- [ ] Either use Zustand properly or remove the dependency
- [ ] Flatten position JSONB → individual columns
- [ ] Update API routes to use flat columns

### Phase 4: ML Enhancement (Optional, Later)
- [ ] Add decision quality metrics (separation maintained, fuel used)
- [ ] Record scenarios for RL training data
- [ ] Experiment with RL for conflict resolution
- [ ] Add LLM-generated radio communications

---

## File Count After Simplification

**Before:** ~25 Python files, ~15 TS components, ~15 docs
**After:** ~15 Python files, ~10 TS components, ~3 docs

Core logic stays. Wrapper complexity goes. System becomes debuggable by one person.
