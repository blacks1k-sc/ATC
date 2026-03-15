# ATC System Startup Guide

## Quick Start - Both Services

### Terminal 1: Start Next.js Frontend
```bash
cd /Users/nrup/ATC-1/atc-nextjs
npm run dev
```
This starts the web interface on **http://localhost:3000**

### Terminal 2: Start Python Engine (Already Running ✅)
```bash
cd /Users/nrup/ATC-1/atc-brain-python
./scripts/start_engine.sh
```
The engine is currently running and listening for aircraft!

## Database Setup (One-Time)

If you haven't run the migration to add the `sector` field:
```bash
cd /Users/nrup/ATC-1/atc-nextjs
node scripts/add-sector-field.js
```

## Access Points

- **Main ATC Interface**: http://localhost:3000
- **Engine Ops Monitor**: http://localhost:3000/engine-ops
- **Ground Operations**: http://localhost:3000/ground
- **Logs**: http://localhost:3000/logs
- **Health Check**: http://localhost:3000/api/health

## System Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Next.js Web    │         │  Python Engine   │
│  (Port 3000)    │◄───────►│  (Background)    │
└────────┬────────┘         └────────┬─────────┘
         │                           │
         ▼                           ▼
    ┌────────────────────────────────────┐
    │         PostgreSQL + Redis         │
    │      (Port 5432)    (Port 6379)    │
    └────────────────────────────────────┘
```

## Workflow

1. **Start Engine** ← Already running! ✅
2. **Start Frontend** ← Need to start this
3. **Generate Aircraft** via UI at http://localhost:3000
4. **Monitor in Real-time** at http://localhost:3000/engine-ops

## Current Status

✅ **PostgreSQL**: Running (Port 5432)
✅ **Redis**: Running (Port 6379)  
✅ **Python Engine**: Running (waiting for aircraft)
❌ **Next.js Frontend**: Need to start

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Restart Next.js
cd /Users/nrup/ATC-1/atc-nextjs && npm run dev
```

### Check Database Connection
```bash
psql atc_system -c "SELECT COUNT(*) FROM aircraft_instances;"
```

### View Engine Logs
The Python engine logs to console in Terminal 2.
Telemetry files: `atc-brain-python/telemetry/phaseA/`


