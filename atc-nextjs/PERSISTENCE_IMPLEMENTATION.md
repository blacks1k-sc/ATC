# ATC System Persistence Implementation

This document describes the comprehensive persistence and realtime streaming system implemented for the ATC application using PostgreSQL and Redis.

## Architecture Overview

The system implements a full-stack persistence layer with:

- **PostgreSQL**: Primary data store with normalized schema
- **Redis**: Event bus for real-time pub/sub messaging
- **REST API**: CRUD operations for aircraft management
- **SSE**: Server-Sent Events for real-time event streaming
- **Environment-driven configuration**: Zero hardcoded values

## Database Schema

### Tables

1. **aircraft_types**: Reference data for aircraft specifications
2. **airlines**: Reference data for airline information
3. **aircraft_instances**: Generated aircraft with unique identifiers
4. **events**: Time-ordered log with message, level, type, and details

### Key Features

- Foreign key constraints with proper cascading
- Unique constraints on ICAO24, callsigns, and registrations
- JSONB columns for flexible data storage
- Comprehensive indexing for performance
- Automatic timestamp management

## API Endpoints

### Aircraft Management

- `POST /api/aircraft/generate` - Create new aircraft
- `GET /api/aircraft` - List active aircraft
- `GET /api/aircraft/[id]` - Get specific aircraft
- `PUT /api/aircraft/[id]` - Update aircraft state

### Events

- `GET /api/events` - List events with filters
- `GET /api/events/stream` - SSE endpoint for real-time events

### Health

- `GET /api/health` - System health check

## Real-time Features

### Event Bus

- Redis pub/sub for event distribution
- Type-safe event publishing
- Automatic reconnection handling
- Event filtering and routing

### SSE Streaming

- Initial event loading from database
- Real-time event streaming from Redis
- Client-side reconnection logic
- Connection status indicators

## Configuration

All configuration is environment-driven:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=atc_system
DB_USER=postgres
DB_PASSWORD=password
DB_POOL_SIZE=20

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Data Pipeline
AIRCRAFT_TYPES_PATH=../data-pipeline/dist/aircraft_types.json
AIRLINES_PATH=../data-pipeline/dist/airlines.json

# Event Bus
EVENT_CHANNEL=atc:events

# Development
SKIP_DB=false
SKIP_REDIS=false
```

## Setup Commands

```bash
# Database setup
npm run db:migrate    # Run schema migrations
npm run db:seed       # Seed reference data
npm run db:reset      # Reset and reseed

# Development
npm run setup:full    # Full setup with database
npm run health       # Check system health
```

## Data Layer

### Repositories

- `AircraftTypeRepository`: Aircraft type management
- `AirlineRepository`: Airline data access
- `AircraftInstanceRepository`: Aircraft CRUD operations
- `EventRepository`: Event logging and retrieval

### Transaction Management

- Database transactions for data consistency
- Retry logic for uniqueness conflicts
- Graceful error handling
- Connection pooling

## Event System

### Event Types

- `aircraft.created`: New aircraft generated
- `aircraft.updated`: Aircraft state changes
- `aircraft.status_changed`: Status transitions
- `aircraft.position_updated`: Position updates
- `event.created`: New log entries
- `system.status`: System status updates
- `communication`: ATC communications

### Event Publishing

```typescript
// Publish aircraft creation
await eventBus.publishAircraftCreated(aircraft);

// Publish status change
await eventBus.publishAircraftStatusChanged(aircraft, oldStatus, newStatus);

// Publish position update
await eventBus.publishAircraftPositionUpdated(aircraft, position);
```

## UI Integration

### Real-time Updates

- Automatic SSE connection setup
- Connection status indicators
- Real-time event display
- Client-side filtering

### Error Handling

- Graceful degradation when services unavailable
- Connection retry logic
- User-friendly error messages
- Health status display

## Performance Considerations

### Database

- Connection pooling with configurable limits
- Comprehensive indexing strategy
- JSONB for flexible queries
- Optimized joins for related data

### Redis

- Efficient pub/sub messaging
- Connection pooling
- Automatic failover handling
- Event filtering at source

### Client

- Efficient SSE handling
- Minimal re-renders
- Optimized filtering
- Connection management

## Security

- Environment-based configuration
- No hardcoded credentials
- Input validation and sanitization
- SQL injection prevention
- XSS protection

## Monitoring

- Health check endpoints
- Connection status monitoring
- Error logging and tracking
- Performance metrics
- Real-time status indicators

## Development

### Local Development

1. Start PostgreSQL and Redis
2. Copy `env.example` to `.env`
3. Run `npm run setup:full`
4. Start development server

### Testing

- Health checks: `npm run health`
- Database status: Check `/api/health`
- Event streaming: Monitor logs page
- Aircraft generation: Use generate button

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check PostgreSQL is running
   - Verify connection parameters
   - Check database exists

2. **Redis connection failed**
   - Check Redis is running
   - Verify connection parameters
   - Check authentication

3. **SSE connection lost**
   - Check network connectivity
   - Verify Redis pub/sub working
   - Check browser console for errors

4. **Events not appearing**
   - Check database has events
   - Verify Redis pub/sub
   - Check SSE connection status

### Debug Commands

```bash
# Check system health
curl http://localhost:3000/api/health

# Test database connection
npm run db:migrate

# Test Redis connection
redis-cli ping

# Check event stream
curl -N http://localhost:3000/api/events/stream
```

## Future Enhancements

- WebSocket support for bidirectional communication
- Event persistence in Redis for durability
- Advanced filtering and search capabilities
- Performance monitoring and metrics
- Automated testing and CI/CD integration
