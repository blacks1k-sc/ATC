# ATC Brain V4 - Complete Setup Guide

## 🎯 Overview

This guide will help you set up the **Python ATC Brain microservice** alongside your existing Next.js ATC system. The Python service provides intelligent aircraft control using waypoint-based navigation and SID/STAR procedures for CYYZ.

## 🏗️ Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                   Browser (User Interface)                   │
│                  React Components + Leaflet                  │
└────────────────┬─────────────────────────────────────────────┘
                 │ HTTP / SSE
                 │
┌────────────────▼─────────────────────────────────────────────┐
│         Next.js Application (Port 3000)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  API Routes (TypeScript)                               │ │
│  │  - /api/atc-brain/start → proxies to Python            │ │
│  │  - /api/atc-brain/stop  → proxies to Python          │ │
│  │  - /api/atc-brain/status → proxies to Python          │ │
│  └────────────────────────────────────────────────────────┘ │
└──────┬────────────────────┬──────────────────┬──────────────┘
       │                    │                  │ HTTP Proxy
       │                    │                  │
       │                    │         ┌────────▼──────────────┐
       │                    │         │  Python ATC Brain     │
       │                    │         │  (Port 8000)          │
       │                    │         │                       │
       │                    │         │  FastAPI Service:      │
       │                    │         │  - /api/start           │
       │                    │         │  - /api/stop           │
       │                    │         │  - /api/status         │
       │                    │         │  - /ws/updates         │
       │                    │         └───────┬───────────────┘
       │                    │                 │
       │ PostgreSQL         │ Redis Pub/Sub   │ PostgreSQL
       │ Connection         │ Event Bus       │ Connection
       │                    │                 │
┌──────▼────────────────────▼─────────────────▼───────────────┐
│                     Shared Infrastructure                    │
│                                                              │
│  PostgreSQL Database:          Redis:                        │
│    - aircraft_instances          - Event channels           │
│    - aircraft_types              - Real-time messages       │
│    - events                      - Pub/Sub coordination     │
│    - runways                                                │
│    - waypoints (NEW)                                        │
│    - procedures (NEW)                                       │
│    - gates (NEW)                                           │
│    - taxiways (NEW)                                        │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Setup Steps

### Step 1: Database Schema Updates

First, update your PostgreSQL database with the new tables:

```bash
# Navigate to your Next.js project
cd atc-nextjs

# Run the updated schema
psql -h localhost -U postgres -d atc_system -f database/schema.sql

# Seed the new tables with CYYZ data
node scripts/seed-waypoints.js
```

### Step 2: Python Service Setup

```bash
# Navigate to the Python service directory
cd atc-brain-python

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp env.example .env
# Edit .env with your database and Redis credentials
```

### Step 3: Configure Environment Variables

Edit `atc-brain-python/.env`:

```env
# Database Configuration (same as your Next.js app)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=atc_system
DB_USER=postgres
DB_PASSWORD=your_password

# Redis Configuration (same as your Next.js app)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ATC Brain Configuration
ATC_BRAIN_HOST=0.0.0.0
ATC_BRAIN_PORT=8000
ATC_BRAIN_UPDATE_INTERVAL=5
```

### Step 4: Start the Services

**Terminal 1 - Python ATC Brain:**
```bash
cd atc-brain-python
./run.sh
# Or manually: python src/main.py
```

**Terminal 2 - Next.js Frontend:**
```bash
cd atc-nextjs
npm run dev
```

**Terminal 3 - Database & Redis (if not already running):**
```bash
# PostgreSQL (if using Docker)
docker run -d --name postgres -e POSTGRES_PASSWORD=your_password -p 5432:5432 postgres:13

# Redis (if using Docker)
docker run -d --name redis -p 6379:6379 redis:alpine
```

## 🧪 Testing the Integration

### 1. Test Python Service Health

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "atc_brain": "stopped"
}
```

### 2. Test Next.js Proxy

```bash
curl http://localhost:3000/api/atc-brain/health
```

### 3. Start ATC Brain from Frontend

1. Open `http://localhost:3000`
2. Click "START SYSTEM" button
3. Check browser console for events
4. Add aircraft and watch them follow waypoints

## 🔄 How It Works

### Aircraft Spawn Process

1. **User Action**: User clicks "ADD AIRCRAFT" in browser
2. **Next.js API**: Creates aircraft in PostgreSQL
3. **Python ATC Brain**: Detects new aircraft via database query
4. **SID/STAR Controller**: Assigns appropriate procedure
5. **Navigation Engine**: Calculates waypoint navigation
6. **Event Publisher**: Publishes position updates to Redis
7. **Next.js SSE**: Streams events to browser
8. **Frontend**: Updates aircraft position on radar

### Waypoint Navigation

- **CYYZ Waypoints**: Pre-loaded with real-world waypoints
- **SID Procedures**: Departure routes (DUVOS SIX, IMEBA TWO)
- **STAR Procedures**: Arrival routes (BOXUM FIVE, BIMKI THREE)
- **Automated Sequencing**: Aircraft follow waypoint sequences
- **Altitude/Speed Restrictions**: Procedure compliance

## 🛠️ Development Workflow

### Adding New Procedures

1. **Add Waypoints**: Insert into `waypoints` table
2. **Create Procedure**: Insert into `procedures` table
3. **Test**: Spawn aircraft and verify navigation

### Debugging

```bash
# Check Python service logs
cd atc-brain-python
python src/main.py

# Check database connection
python -c "from src.database.connection import DatabaseManager; print('DB OK')"

# Check Redis connection
python -c "from src.services.event_publisher import EventPublisher; print('Redis OK')"
```

### Monitoring

- **Python Service**: `http://localhost:8000/api/health`
- **Next.js Proxy**: `http://localhost:3000/api/atc-brain/health`
- **Database**: Check `aircraft_instances` table
- **Redis**: Monitor event channels

## 📊 Key Features

### ✅ What's New in V4

- **Python Microservice**: Separate service for AI control
- **Waypoint Navigation**: Real-world CYYZ procedures
- **SID/STAR Controllers**: Automated departure/arrival
- **Flight Phase Management**: Complete state machine
- **Event Integration**: Seamless with existing frontend

### ✅ What Stays the Same

- **Next.js Frontend**: No changes needed
- **React Components**: RadarDisplay, ControlPanels, etc.
- **Database Schema**: Extended, not replaced
- **Redis Events**: Same event format
- **SSE Streaming**: Same real-time updates

## 🚨 Troubleshooting

### Common Issues

**Python service won't start:**
```bash
# Check dependencies
pip install -r requirements.txt

# Check environment variables
cat .env

# Check database connection
python -c "import asyncpg; print('PostgreSQL driver OK')"
```

**Database connection failed:**
```bash
# Verify PostgreSQL is running
psql -h localhost -U postgres -d atc_system -c "SELECT 1"

# Check credentials in .env
```

**Redis connection failed:**
```bash
# Verify Redis is running
redis-cli ping

# Check Redis configuration
```

**Frontend not receiving events:**
```bash
# Check SSE stream
curl -N http://localhost:3000/api/events/stream

# Check Redis events
redis-cli monitor
```

## 🎉 Success Indicators

You'll know the integration is working when:

1. ✅ Python service starts without errors
2. ✅ Next.js proxy endpoints respond
3. ✅ Aircraft spawn and move automatically
4. ✅ Waypoint navigation is visible on radar
5. ✅ Flight phases transition correctly
6. ✅ Real-time events flow to frontend

## 📝 Next Steps

After successful setup:

1. **Customize Procedures**: Add more SID/STAR routes
2. **Enhance Controllers**: Add more sophisticated logic
3. **Add Conflict Detection**: Implement separation assurance
4. **Optimize Performance**: Tune update intervals
5. **Add Monitoring**: Set up logging and metrics

## 🤝 Support

If you encounter issues:

1. Check the logs in both services
2. Verify database and Redis connections
3. Ensure all environment variables are set
4. Test each component individually
5. Check the troubleshooting section above

The Python ATC Brain is now ready to provide intelligent aircraft control for your ATC system! 🚀
