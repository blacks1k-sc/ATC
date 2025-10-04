# ATC Brain Python Service

AI-powered Air Traffic Control Brain for automated aircraft management using waypoint-based navigation and SID/STAR procedures.

## 🏗️ Architecture

This Python service runs as a **microservice** alongside the Next.js frontend, providing intelligent aircraft control through:

- **FastAPI** web server for HTTP endpoints
- **PostgreSQL** database for aircraft and waypoint data
- **Redis** event bus for real-time communication
- **Waypoint-based navigation** for CYYZ procedures
- **SID/STAR controllers** for departure and arrival procedures

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database (shared with Next.js app)
- Redis server (shared with Next.js app)

### Installation

```bash
# Navigate to Python service directory
cd atc-brain-python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env
# Edit .env with your database and Redis credentials
```

### Configuration

Edit `.env` file with your settings:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=atc_system
DB_USER=postgres
DB_PASSWORD=your_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ATC Brain Configuration
ATC_BRAIN_HOST=0.0.0.0
ATC_BRAIN_PORT=8000
ATC_BRAIN_UPDATE_INTERVAL=5
```

### Running the Service

```bash
# Start the FastAPI server
python src/main.py

# Or with uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at `http://localhost:8000`

## 📡 API Endpoints

### Health & Status

- `GET /` - Basic health check
- `GET /api/health` - Detailed health status
- `GET /api/status` - ATC Brain status

### Control

- `POST /api/start` - Start ATC Brain control loop
- `POST /api/stop` - Stop ATC Brain control loop

### WebSocket

- `WS /ws/updates` - Real-time updates stream

## 🧠 ATC Brain Features

### Waypoint Navigation

- **CYYZ Waypoints**: Pre-loaded with real-world waypoints
- **Haversine Distance**: Accurate distance calculations
- **Bearing Calculation**: Precise heading calculations
- **Position Updates**: Real-time aircraft positioning

### Flight Procedures

#### SID (Standard Instrument Departure)
- **DUVOS SIX**: Western departure from runway 05
- **IMEBA TWO**: Southern departure from runway 23
- **Automated Sequencing**: Waypoint progression
- **Altitude/Speed Restrictions**: Procedure compliance

#### STAR (Standard Terminal Arrival Route)
- **BOXUM FIVE**: Standard arrival for runway 05
- **BIMKI THREE**: Alternate arrival for runway 05
- **Descent Management**: Automated altitude changes
- **Approach Sequencing**: Final approach coordination

### Flight Phase Management

1. **SPAWNING** → Aircraft created
2. **DEPARTURE** → SID procedure execution
3. **ENROUTE** → Cruise phase
4. **ARRIVAL** → STAR procedure execution
5. **APPROACH** → Final approach
6. **FINAL** → Landing approach
7. **LANDING** → Touchdown and rollout

## 🔄 Event Flow

```
1. Next.js Frontend → POST /api/atc-brain/start
2. Python Service → Starts control loop
3. Python Service → Queries active aircraft
4. Python Service → Calculates positions/commands
5. Python Service → Publishes to Redis
6. Next.js SSE → Receives events
7. Browser → Updates UI in real-time
```

## 🗄️ Database Schema

The service uses the same PostgreSQL database as the Next.js app with additional tables:

- **waypoints**: Navigation waypoints for CYYZ
- **procedures**: SID/STAR procedures
- **gates**: Terminal gates for departures
- **taxiways**: Ground movement paths
- **aircraft_history**: Archived flight data

## 🛠️ Development

### Project Structure

```
atc-brain-python/
├── src/
│   ├── main.py                 # FastAPI server
│   ├── atc_brain.py           # Main orchestrator
│   ├── config/
│   │   └── settings.py        # Configuration
│   ├── database/
│   │   └── connection.py      # PostgreSQL connection
│   ├── services/
│   │   └── event_publisher.py # Redis event publishing
│   ├── core/
│   │   └── navigation.py      # Navigation utilities
│   └── controllers/
│       ├── sid_controller.py  # Departure procedures
│       └── star_controller.py # Arrival procedures
├── requirements.txt
├── env.example
└── README.md
```

### Adding New Procedures

1. Add waypoints to database
2. Create procedure in `procedures` table
3. Update controllers as needed
4. Test with aircraft spawn

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python src/main.py

# Check database connection
python -c "from src.database.connection import DatabaseManager; print('DB OK')"

# Check Redis connection
python -c "from src.services.event_publisher import EventPublisher; print('Redis OK')"
```

## 🚀 Deployment

### Docker (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
CMD ["python", "src/main.py"]
```

### Production Considerations

- Use environment variables for configuration
- Set up proper logging
- Configure database connection pooling
- Set up Redis clustering if needed
- Use process manager (PM2, systemd)

## 🔗 Integration with Next.js

The Python service integrates seamlessly with the existing Next.js ATC system:

1. **Same Database**: Shares PostgreSQL with Next.js
2. **Same Redis**: Uses same event bus
3. **Proxy Endpoints**: Next.js proxies requests to Python
4. **Real-time Updates**: Events flow through existing SSE stream

## 📊 Monitoring

- **Health Checks**: Built-in health endpoints
- **Logging**: Structured logging with timestamps
- **Metrics**: Aircraft count, procedure status
- **Alerts**: System alerts via Redis events

## 🤝 Contributing

1. Follow Python PEP 8 style guide
2. Add type hints to all functions
3. Write docstrings for public methods
4. Test with real aircraft data
5. Update documentation

## 📝 License

Part of the ATC-1 project. See main project README for license information.
