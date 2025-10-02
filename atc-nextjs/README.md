# ATC Next.js Application

A comprehensive Air Traffic Control simulation system with real-time persistence, event streaming, and modern web technologies.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL 12+
- Redis 6+

### Installation

```bash
# Install dependencies
npm install

# Setup environment
cp env.example .env
# Edit .env with your database and Redis settings

# Initialize database
npm run setup:full

# Start development server
npm run dev

# Open http://localhost:3000
```

## 📁 Application Structure

### **Root Level Files**

- **`.next/`** - Next.js build output directory (auto-generated, contains compiled app)
- **`node_modules/`** - Project dependencies (auto-generated, contains React, Next.js, etc.)
- **`.eslintrc.json`** - ESLint configuration for code quality and style rules
- **`MIGRATION_SUMMARY.md`** - Detailed documentation of the migration from static HTML to Next.js
- **`next-env.d.ts`** - Next.js TypeScript declarations (auto-generated, provides Next.js types)
- **`next.config.js`** - Next.js configuration file for custom settings
- **`package.json`** - Project metadata, dependencies, and npm scripts
- **`package-lock.json`** - Dependency lock file (auto-generated, ensures consistent installs)
- **`README.md`** - This file - Next.js application documentation
- **`run.sh`** - Shell script to install dependencies and start dev server
- **`tsconfig.json`** - TypeScript compiler configuration

### `/src/app/`
- **`globals.css`** - All original ATC CSS styles (migrated from static HTML)
- **`layout.tsx`** - Root layout component (wraps entire application)
- **`page.tsx`** - Main ATC system page (renders ATCSystem component)
- **`logs/page.tsx`** - Logs/History page route (renders LogsPage component)
- **`test/page.tsx`** - Functionality test page (verifies system components work)

### `/src/components/`
- **`ATCSystem.tsx`** - Main system component (manages all state and business logic)
- **`Header.tsx`** - Header with tabs, system status, and live UTC clock
- **`RadarDisplay.tsx`** - Airspace radar with sweep animation and aircraft markers
- **`GroundLayout.tsx`** - Airport ground layout with runways, taxiways, terminals
- **`ControlPanels.tsx`** - Flight strips, coordination messages, weather data
- **`Communications.tsx`** - ATC message logs (6 operational panels + system status)
- **`ControlButtons.tsx`** - System control buttons (START, ADD AIRCRAFT, EMERGENCY, LOGS)
- **`LogsPage.tsx`** - Main logs/history page component
- **`LogsTable.tsx`** - Table display for log entries
- **`LogFilters.tsx`** - Filtering controls for logs
- **`stores/logsStore.ts`** - Zustand store for logs state management

### `/src/types/`
- **`atc.ts`** - TypeScript interfaces for all ATC data structures (Aircraft, FlightStrip, etc.)

## 🎯 Key Features

### Real-time Persistence
- **PostgreSQL Database**: Normalized schema with aircraft types, airlines, instances, and events
- **Redis Event Bus**: Real-time pub/sub messaging for live updates
- **REST API**: Full CRUD operations for aircraft management
- **SSE Streaming**: Server-Sent Events for real-time communication logs

### Interactive UI
- **Aircraft Generator**: Create aircraft with unique identifiers and specifications
- **Real-time Logs**: Live communication logs with filtering and search
- **Ground Map**: Interactive airport layout with aircraft positioning
- **Health Monitoring**: System status and connection indicators

### Advanced Features
- **Event System**: Comprehensive logging with multiple event types
- **Data Pipeline Integration**: Aircraft types and airlines from external sources
- **Environment-driven**: Fully configurable via environment variables
- **Connection Management**: Automatic reconnection and error handling

## 🛠️ Development

### Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run test` - Start test server on port 3001

### Database Scripts
- `npm run db:migrate` - Run database migrations
- `npm run db:seed` - Seed reference data
- `npm run db:reset` - Reset and reseed database
- `npm run setup:full` - Full setup with database
- `npm run health` - Check system health

### Adding Features
- **UI Changes**: Modify components in `src/components/`
- **Data Structure**: Update types in `src/types/atc.ts`
- **Main Page**: Edit `src/app/page.tsx`
- **Styling**: Update `src/app/globals.css`

## 🧪 Testing

- **Main System**: http://localhost:3001 (Note: Port 3000 was in use, so using 3001)
- **Logs/History**: http://localhost:3001/logs
- **Test Page**: http://localhost:3001/test
- **Health Check**: http://localhost:3001/api/health
- **Event Stream**: http://localhost:3001/api/events/stream

## 🔧 Configuration

All configuration is environment-driven. Copy `env.example` to `.env`:

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

# Development Flags
SKIP_DB=false
SKIP_REDIS=false
```

## 📡 API Endpoints

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

## 📚 Documentation System

The project includes a comprehensive four-level documentation system:

### **1. understand.md** - Beginner's Guide
- **Location**: `../understand.md`
- **For**: Complete beginners with no web development experience
- **Contains**: 545 lines of beginner-friendly explanations
- **Features**: Real-world analogies, step-by-step learning path

### **2. README.md** - Project Overview
- **Location**: `../README.md`
- **For**: Anyone wanting to understand and use the project
- **Contains**: 198 lines of project overview and quick start
- **Features**: Feature list, architecture, usage instructions

### **3. guide.md** - Technical Documentation
- **Location**: `../guide.md`
- **For**: Developers working on the project
- **Contains**: 600+ lines of detailed technical explanations
- **Features**: Component architecture, data flow, troubleshooting

### **4. README.md** - Application Documentation (This file)
- **Location**: `atc-nextjs/README.md`
- **For**: Developers working with the Next.js app specifically
- **Contains**: 130+ lines of Next.js app details
- **Features**: Component details, scripts, configuration

### **Additional Documentation**
- **Migration Summary**: `MIGRATION_SUMMARY.md` - Detailed migration documentation
- **File Structure**: All docs include accurate file structure based on actual repository scan

## 🔧 Configuration

- **TypeScript**: `tsconfig.json`
- **Next.js**: `next.config.js`
- **ESLint**: `.eslintrc.json`
- **Dependencies**: `package.json`

## 🎨 Styling

All styles are preserved in `src/app/globals.css`:
- CSS Grid layout for main system
- CSS custom properties for colors
- Keyframe animations for effects
- Component-specific styling
- Responsive design considerations

## 🔄 State Management

Centralized in `ATCSystem.tsx`:
- System activation state
- Aircraft data (airborne and ground)
- Flight strips management
- Emergency simulation logic
- Real-time clock updates
- ATC message handling

## 🚨 Emergency System

Complete emergency simulation:
- Emergency aircraft declaration
- Visual alerts and notifications
- Priority handling and coordination
- Automatic resolution after 10 seconds

## 📊 System Status

Real-time status indicators:
- AI Controllers: 4/4 Active
- Radar: Operational
- Communications: All Frequencies
- Weather: Monitored
- Emergency: Detection Active