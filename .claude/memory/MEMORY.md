# Session Memory Index

> Auto-loaded at session start. Lines after 200 are truncated — keep concise.
> Detail files: decisions.md, preferences.md, user.md, people.md

## Project: ATC-1 (Air Traffic Control Simulation)

### Repos
- `/Users/nrup/ATC-1/atc-brain-python` — Python simulation engine (main branch: `main`)
- `/Users/nrup/ATC-1/atc-nextjs` — Next.js frontend
- Primary working dir: `/Users/nrup/ATC-1/atc-brain-python`
- Current branch: `llm-event-hooks` (code lives on `main` after merges)

### Architecture (as of 2026-03-14)
- **Engine** (`engine/core_engine.py`): 1 Hz tick, physics, event detection, publishes to Redis `atc:events`
- **StateManager** (`engine/state_manager.py`): asyncpg DB reads/writes, handles `waypoint_sequence JSONB`
- **Kinematics** (`engine/kinematics.py`): `apply_waypoint_guided_physics()` → replaces old magnet behavior
- **ILS Geometry** (`engine/ils_geometry.py`): CYYZ runway coords, waypoint sequence computation, glideslope
- **ResourceRegistry** (`llm/resource_registry.py`): asyncio.Lock, runway/gate occupancy, approach queue
- **RuleEngine** (`llm/rule_engine.py`): deterministic tier; CASE 0 assigns ILS waypoints
- **QwenClient** (`llm/qwen_client.py`): single aiohttp session to Ollama `qwen2.5:7b`
- **PlanningCycle** (`llm/planning_cycle.py`): 10s loop, reads `atc:active_runway` from Redis
- **launch_llm.py**: wires all components, passes `redis_client` to PlanningCycle
- **Frontend**: `RunwaySelector.tsx` → modal → POSTs to `/api/runway` → Redis → backend reads it

### DB Schema (PostgreSQL)
- `aircraft_instances`: includes `runway_assigned`, `gate_assigned`, `clearance_seq`, `waypoint_sequence JSONB`
- `clearances`: id, aircraft_id, issued_at, cleared_*, status (ACTIVE|COMPLETED|CANCELLED)
- Migrations run: v1, v2, v3 (waypoint_sequence added)

### CYYZ Specifics
- **5 physical runways** × 2 ends = 10 designators: 06L/24R, 06R/24L, 15L/33R, 15R/33L, 05/23
- Prevailing wind 230° → prefer 23 for arrivals
- `atc:active_runway` Redis key: frontend sets, planning cycle reads

### Key Design Decisions
→ See decisions.md for full rationale

### User Preferences
→ See preferences.md

---
*Updated: 2026-03-14*
