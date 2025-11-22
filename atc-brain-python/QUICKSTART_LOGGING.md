# Quick Start: Engine Logging

## TL;DR

The engine now runs **silently by default** with clean console output. All data flows (Redis, Postgres, telemetry) continue working normally.

## Run Silent Mode (Default)
```bash
cd atc-brain-python
python -m engine
```
**Output**: Clean startup/shutdown messages only ✨

## Run Debug Mode (Verbose)
```bash
cd atc-brain-python
DEBUG_PRINTS=true python -m engine
```
**Output**: All threshold events, per-aircraft logs, full details 📊

## Environment Variables

Create a `.env` file in `atc-brain-python/` directory:

```bash
# Silent mode (default)
DEBUG_PRINTS=false

# Verbose mode
DEBUG_PRINTS=true

# Custom telemetry directory
TELEMETRY_DIR=./telemetry/phaseA
```

## What Changed?

### Before (Flooded Console) 🔴
```
🛬 TOUCHDOWN: ABC123 at 15 ft AGL
🤝 HANDOFF_READY: DEF456 at 25.3 NM
📍 ENTERED_ENTRY_ZONE: GHI789 at 48.7 NM
[... hundreds of lines per minute ...]
```

### After (Clean Console) ✅
```
🚀 Initializing Kinematics Engine...
✅ Kinematics Engine initialized
🏁 Starting engine tick loop (1 Hz)
[... clean execution ...]
```

## Verify Everything Works

### 1. Check Telemetry Files
```bash
ls -lh telemetry/phaseA/
# Should see: engine_YYYYMMDD_HHMMSS.jsonl files
```

### 2. Check Redis Events
```bash
# In another terminal
redis-cli SUBSCRIBE atc:events
# Should see events published every 50ms
```

### 3. Check Database
```bash
psql -d atc_system -c "SELECT COUNT(*) FROM events WHERE created_at > NOW() - INTERVAL '1 minute';"
# Should see recent event count
```

## Common Commands

```bash
# Run 60-second test (silent)
python -m engine --test

# Run 60-second test (verbose)
DEBUG_PRINTS=true python -m engine --test

# Run indefinitely (silent)
python -m engine

# Run indefinitely (verbose)
DEBUG_PRINTS=true python -m engine

# Custom duration
python -m engine --duration 300  # 5 minutes
```

## Data Flow

All data flows continue working **exactly as before**:

- ✅ **PostgreSQL**: Aircraft states updated every 1 second
- ✅ **Redis**: Events published every 50ms
- ✅ **Telemetry**: Snapshots written every 10 seconds
- ✅ **1 Hz Tick**: Deterministic physics maintained

## Need Help?

See full documentation:
- `ENGINE_LOGGING_REFACTOR.md` - Detailed refactor info
- `ENV_CONFIG.md` - Environment variable reference
- `REFACTOR_COMPLETE_LOGGING.md` - Complete verification results

## That's It! 🎉

The engine now runs quietly by default while maintaining full functionality.

