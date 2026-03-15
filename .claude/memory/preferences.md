# User Preferences

## Communication Style
- Short, direct responses — no filler, no preamble
- No emojis
- Answer in chat for explanations; only write code when implementing
- Don't over-engineer — minimum complexity for current task
- Don't add docstrings/comments to unchanged code

## Workflow
- Read files before modifying; understand existing patterns first
- Prefer Edit over Write for existing files
- Parallel tool calls when independent
- Commit only when explicitly asked
- Ask before destructive git operations

## Code Style (Python)
- asyncio/asyncpg throughout the backend
- JSONB columns need `::jsonb` cast in asyncpg queries
- Lazy imports to avoid circular import issues (see rule_engine.py `_get_ils()`)
- No backwards-compat shims; just change the code

## Code Style (TypeScript / Next.js)
- `'use client'` components
- Inline styles with dark ATC theme: `#0a1628` bg, `#00ff9d` accent, monospace font
- postMessage for iframe communication (RadarDisplay ↔ radar-map.html)

## ATC Simulation Philosophy
- Realism matters: proper ILS geometry, glideslope, real CYYZ coordinates
- Safety layers should be independent (don't rely on LLM alone)
- Deterministic rule engine handles standard cases; LLM only for complex/ambiguous

## Database
- PostgreSQL via asyncpg
- Redis for pub/sub and key-value (runway selection, events)
- Migrations in `scripts/migrate_db_vN.py`; run manually

## Memory System
- Files live at `/Users/nrup/ATC-1/.claude/memory/` — visible in IDE, local to project
- Update MEMORY.md after significant architectural changes
- Keep MEMORY.md under 200 lines (index only); details in category files
- decisions.md: rationale for non-obvious choices
- preferences.md: this file
- user.md: user context
- people.md: team/collaborators
