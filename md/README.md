# ATC System - Next.js 14 + React + TypeScript

A pixel-perfect conversion of the static ATC HTML/CSS/JS interface into a modern Next.js 14 application with React and TypeScript.

## 🚀 Quick Start

```bash
# Navigate to the Next.js application
cd atc-nextjs

# Install dependencies
npm install

# Start the development server
npm run dev
```

## 🎮 Access the System

- **Main ATC System**: http://localhost:3000
- **Logs/History Page**: http://localhost:3000/logs
- **Ground Operations**: http://localhost:3000/ground
- **Test Page**: http://localhost:3000/test

## 🎛️ Features

### ATC Operations Center
- **Pixel-perfect recreation** of the original ATC interface
- **Live UTC system clock** that updates every second
- **Radar sweep animation** with authentic ATC visuals
- **Emergency simulation** with flashing alerts and priority handling
- **ATC communication logs** with color-coded departure (green) and arrival (red) messages
- **Flight strips** with active, emergency, and normal states
- **Ground layout** with runways, taxiways, terminals, and gates
- **Weather data** and NOTAMS display
- **System status indicators** for all AI controllers

### Interactive Controls
- **Start System**: Activate AI controllers and seed sample data
- **Add Aircraft**: Generate new aircraft and add to sequencing
- **Simulate Emergency**: Test emergency response with 10-second auto-resolution
- **Logs**: Access comprehensive ATC communication logs and history
- **Ground Ops**: Interactive airport map with runways, taxiways, and terminals

### Logs/History System
- **Comprehensive Logging**: Track all ATC communications with timestamps
- **Multi-Direction Support**: TX, RX, CPDLC, XFER, SYS communication types
- **Advanced Filtering**: Filter by direction type, search by callsign/transcript
- **Voice-Ready**: Audio playback support with transcript search
- **Color-Coded Messages**: Red for arrivals, green for departures, neutral for system
- **Mock Data Generation**: Generate realistic ATC communication logs
- **Neon Dark Theme**: Consistent with main ATC interface styling

### Enhanced Runway Display System
- **SVG-Based Rendering**: High-quality vector graphics for precise runway visualization
- **Exit Points**: Yellow dots showing where taxiways intersect runways for rapid exits
- **Departure Points**: Green DEP badges at runway thresholds for takeoff positions
- **Real Airport Data**: Uses OpenStreetMap data via Overpass API for accuracy
- **Neon Styling**: Glowing effects matching the ATC theme
- **Fitted Display**: Automatically scales and centers runways within the display pane
- **Geometry Processing**: Advanced line intersection algorithms for exit point detection

### Ground Operations System
- **Interactive Airport Map**: Full-featured map with runways, taxiways, terminals, and gates
- **Real Airport Data**: Uses OpenStreetMap data for accurate airport layouts
- **Dual View Modes**: Toggle between light map view and dark ATC-themed view
- **Runway Display**: Main OPS page shows airport runways with proper scaling
- **Navigation**: Easy navigation between Ground Ops and main OPS views
- **Live Data**: Real-time airport information from external APIs

## 🏗️ Architecture

### Frontend
- **ATC Interface**: Next.js 14 + React + TypeScript for modern, maintainable code
- **Pixel-perfect recreation** of the original ATC interface
- **Real-time updates** with React state management
- **TypeScript** for type safety and better development experience

## 📁 Project Structure

```
├── atc-nextjs/            # Next.js 14 + React + TypeScript application
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   │   ├── globals.css # All original CSS styles
│   │   │   ├── layout.tsx  # Root layout component
│   │   │   ├── page.tsx    # Main ATC system page
│   │   │   ├── logs/
│   │   │   │   └── page.tsx # Logs/History page
│   │   │   ├── ground/
│   │   │   │   ├── page.tsx # Ground Operations page
│   │   │   │   └── layout.tsx # Ground Operations layout
│   │   │   ├── api/
│   │   │   │   └── airport/
│   │   │   │       └── [icao]/
│   │   │   │           └── route.ts # Airport data API endpoint
│   │   │   └── test/
│   │   │       └── page.tsx # Test page for functionality verification
│   │   ├── components/    # React components
│   │   │   ├── ATCSystem.tsx      # Main system component (state management)
│   │   │   ├── Header.tsx         # Header with tabs and system status
│   │   │   ├── RadarDisplay.tsx   # Airspace radar with sweep animation
│   │   │   ├── RunwayDisplay.tsx  # Airport runway display component
│   │   │   ├── GroundMapYYZ.tsx   # Interactive airport map component
│   │   │   ├── ControlPanels.tsx  # Flight strips, coordination, weather
│   │   │   ├── Communications.tsx # ATC message logs (6 panels)
│   │   │   └── ControlButtons.tsx # System control buttons
│   │   └── types/
│   │       └── atc.ts     # TypeScript interfaces and types
│   ├── package.json       # Dependencies and npm scripts
│   ├── tsconfig.json      # TypeScript configuration
│   ├── next.config.js     # Next.js configuration
│   ├── next-env.d.ts      # Next.js TypeScript declarations
│   ├── .eslintrc.json     # ESLint configuration
│   ├── README.md          # Next.js app documentation
│   ├── MIGRATION_SUMMARY.md # Detailed migration documentation
│   └── run.sh             # Quick start script
├── guide.md               # Detailed file-by-file documentation
└── README.md              # This file
```

## 🔧 Configuration

### Ports
- **Frontend (Next.js)**: 3000

## 🎯 Usage

1. **Start the system**: `cd atc-nextjs && npm run dev`
2. **Open ATC system**: http://localhost:3000
3. **Interact with system**: Use control buttons to manage traffic
4. **View logs**: Click LOGS button or press L key to access logs/history
5. **Ground operations**: Click GROUND OPS button to view interactive airport map
6. **Test functionality**: Visit http://localhost:3000/test

## 🚨 Emergency Simulation

The system includes a complete emergency simulation:
- Emergency aircraft declaration with flashing alerts
- Visual notifications and priority handling
- Emergency coordination messages
- Automatic resolution after 10 seconds

## 🛠️ Development

### Scripts
- `npm run dev` - Start Next.js development server
- `npm run build` - Build Next.js application for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run test` - Start test server on port 3001
- `npm run setup` - Install dependencies and start dev server

### Adding Features
- **UI Changes**: Modify components in `src/components/`
- **Data Structure**: Update types in `src/types/atc.ts`
- **Main Page**: Edit `src/app/page.tsx`
- **Styling**: Update `src/app/globals.css`

## 📊 System Status

The system provides real-time status indicators:
- **AI Controllers**: 4/4 Active
- **Radar**: Operational
- **Communications**: All Frequencies
- **Weather**: Monitored
- **Emergency**: Detection Active

## 🎨 Interface Design

The ATC Operations Center features:
- **Dark theme** with authentic ATC colors
- **Radar sweep animation** with neon glow effects
- **Airport ground layout** with runways and taxiways
- **Real-time communication logs** with color coding
- **Emergency alert system** with flashing animations
- **Controller status indicators** with pulsing lights

## 🔄 Real-time Updates

- **Aircraft position updates** with smooth animations
- **Communication message flow** with proper color coding
- **Emergency status changes** with visual alerts
- **System health monitoring** with status indicators
- **Weather condition updates** in real-time

## 🧪 Testing

- **Functionality Test**: Visit `/test` for system verification
- **All animations work**: Radar sweep, emergency flashing, aircraft movements
- **Emergency simulation**: Functions correctly with auto-resolution
- **Real-time clock**: Updates properly every second
- **ATC logs**: Display with correct styling and color coding

## 📝 License

This project is for educational and demonstration purposes.

## 🔄 Migration Status

✅ **Complete**: Static HTML/CSS/JS → Next.js 14 + React + TypeScript
- Pixel-perfect visual recreation
- All functionality preserved
- Modern architecture implemented
- TypeScript type safety added
- Component-based structure created
- Comprehensive documentation system

## 📚 Documentation System

The project now includes a complete documentation system with three levels:

1. **`understand.md`** - **Beginner's Guide** (Start here for complete beginners)
   - Explains every file and folder in simple terms
   - Real-world analogies and examples
   - Step-by-step learning path

2. **`README.md`** - **Project Overview** (This file - quick start and features)
   - Project overview and quick start
   - Feature list and architecture
   - Usage instructions

3. **`guide.md`** - **Technical Documentation** (For developers)
   - Detailed technical explanations
   - Component architecture
   - Development guidelines

4. **`atc-nextjs/README.md`** - **Application Documentation** (Next.js specific)
   - Next.js app structure
   - Component details
   - Development scripts

## 🎯 Current Project State

- **✅ Migration Complete**: All original functionality preserved
- **✅ Documentation Complete**: Four levels of documentation
- **✅ Development Ready**: Full Next.js 14 + React + TypeScript setup
- **✅ Testing Ready**: Test page and functionality verification
- **✅ Production Ready**: Build and deployment configuration
