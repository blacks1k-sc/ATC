# ATC-1 — Claude Instructions

## Session Start Protocol
At the start of every session, read these memory files (in order):
1. `/Users/nrup/ATC-1/.claude/memory/MEMORY.md` — architecture index
2. `/Users/nrup/ATC-1/.claude/memory/decisions.md` — design rationale
3. `/Users/nrup/ATC-1/.claude/memory/preferences.md` — code/workflow preferences
4. `/Users/nrup/ATC-1/.claude/memory/user.md` — user context
5. `/Users/nrup/ATC-1/.claude/memory/people.md` — collaborators

Do NOT re-read these mid-session unless something seems inconsistent.

## Decision Logging Protocol
Whenever the user describes a decision they are making:
1. Append a row to `/Users/nrup/ATC-1/.claude/decisions.csv`
2. Columns: `date,decision,reasoning,expected_outcome,changes_made`
3. `date` = today's date (YYYY-MM-DD)
4. `changes_made` = fill in after implementation is done; leave blank if decision is just being recorded
5. If the decision changes architecture or preferences, also update the relevant memory file

CSV lives at: `/Users/nrup/ATC-1/.claude/decisions.csv`

## Session End / Compaction Protocol
When a session ends or `/compact` is triggered:
- Update `MEMORY.md` with any new architecture, files, or key facts
- Update `decisions.csv` with `changes_made` for any decisions implemented this session
- Update `preferences.md` if new code style patterns emerged
- Update `user.md` if new pending items or goals were stated

Only update what changed. Do not duplicate existing entries.

---

## Project Overview
ATC simulation for CYYZ (Toronto Pearson). Two repos:
- `atc-brain-python/` — Python engine (asyncio, asyncpg, Redis, Ollama)
- `atc-nextjs/` — Next.js radar frontend

## Architecture (high-level)
```
Engine (1Hz) → Redis events → ResourceRegistry
                ↓
           PlanningCycle (10s)
           RuleEngine (deterministic) → standard cases
           QwenClient (qwen2.5:7b)  → complex cases
                ↓
           DB writes (target_altitude, waypoint_sequence, etc.)
                ↓
           Engine reads targets next tick
```

## Key Files
| File | Role |
|------|------|
| `engine/core_engine.py` | Main 1Hz loop, physics, event emission, waypoint advancement |
| `engine/kinematics.py` | Physics — `apply_waypoint_guided_physics()` is the primary function |
| `engine/ils_geometry.py` | CYYZ runway coords, ILS waypoint computation, glideslope |
| `engine/state_manager.py` | asyncpg DB layer — reads `waypoint_sequence JSONB` |
| `engine/airport_data.py` | Runway polygon computation |
| `llm/resource_registry.py` | Runway/gate occupancy with asyncio.Lock |
| `llm/rule_engine.py` | Tier-1 decisions; CASE 0 = assign ILS waypoints |
| `llm/qwen_client.py` | Tier-2 LLM via aiohttp to Ollama |
| `llm/planning_cycle.py` | 10s orchestration loop |
| `launch_llm.py` | Entry point — wires all components |
| `scripts/migrate_db_v*.py` | DB migrations (run manually) |
| `atc-nextjs/src/components/RunwaySelector.tsx` | Pre-sim modal for runway selection |
| `atc-nextjs/src/components/RadarDisplay.tsx` | iframe wrapper, sends postMessage to radar |
| `atc-nextjs/public/radar-map.html` | Leaflet radar map, draws ILS centerline |
| `atc-nextjs/src/app/api/runway/route.ts` | API: GET/POST active runway ↔ Redis |

## Critical Constraints
- **asyncpg JSONB**: Always use `$N::jsonb` cast for JSONB parameters
- **asyncio.Lock in ResourceRegistry**: Never bypass; it prevents duplicate runway assignment
- **5 physical runways at CYYZ**: 06L/24R, 06R/24L, 15L/33R, 15R/33L, 05/23 (10 designators total)
- **Redis key `atc:active_runway`**: Frontend writes, planning cycle reads — do not hardcode runway
- **Waypoint sequence stagger**: `queue_position × 5 NM` at intercept to prevent final-approach conflicts
- **Flat-earth approximation**: Used for all distance/bearing math (< 200 NM, acceptable precision)

## DB Migrations Run
- v1: runway_assigned, gate_assigned, clearance_seq columns
- v2: clearances table
- v3: waypoint_sequence JSONB column ✓ (run 2026-03-14)

## Pending Work
- RunwaySelector: show 5 runway pairs (06L/24R) instead of 10 individual designators
- Taxiway segment registry (planned in original design, not yet implemented)

## Don't Do
- Don't use subprocess to call Ollama — use QwenClient (aiohttp)
- Don't skip the ResourceRegistry lock
- Don't hardcode airport as "CYYZ center" for aircraft targeting — use waypoints
- Don't commit without being asked
- Don't add docstrings/comments to code you didn't change
