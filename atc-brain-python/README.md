# ATC Kinematics Engine - Phase A

Deterministic 1 Hz simulation engine for autonomous aircraft control in the ATC system.

## 🎯 Overview

The Kinematics Engine is the autonomous "pilot" that controls arrival aircraft from generation until ATC takeover. It implements realistic physics-based motion using aviation formulas and emits real-time events via Redis pub/sub.

**Phase A Scope**: Arrivals only. Departures ignored.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (with atc-nextjs schema)
- Redis
- Next.js application running

### Installation

```bash
cd atc-brain-python

# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
# DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
# REDIS_HOST, REDIS_PORT

# Install dependencies
pip install -r requirements.txt

# Run database migration
python scripts/migrate_db.py
```

### Running the Engine

```bash
# Start engine (runs indefinitely)
python -m engine.core_engine

# Run 60-second test
python -m engine.core_engine --test

# Run for specific duration
python -m engine.core_engine --duration 300  # 5 minutes
```

### Running Tests

```bash
# Unit tests
python -m unittest discover tests/

# Specific test file
python -m unittest tests.test_kinematics
```

## 📁 Project Structure

```
atc-brain-python/
├── engine/
│   ├── core_engine.py        # Main orchestrator (1 Hz tick loop)
│   ├── kinematics.py         # Physics formulas (speed, heading, altitude)
│   ├── geo_utils.py          # Geographic calculations
│   ├── state_manager.py      # Database integration
│   ├── event_publisher.py    # Redis event emission
│   ├── spawn_listener.py     # New aircraft detection
│   ├── airport_data.py       # Airport reference data
│   └── constants.py          # Physical constants
├── docs/
│   ├── phaseA_architecture.md   # System design
│   ├── phaseA_contracts.md      # Data schemas
│   └── phaseA_acceptance.md     # Validation criteria
├── tests/
│   ├── test_kinematics.py    # Formula unit tests
│   └── test_geo_utils.py     # Geographic tests
├── scripts/
│   └── migrate_db.py         # Database migration
├── telemetry/phaseA/         # Output logs (created at runtime)
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🧮 Physics Formulas

All formulas operate on 1-second time steps (Δt = 1 s):

| System | Formula |
|--------|---------|
| Speed tracking | ΔV = clip(V* − V, ±a_max Δt) |
| Turn rate | ω_max = g·tan(φ_max)/V_m |
| Altitude | Δh = clip(h* − h, ±ḣ_max Δt/60) |
| Position | Δlat = (V/3600)·Δt·cos(ψ)/60 |
| Distance | D = √((Δφ)² + (cosφ Δλ)²)·60 |

**Constants**: a_acc=0.6 kt/s, a_dec=0.8 kt/s, φ_max=25°, ḣ=1800-3000 fpm

## 📡 Event Flow

### Subscribed Events (from Next.js)

- `aircraft.created` → Detects new arrivals and assigns ENGINE control

### Published Events (to Next.js)

- `aircraft.position_updated` → Every tick for each aircraft
- `aircraft.threshold_event` → ENTERED_ENTRY_ZONE, HANDOFF_READY, TOUCHDOWN
- `engine.state_snapshot` → Every 10 ticks
- `system.status` → On start/stop

## 🎛️ Configuration

Environment variables in `.env`:

```bash
# Database (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=atc_system
DB_USER=postgres
DB_PASSWORD=your_password
DB_POOL_SIZE=20

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Engine
ENGINE_TICK_RATE=1.0
TELEMETRY_DIR=telemetry/phaseA

# Airport
AIRPORT_ICAO=CYYZ
AIRPORT_DATA_PATH=../atc-nextjs/src/data/cyyz-airport.json
```

## 📊 Telemetry

Telemetry snapshots written to `telemetry/phaseA/engine_YYYYMMDD_HHMMSS.jsonl`:

```json
{"tick":1,"timestamp":"2025-10-05T12:00:01Z","id":123,"callsign":"ACA217","lat":43.85,"lon":-79.80,"altitude_ft":17950,"speed_kts":279,"heading":230,"vertical_speed_fpm":-500,"distance_to_airport_nm":42.1,"controller":"ENGINE","phase":"DESCENT"}
```

## ✅ Acceptance Criteria

- ✅ 1 Hz tick rate (± 0.05 s drift over 10 minutes)
- ✅ All arrivals with `controller='ENGINE'` move deterministically
- ✅ Threshold events fire once (ENTERED_ENTRY_ZONE, HANDOFF_READY, TOUCHDOWN)
- ✅ JSON telemetry logs written
- ✅ Deterministic replay (same seed → identical results)
- ✅ Graceful handling of DB/Redis disconnects

## 🧪 Testing

### Unit Tests

```bash
python -m unittest tests.test_kinematics
python -m unittest tests.test_geo_utils
```

### 60-Second Simulation Test

```bash
# 1. Start Next.js (atc-nextjs)
cd ../atc-nextjs && npm run dev

# 2. Generate 3 arrival aircraft via UI

# 3. Run engine test
cd ../atc-brain-python
python -m engine.core_engine --test

# Expected: 60 ticks, 3 aircraft controlled, events fired, telemetry created
```

## 🐛 Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify database exists
psql -U postgres -l | grep atc_system

# Run migration
python scripts/migrate_db.py
```

### Redis Connection Failed

```bash
# Check Redis is running
redis-cli ping

# Start Redis
redis-server
```

### No Aircraft Detected

1. Verify Next.js generated aircraft with `flight_type='ARRIVAL'`
2. Check Redis channel: `redis-cli SUBSCRIBE atc:events`
3. Check engine logs for spawn listener messages

### Slow Tick Performance

- Check database query time
- Reduce active aircraft count (< 100)
- Verify database indexes exist
- Check PostgreSQL connection pool size

## 📚 Documentation

- [Architecture](docs/phaseA_architecture.md) - System design and data flow
- [Contracts](docs/phaseA_contracts.md) - Event schemas and database fields
- [Acceptance](docs/phaseA_acceptance.md) - Validation criteria and tests

## 🚀 Future Phases

**Phase 2**: Entry ATC integration (handoff logic, target commands)  
**Phase 3**: Conflict detection and separation  
**Phase 4**: Departure support  
**Phase 5**: Weather integration (wind vectors)  

## 🔒 Security

- All credentials in `.env` (never committed)
- Database uses connection pooling with authentication
- Redis optional password authentication
- No exposed network ports

## 📝 License

Internal ATC System Project

---

**Version**: 1.0.0  
**Branch**: `ai-atc-brain-v2`  
**Last Updated**: 2025-10-05

