# ATC System - Project Overview

A comprehensive Air Traffic Control simulation system built with modern web technologies, featuring real-time persistence, event streaming, and interactive UI components.

## 🏗️ Project Architecture

### **Multi-Component System**
- **Frontend**: Next.js 14 + React + TypeScript application
- **Backend**: REST API with PostgreSQL database
- **Real-time**: Redis event bus with Server-Sent Events (SSE)
- **Data Pipeline**: Python-based aircraft data processing
- **Database**: PostgreSQL with comprehensive schema
- **Caching**: Redis for real-time event distribution

## 🛠️ Technology Stack

### **Frontend Technologies**
- **Next.js 14**: React framework with App Router
- **React 18**: Component-based UI library
- **TypeScript**: Type-safe JavaScript
- **CSS Grid**: Layout system for ATC interface
- **Leaflet**: Interactive maps for ground operations
- **React-Leaflet**: React components for maps

### **Backend Technologies**
- **Node.js**: JavaScript runtime
- **PostgreSQL**: Primary database with JSONB support
- **Redis**: Event bus and real-time messaging
- **REST API**: CRUD operations for aircraft management
- **Server-Sent Events**: Real-time event streaming

### **Development Tools**
- **ESLint**: Code quality and style enforcement
- **TypeScript**: Static type checking
- **Git**: Version control
- **npm**: Package management

### **Data Pipeline**
- **Python 3**: Data processing and API integration
- **JSON**: Data exchange format
- **HTTP**: External API integration
- **Caching**: Local data persistence

## 📊 Database Schema

### **Core Tables**

#### **aircraft_types**
- Reference data for aircraft specifications
- Fields: `icao_type`, `wake`, `engines`, `dimensions`, `mtow_kg`, `cruise_speed_kts`, etc.
- Indexed on `icao_type` for fast lookups

#### **airlines**
- Reference data for airline information
- Fields: `name`, `icao`, `iata`, `country`
- Indexed on `icao` and `iata` for efficient queries

#### **aircraft_instances**
- Generated aircraft with unique identifiers
- Fields: `icao24`, `registration`, `callsign`, `position`, `status`, `squawk_code`
- Foreign keys to `aircraft_types` and `airlines`
- JSONB `position` field for flexible location data

#### **events**
- Time-ordered log with comprehensive event tracking
- Fields: `level`, `type`, `message`, `details`, `aircraft_id`, `sector`, `frequency`, `direction`
- Supports filtering by level, type, aircraft, and sector

### **Key Features**
- **Foreign Key Constraints**: Proper relational integrity
- **Unique Constraints**: ICAO24, callsigns, and registrations
- **JSONB Support**: Flexible data storage for positions and details
- **Comprehensive Indexing**: Optimized for performance
- **Automatic Timestamps**: Created/updated tracking
- **Database Functions**: Unique identifier generation

## 🔌 API Endpoints

### **Aircraft Management**
- `POST /api/aircraft/generate` - Create new aircraft with unique identifiers
- `GET /api/aircraft` - List active aircraft with filtering
- `GET /api/aircraft/[id]` - Get specific aircraft details
- `PUT /api/aircraft/[id]` - Update aircraft state (position, status, etc.)

### **Event System**
- `GET /api/events` - List events with advanced filtering
- `GET /api/events/stream` - SSE endpoint for real-time events

### **Data Access**
- `GET /api/aircraft/types` - Get aircraft types and airlines from data pipeline
- `GET /api/airport/[icao]` - Get airport data and runway information

### **System Health**
- `GET /api/health` - Comprehensive health check for database and Redis

## 🎨 Frontend Components

### **Core System Components**

#### **ATCSystem.tsx** - Main System Controller
- Central state management for entire ATC system
- Manages aircraft data, flight strips, and system status
- Handles emergency simulation and resolution
- Coordinates between all other components

#### **Header.tsx** - System Header
- Controller tabs (TOWER, GROUND, APPROACH, CENTER, COORD)
- System status indicators with color-coded lights
- Live UTC clock with runway status
- Tab switching functionality

#### **RadarDisplay.tsx** - Airspace Radar
- Interactive radar display with sweep animation
- Aircraft positioning and tracking
- Emergency aircraft highlighting
- Real-time position updates

#### **RunwayDisplay.tsx** - Runway Information
- Airport runway layout and status
- Departure and arrival information
- Weather data integration
- Runway configuration display

#### **ControlPanels.tsx** - Flight Management
- Flight strips for active aircraft
- Weather data display
- Emergency coordination messages
- System status monitoring

#### **Communications.tsx** - ATC Communications
- 6 operational communication panels
- Color-coded message types (departure/arrival)
- Real-time message updates
- System status integration

#### **ControlButtons.tsx** - System Controls
- START SYSTEM button
- ADD AIRCRAFT functionality
- GENERATE AIRCRAFT with selector
- SIMULATE EMERGENCY button
- Navigation to logs and ground operations

### **Specialized Components**

#### **AircraftSelector.tsx** - Aircraft Generation
- Interactive aircraft type selection
- Airline selection with filtering
- Real-time aircraft generation
- Integration with database

#### **GroundMapYYZ.tsx** - Ground Operations
- Interactive airport ground layout
- Aircraft positioning on ground
- Taxiway and gate management
- Real-time ground traffic

## 🔄 Real-time Features

### **Event Bus System**
- **Redis Pub/Sub**: Real-time event distribution
- **Event Types**: Aircraft created/updated, status changes, position updates
- **Filtering**: Event filtering by type, level, aircraft, and sector
- **Persistence**: Events stored in database for historical access

### **Server-Sent Events (SSE)**
- **Real-time Streaming**: Live event updates to frontend
- **Initial Data Loading**: Historical events from database
- **Connection Management**: Automatic reconnection and error handling
- **Filtering**: Client-side event filtering

### **State Management**
- **React Hooks**: useState, useEffect, useCallback for state management
- **Zustand**: Lightweight state management for complex data
- **Real-time Updates**: Automatic UI updates from server events

## 🚀 Key Features

### **Aircraft Management**
- **Unique Identifiers**: ICAO24, registration, and callsign generation
- **Position Tracking**: Real-time aircraft positioning
- **Status Management**: Active, emergency, and inactive states
- **Flight Planning**: Comprehensive flight plan data

### **Emergency Simulation**
- **Emergency Declaration**: Aircraft emergency simulation
- **Visual Alerts**: Flashing animations and priority handling
- **Automatic Resolution**: 10-second emergency resolution
- **Coordination**: Emergency coordination messages

### **Real-time Communication**
- **ATC Messages**: Color-coded communication logs
- **Multiple Panels**: 6 operational communication stages
- **Message Filtering**: Filter by type, level, and aircraft
- **Historical Access**: Complete message history

### **Interactive UI**
- **Radar Display**: Animated radar sweep with aircraft tracking
- **Ground Operations**: Interactive airport layout
- **Flight Strips**: Active flight management
- **System Status**: Real-time system health monitoring

## 🔧 Configuration

### **Environment Variables**
```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=atc_system
DB_USER=postgres
DB_PASSWORD=password
DB_POOL_SIZE=20

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Data Pipeline Paths
AIRCRAFT_TYPES_PATH=../data-pipeline/dist/aircraft_types.json
AIRLINES_PATH=../data-pipeline/dist/airlines.json

# Event Bus Configuration
EVENT_CHANNEL=atc:events

# Development Flags
SKIP_DB=false
SKIP_REDIS=false
```

### **Database Setup**
```bash
# Create database
npm run db:create

# Run migrations
npm run db:migrate

# Seed reference data
npm run db:seed

# Full setup
npm run setup:full
```

## 📁 Project Structure

```
ATC-1/
├── atc-nextjs/                 # Main Next.js application
│   ├── src/
│   │   ├── app/                # Next.js App Router
│   │   │   ├── api/            # API endpoints
│   │   │   ├── globals.css     # All ATC styles
│   │   │   ├── layout.tsx      # Root layout
│   │   │   ├── page.tsx        # Main ATC system
│   │   │   ├── logs/           # Logs page
│   │   │   └── ground/         # Ground operations
│   │   ├── components/         # React components
│   │   │   ├── ATCSystem.tsx   # Main system controller
│   │   │   ├── Header.tsx      # System header
│   │   │   ├── RadarDisplay.tsx # Airspace radar
│   │   │   ├── RunwayDisplay.tsx # Runway information
│   │   │   ├── ControlPanels.tsx # Flight management
│   │   │   ├── Communications.tsx # ATC communications
│   │   │   ├── ControlButtons.tsx # System controls
│   │   │   ├── AircraftSelector.tsx # Aircraft generation
│   │   │   └── GroundMapYYZ.tsx # Ground operations
│   │   ├── types/             # TypeScript interfaces
│   │   │   └── atc.ts         # ATC data structures
│   │   └── utils/             # Utility functions
│   ├── lib/                   # Database and event bus
│   │   ├── database.ts         # PostgreSQL integration
│   │   └── eventBus.ts        # Redis event bus
│   ├── database/              # Database schema
│   │   └── schema.sql          # Complete database schema
│   ├── scripts/               # Database scripts
│   │   ├── setup-db.js        # Database setup
│   │   ├── migrate.js         # Schema migrations
│   │   └── seed.js            # Data seeding
│   └── package.json           # Dependencies and scripts
├── data-pipeline/             # Python data processing
│   ├── src/                   # Python source code
│   ├── dist/                   # Processed data files
│   └── requirements.txt        # Python dependencies
└── overview.md               # This overview document
```

## 🚀 Getting Started

### **Prerequisites**
- Node.js 18+
- PostgreSQL 12+
- Redis 6+
- Python 3.8+ (for data pipeline)

### **Quick Start**
```bash
# Clone and navigate to project
cd ATC-1/atc-nextjs

# Install dependencies
npm install

# Setup environment
cp env.example .env
# Edit .env with your database settings

# Initialize database
npm run setup:full

# Start development server
npm run dev

# Open http://localhost:3000
```

### **Available Scripts**
```bash
# Development
npm run dev              # Start development server
npm run build            # Build for production
npm run start            # Start production server
npm run lint             # Run ESLint

# Database
npm run db:setup         # Setup database
npm run db:migrate       # Run migrations
npm run db:seed          # Seed data
npm run db:reset         # Reset and reseed

# System
npm run health           # Check system health
npm run setup:full       # Full setup with database
```

## 🔍 System URLs

### **Main Application**
- **ATC System**: http://localhost:3000
- **Ground Operations**: http://localhost:3000/ground
- **Logs/History**: http://localhost:3000/logs
- **Test Page**: http://localhost:3000/test

### **API Endpoints**
- **Health Check**: http://localhost:3000/api/health
- **Aircraft List**: http://localhost:3000/api/aircraft
- **Events**: http://localhost:3000/api/events
- **Event Stream**: http://localhost:3000/api/events/stream

## 📈 Performance Features

### **Database Optimization**
- **Connection Pooling**: Configurable pool size (default: 20)
- **Comprehensive Indexing**: Optimized queries for all tables
- **JSONB Support**: Flexible data storage with efficient queries
- **Transaction Management**: ACID compliance for data integrity

### **Real-time Performance**
- **Redis Pub/Sub**: Efficient event distribution
- **SSE Streaming**: Minimal overhead for real-time updates
- **Event Filtering**: Server-side filtering to reduce bandwidth
- **Connection Management**: Automatic reconnection and error handling

### **Frontend Optimization**
- **React Hooks**: Efficient state management
- **Component Optimization**: Minimal re-renders
- **CSS Grid**: Efficient layout system
- **Lazy Loading**: On-demand component loading

## 🔒 Security Features

### **Database Security**
- **Environment-based Configuration**: No hardcoded credentials
- **SQL Injection Prevention**: Parameterized queries
- **Connection Security**: Secure database connections
- **Input Validation**: Comprehensive data validation

### **API Security**
- **Input Sanitization**: XSS protection
- **Error Handling**: Secure error messages
- **Rate Limiting**: Built-in request limiting
- **CORS Configuration**: Proper cross-origin handling

## 📊 Monitoring and Health

### **Health Checks**
- **Database Connection**: PostgreSQL health monitoring
- **Redis Connection**: Redis health monitoring
- **System Status**: Overall system health
- **API Endpoints**: Individual service health

### **Logging System**
- **Event Logging**: Comprehensive event tracking
- **Error Logging**: Detailed error information
- **Performance Metrics**: System performance tracking
- **Audit Trail**: Complete system activity log

## 🎯 Use Cases

### **Air Traffic Control Simulation**
- **Training**: ATC controller training and simulation
- **Education**: Aviation education and learning
- **Research**: Air traffic management research
- **Development**: ATC system development and testing

### **Real-time Monitoring**
- **System Health**: Real-time system status monitoring
- **Event Tracking**: Comprehensive event logging and analysis
- **Performance**: System performance monitoring and optimization
- **Debugging**: Development and debugging support

## 🔮 Future Enhancements

### **Planned Features**
- **WebSocket Support**: Bidirectional real-time communication
- **Advanced Filtering**: Enhanced event filtering and search
- **Performance Monitoring**: Detailed performance metrics
- **Automated Testing**: Comprehensive test suite
- **CI/CD Integration**: Automated deployment pipeline

### **Potential Extensions**
- **Multi-airport Support**: Support for multiple airports
- **Advanced AI**: Machine learning integration
- **Voice Integration**: Voice communication simulation
- **Mobile Support**: Mobile-responsive interface
- **Internationalization**: Multi-language support

## 📚 Documentation

### **Comprehensive Documentation System**
1. **understand.md** - Beginner's guide (545 lines)
2. **README.md** - Project overview (198 lines)
3. **guide.md** - Technical documentation (600+ lines)
4. **atc-nextjs/README.md** - Application documentation (235 lines)
5. **MIGRATION_SUMMARY.md** - Migration details
6. **PERSISTENCE_IMPLEMENTATION.md** - Database implementation
7. **overview.md** - This comprehensive overview

### **Additional Resources**
- **API Documentation**: Complete endpoint documentation
- **Database Schema**: Detailed schema documentation
- **Component Documentation**: React component documentation
- **Configuration Guide**: Environment and setup guide

---

This overview provides a comprehensive understanding of the ATC system architecture, technology stack, and implementation details. The system represents a modern, scalable approach to air traffic control simulation with real-time capabilities and interactive user interfaces.
