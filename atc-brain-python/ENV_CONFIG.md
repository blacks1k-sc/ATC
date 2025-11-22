# Environment Configuration

This document describes all environment variables used by the ATC kinematics engine.

## Quick Start

Create a `.env` file in the `atc-brain-python` directory with the following variables:

```bash
# ========== Mode Configuration ==========
ENGINE_MODE=PROD  # PROD or DEV

# ========== Debug Configuration ==========
DEBUG_PRINTS=false  # Set to 'true' to enable per-tick debug logging

# ========== Telemetry Configuration ==========
TELEMETRY_DIR=./telemetry/phaseA  # Directory for telemetry output

# ========== Database Configuration ==========
DB_HOST=localhost
DB_PORT=5432
DB_NAME=atc_system
DB_USER=postgres
DB_PASSWORD=password
DB_POOL_SIZE=20

# ========== Redis Configuration ==========
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
EVENT_CHANNEL=atc:events
```

## Environment Variables

### Mode Configuration

#### `ENGINE_MODE`
- **Values**: `PROD` or `DEV`
- **Default**: `PROD`
- **Description**: Controls operational mode
  - `PROD`: Production settings (faster Redis, more frequent telemetry)
  - `DEV`: Development settings (more logging, slower intervals)

### Debug Configuration

#### `DEBUG_PRINTS`
- **Values**: `true` or `false`
- **Default**: `false`
- **Description**: Controls per-tick debug logging
  - `false`: Clean console output (recommended for production)
  - `true`: Verbose logging of threshold events (TOUCHDOWN, HANDOFF_READY, etc.)

### Telemetry Configuration

#### `TELEMETRY_DIR`
- **Type**: Directory path
- **Default**: `./telemetry/phaseA`
- **Description**: Directory where telemetry `.jsonl` files are written
  - Files are named: `engine_YYYYMMDD_HHMMSS.jsonl`
  - Each line is a JSON snapshot of aircraft state

### Database Configuration

#### `DB_HOST`
- **Type**: String
- **Default**: `localhost`
- **Description**: PostgreSQL server hostname

#### `DB_PORT`
- **Type**: Integer
- **Default**: `5432`
- **Description**: PostgreSQL server port

#### `DB_NAME`
- **Type**: String
- **Default**: `atc_system`
- **Description**: PostgreSQL database name

#### `DB_USER`
- **Type**: String
- **Default**: `postgres`
- **Description**: PostgreSQL username

#### `DB_PASSWORD`
- **Type**: String
- **Default**: `password`
- **Description**: PostgreSQL password

#### `DB_POOL_SIZE`
- **Type**: Integer
- **Default**: `20` (PROD), `10` (DEV)
- **Description**: Maximum number of database connections in the pool

### Redis Configuration

#### `REDIS_HOST`
- **Type**: String
- **Default**: `localhost`
- **Description**: Redis server hostname

#### `REDIS_PORT`
- **Type**: Integer
- **Default**: `6379`
- **Description**: Redis server port

#### `REDIS_PASSWORD`
- **Type**: String
- **Default**: None
- **Description**: Redis password (leave empty if no auth)

#### `EVENT_CHANNEL`
- **Type**: String
- **Default**: `atc:events`
- **Description**: Redis pub/sub channel for publishing events

## Usage Examples

### Silent Mode (Production)
```bash
ENGINE_MODE=PROD DEBUG_PRINTS=false python -m engine
```

### Debug Mode (Development)
```bash
ENGINE_MODE=DEV DEBUG_PRINTS=true python -m engine
```

### Custom Telemetry Directory
```bash
TELEMETRY_DIR=/var/log/atc/telemetry python -m engine
```

### Complete Production Setup
```bash
# Create .env file
cat > .env << EOF
ENGINE_MODE=PROD
DEBUG_PRINTS=false
TELEMETRY_DIR=/var/log/atc/telemetry
DB_HOST=postgres.production.local
DB_PORT=5432
DB_NAME=atc_production
DB_USER=atc_engine
DB_PASSWORD=secure_password_here
DB_POOL_SIZE=50
REDIS_HOST=redis.production.local
REDIS_PORT=6379
REDIS_PASSWORD=redis_password_here
EVENT_CHANNEL=atc:events
EOF

# Run engine
python -m engine
```

## Performance Tuning

### Production Settings (PROD mode)
- Redis batch interval: 50ms (high-frequency updates)
- Telemetry interval: 10s (frequent snapshots)
- DB pool size: 20 connections
- Worker stats logging: Disabled

### Development Settings (DEV mode)
- Redis batch interval: 100ms (lower frequency)
- Telemetry interval: 30s (less frequent)
- DB pool size: 10 connections
- Worker stats logging: Enabled

## Monitoring

### Check Telemetry Output
```bash
# View latest telemetry file
tail -f telemetry/phaseA/engine_*.jsonl

# Count snapshots
wc -l telemetry/phaseA/engine_*.jsonl
```

### Monitor Redis Events
```bash
redis-cli SUBSCRIBE atc:events
```

### Check Database Events
```bash
psql -d atc_system -c "SELECT * FROM events ORDER BY created_at DESC LIMIT 10;"
```

