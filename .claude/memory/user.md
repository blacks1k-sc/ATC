# User Context

## Identity
- Username: nrup (macOS login)
- Working on: ATC-1 — a realistic Air Traffic Control simulation for CYYZ (Toronto Pearson)

## Project Goals
- Realistic multi-aircraft ATC simulation
- Physics-based aircraft movement (bank-limited turns, glideslope descent)
- Proper ILS approach routing (not "magnet" behavior)
- LLM-assisted ATC decisions (Qwen2.5-7B via Ollama) for complex cases
- Rule-based deterministic decisions for standard cases
- No runway/gate conflicts (ResourceRegistry with asyncio.Lock)
- Frontend: Next.js radar display + real-time aircraft positions via Redis pub/sub

## Technical Environment
- macOS (darwin 25.2.0)
- Python 3.11 / 3.13 (both present)
- Node.js + Next.js for frontend
- PostgreSQL + Redis (local)
- Ollama running locally at localhost:11434
- Shell: zsh

## Active Branch
- `llm-event-hooks` (feature work)
- `main` (stable, receives merges)

## Known Pending Items
- RunwaySelector: restructure to show 5 runway pairs instead of 10 designators
- Taxiway segment registry (planned in original design, not yet implemented)
