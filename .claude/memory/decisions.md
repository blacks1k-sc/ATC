# Architectural Decisions

## LLM Layer (2025-11)
- **Replaced**: Per-aircraft Ollama subprocess calls (parallel, no shared state)
- **With**: Two-tier controller — RuleEngine (deterministic) + QwenClient (single batch call every 10s)
- **Why**: Old system caused duplicate runway/gate assignment, 10 parallel processes, fake safety validation

## ILS Approach Routing (2026-03)
- **Replaced**: "Magnet" behavior (aircraft fly directly to CYYZ center lat/lon)
- **With**: `apply_waypoint_guided_physics()` — steers toward ENTRY→INTERCEPT→FAF→THRESHOLD waypoints
- **Why**: Unrealistic; no proper final approach; no separation on final
- **Waypoint stagger**: queue_position × 5 NM extra intercept distance (base 20 NM from threshold)
- **Glideslope**: 3° — `CYYZ_ELEVATION_FT + tan(3°) × distance_nm × 6076` — computed live each tick for THRESHOLD/FAF
- **Flat-earth approximation** used throughout (< 200 NM, sufficient precision)

## Resource Contention
- `asyncio.Lock` in ResourceRegistry prevents duplicate runway assignment even if LLM hallucinates
- Validated post-LLM response: `_validate(decision)` checks live registry before `_apply()`

## DB Updates (JSONB)
- `waypoint_sequence` must use `::jsonb` cast in all asyncpg queries (parameterized $N::jsonb)
- `batch_update_aircraft_states` uses 9-tuple: added waypoint_seq_json as param 9

## Frontend ↔ Backend Runway Sync
- Redis key `atc:active_runway` as shared state
- Frontend: `RunwaySelector.tsx` → POST `/api/runway` → `redis.set('atc:active_runway', runway)`
- Backend: `planning_cycle._cycle()` reads `redis_client.get("atc:active_runway")` at start of each cycle

## RunwaySelector UI Issue (known)
- Currently shows 10 designators (both ends); user noted CYYZ has 5 runways
- Should be restructured to show 5 pairs (06L/24R etc.) and let user pick active end
- NOT yet fixed — pending improvement

## Ollama Model Choice
- `qwen2.5:7b` (replaced mistral)
- Accessed via HTTP `http://localhost:11434/api/chat` (not subprocess)
- Persistent `aiohttp.ClientSession` in QwenClient

## Safety Layers (5 total)
1. ResourceRegistry asyncio.Lock (primary gate)
2. Separation conflict detection O(N²), injected into LLM prompt
3. Rule engine FCFS approach sequencing
4. Runway hold-short via registry occupancy
5. 10s re-evaluation cycle catches physics overshoot

## Event Architecture
- Engine publishes: `zone_crossed`, `runway_landed`, `runway_vacated` → Redis `atc:events`
- RegistryEventSubscriber consumes events → updates ResourceRegistry
- `runway.landed` → `assign_runway()`, `runway.vacated` → `release_runway()`
