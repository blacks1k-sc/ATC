# Radar Implementation Documentation

## Overview

The ATC system implements a comprehensive radar display system that simulates real-world air traffic control radar screens. The radar system consists of both frontend visualization components and backend positioning/kinematics engines that work together to provide real-time aircraft tracking and display.

## Tech Stack

### Frontend (Next.js/React)
- **Framework**: Next.js 14 with React 18
- **Language**: TypeScript
- **Styling**: CSS3 with custom animations
- **State Management**: React hooks (useState, useEffect, useCallback)
- **Real-time Updates**: Server-Sent Events (SSE)

### Backend (Python)
- **Engine**: Custom Python kinematics engine
- **Database**: PostgreSQL with Prisma ORM
- **Real-time Communication**: WebSocket/SSE
- **Geographic Calculations**: Custom geo_utils module
- **Data Pipeline**: Custom aircraft data generation

## Core Files and Implementation

### 1. Frontend Radar Display Components

#### `/atc-nextjs/src/components/RadarDisplay.tsx`
**Purpose**: Main radar screen visualization component

**Key Features**:
- **Radar Circles**: 8 concentric circles (80px to 640px diameter) representing distance ranges
- **Degree Markings**: 12 compass bearings (0°, 30°, 60°, 90°, 120°, 150°, 180°, 210°, 240°, 270°, 300°, 330°)
- **Radar Sweep Animation**: 4-second rotating green wedge with conic gradient
- **Aircraft Markers**: Diamond-shaped markers with flight information labels
- **Emergency Handling**: Special highlighting for emergency aircraft

**Implementation Details**:
```typescript
interface RadarDisplayProps {
  aircraft: Aircraft[];
  emergencyAircraft: Aircraft | null;
  emergencyAlert: boolean;
}
```

**Radar Circles Configuration**:
```typescript
const radarCircles = [80, 160, 240, 320, 400, 480, 560, 640];
```

**Degree Markings Positioning**:
- Uses precise CSS positioning for 12 compass bearings
- Each mark positioned at specific percentages around the radar perimeter
- Green neon glow effect with text-shadow

#### `/atc-nextjs/src/app/globals.css` (Radar Styles)
**Radar Sweep Animation**:
```css
.radar-sweep-wedge {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 640px;
  height: 640px;
  transform-origin: center;
  animation: sweep 4s linear infinite;
  filter: drop-shadow(0 0 6px var(--neon));
}

.sweep-wedge {
  background: conic-gradient(from 0deg,
    rgba(0,255,0,0) 0deg, rgba(0,255,0,.02) 6deg, 
    rgba(0,255,0,.05) 12deg, rgba(0,255,0,.09) 18deg,
    rgba(0,255,0,.14) 22deg, rgba(0,255,0,.20) 26deg, 
    rgba(0,255,0,.28) 29deg, rgba(0,255,0,.38) 30.5deg,
    rgba(0,255,0,.65) 31.5deg, rgba(0,255,0,.9) 32.25deg, 
    rgba(0,255,0,1) 33deg, rgba(0,255,0,0) 33.2deg);
  mix-blend-mode: screen;
}

@keyframes sweep {
  from { transform: translate(-50%,-50%) rotate(0); }
  to { transform: translate(-50%,-50%) rotate(360deg); }
}
```

**Aircraft Markers**:
```css
.aircraft-airborne {
  position: absolute;
  width: 16px;
  height: 16px;
  background: #00ffff;
  transform: translate(-50%,-50%) rotate(45deg);
  cursor: pointer;
  transition: .3s;
}

.aircraft-airborne::before {
  content: '';
  position: absolute;
  inset: -3px;
  border: 1px solid #00ffff;
  transform: rotate(-45deg);
}
```

### 2. Aircraft Positioning and Coordinate Systems

#### `/atc-nextjs/src/types/atc.ts`
**Aircraft Interface**:
```typescript
export interface Aircraft {
  id: string;
  callsign: string;
  type: string;
  status: 'airborne' | 'ground' | 'taxiing' | 'takeoff' | 'emergency';
  position: {
    top: string;    // CSS percentage position
    left: string;   // CSS percentage position
  };
  label: {
    top: string;
    left: string;
    borderColor: string;
    content: string; // HTML content for flight info
  };
  route?: string;
  altitude?: string;
  heading?: string;
}
```

#### `/atc-nextjs/src/utils/coordinateUtils.ts`
**Geographic to CSS Coordinate Transformation**:
```typescript
export function geoToCssPercent(
  coord: [number, number], 
  bounds: BoundingBox
): { x: number; y: number } {
  const [lon, lat] = coord;
  
  const x = ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * 100;
  const y = ((bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat)) * 100;
  
  return { x, y };
}
```

### 3. Backend Kinematics Engine

#### `/atc-brain-python/engine/kinematics.py`
**Aircraft State Updates**:
- **Position Updates**: Uses `update_position()` function with heading and speed
- **Speed Updates**: Gradual acceleration/deceleration to target speeds
- **Heading Updates**: Smooth turns with realistic turn rates
- **Altitude Updates**: Controlled climbs and descents
- **Random Drift**: Realistic flight path variations

**Key Functions**:
```python
def update_aircraft_state(aircraft: Dict[str, Any], dt: float = DT) -> Dict[str, Any]:
    """Update complete aircraft state for one tick."""
    # Extract current state
    position = aircraft.get("position", {})
    lat = position.get("lat", 0.0)
    lon = position.get("lon", 0.0)
    altitude = position.get("altitude_ft", 0.0)
    speed = position.get("speed_kts", 0.0)
    heading = position.get("heading", 0.0)
    
    # Calculate distance to airport
    distance_nm = distance_to_airport(lat, lon)
    
    # Update speed, heading, altitude based on targets or drift
    # ... implementation details
```

#### `/atc-brain-python/engine/geo_utils.py`
**Geographic Calculations**:
```python
def update_position(lat: float, lon: float, heading_deg: float, 
                   speed_kts: float, dt: float = 1.0) -> Tuple[float, float]:
    """Update aircraft position using small-step Earth approximation."""
    # Convert speed to nautical miles per second
    speed_nm_per_sec = speed_kts / 3600.0
    
    # Distance traveled in this time step
    distance_nm = speed_nm_per_sec * dt
    
    # Convert heading to radians
    heading_rad = math.radians(heading_deg)
    
    # Calculate displacement in NM
    delta_north_nm = distance_nm * math.cos(heading_rad)
    delta_east_nm = distance_nm * math.sin(heading_rad)
    
    # Convert to lat/lon change
    delta_lat = delta_north_nm / NM_PER_DEGREE_LAT
    cos_lat = math.cos(math.radians(lat))
    delta_lon = delta_east_nm / (NM_PER_DEGREE_LAT * cos_lat)
    
    # Update position
    new_lat = lat + delta_lat
    new_lon = lon + delta_lon
    
    return new_lat, new_lon
```

### 4. Airspace Management

#### `/atc-brain-python/engine/airspace.py`
**Sector Management**:
- **ENTRY Sector**: 40-60 NM radius, 20,000-60,000 ft altitude
- **ENROUTE Sector**: 20-40 NM radius, 18,000-35,000 ft altitude  
- **APPROACH Sector**: 10-20 NM radius, 0-18,000 ft altitude
- **RUNWAY Sector**: 0-10 NM radius, 0-3,000 ft altitude

**Sector Detection**:
```python
def get_sector_by_position(self, distance_nm: float, altitude_ft: float) -> Optional[SectorDefinition]:
    """Determine sector based on distance and altitude."""
    for sector in sorted(self.sectors, key=lambda s: s.radius_nm_inner):
        if sector.radius_nm_inner <= distance_nm <= sector.radius_nm_outer:
            if sector.altitude_ft_min <= altitude_ft <= sector.altitude_ft_max:
                return sector
    return None
```

### 5. Real-time Data Flow

#### `/atc-nextjs/src/app/api/events/stream/route.ts`
**Server-Sent Events for Real-time Updates**:
- Streams aircraft position updates to frontend
- Handles emergency alerts and system status changes
- Maintains persistent connection for live radar updates

#### `/atc-nextjs/src/app/engine-ops/page.tsx`
**Engine Operations Interface**:
- Real-time aircraft data display
- Position, altitude, speed, heading information
- Sector filtering and status monitoring
- Auto-refresh every 1 second

### 6. Aircraft Data Generation

#### `/atc-nextjs/src/app/api/aircraft/generate/route.ts`
**Aircraft Spawn Logic**:
```typescript
function generatePosition(flightType: string = 'ARRIVAL'): { 
  lat: number; 
  lon: number; 
  altitude_ft: number; 
  heading: number; 
  speed_kts: number 
} {
  const baseLat = 43.6777;  // Toronto Pearson coordinates
  const baseLon = -79.6248;
  
  if (flightType === 'ARRIVAL') {
    // Start arrivals 30-50 NM away at cruise altitude
    const distance_nm = Math.random() * 20 + 30;
    const bearing = Math.random() * 360;
    const bearing_rad = (bearing * Math.PI) / 180;
    
    const lat = baseLat + (distance_nm / 60) * Math.cos(bearing_rad);
    const lon = baseLon + (distance_nm / (60 * Math.cos((baseLat * Math.PI) / 180))) * Math.sin(bearing_rad);
    
    return {
      lat, lon,
      altitude_ft: Math.floor(Math.random() * 10000) + 15000,
      heading: Math.floor(Math.random() * 360),
      speed_kts: Math.floor(Math.random() * 100) + 250
    };
  }
  // ... departure logic
}
```

## Radar Display Features

### Visual Elements
1. **Concentric Circles**: 8 distance range rings (10 NM intervals)
2. **Compass Bearings**: 12 degree markings around perimeter
3. **Radar Sweep**: Animated green wedge rotating every 4 seconds
4. **Aircraft Markers**: Diamond-shaped with flight information labels
5. **Emergency Indicators**: Red highlighting and flashing alerts

### Aircraft Information Display
Each aircraft marker shows:
- **Flight Number**: e.g., "UAL245", "AAL891"
- **Flight Level**: e.g., "FL350", "FL280"
- **Speed**: e.g., "M.82", "M.78"
- **Route**: e.g., "SFO-LAX", "APCH 25L"

### Real-time Updates
- **Position Updates**: 1 Hz update rate from backend engine
- **Sector Transitions**: Automatic sector detection and handoffs
- **Emergency Handling**: Immediate visual alerts and highlighting
- **Live Data**: Server-Sent Events for real-time radar updates

## Technical Implementation Notes

### Coordinate System
- **Geographic**: Latitude/Longitude (WGS84)
- **Display**: CSS percentage positioning
- **Transformation**: Custom geoToCssPercent utility function
- **Reference Point**: Toronto Pearson International Airport (CYYZ)

### Performance Optimizations
- **CSS Animations**: Hardware-accelerated transforms
- **React Optimization**: useCallback for event handlers
- **Real-time Updates**: Efficient SSE streaming
- **Memory Management**: Proper cleanup of intervals and event sources

### Error Handling
- **Network Failures**: Graceful degradation of real-time updates
- **Data Validation**: Type checking for aircraft position data
- **Emergency States**: Robust emergency aircraft handling
- **Fallback Modes**: Static display when engine is unavailable

## File Structure Summary

```
Frontend Components:
├── /atc-nextjs/src/components/RadarDisplay.tsx     # Main radar display
├── /atc-nextjs/src/components/ATCSystem.tsx        # System integration
├── /atc-nextjs/src/app/globals.css                 # Radar styling & animations
├── /atc-nextjs/src/types/atc.ts                    # Aircraft interfaces
├── /atc-nextjs/src/utils/coordinateUtils.ts        # Coordinate transformations
└── /atc-nextjs/src/app/engine-ops/page.tsx         # Operations interface

Backend Engine:
├── /atc-brain-python/engine/kinematics.py          # Aircraft state updates
├── /atc-brain-python/engine/geo_utils.py           # Geographic calculations
├── /atc-brain-python/engine/airspace.py            # Sector management
├── /atc-brain-python/engine/core_engine.py         # Main engine controller
└── /atc-brain-python/engine/state_manager.py       # State persistence

API Endpoints:
├── /atc-nextjs/src/app/api/aircraft/generate/      # Aircraft generation
├── /atc-nextjs/src/app/api/events/stream/          # Real-time updates
└── /atc-nextjs/src/app/api/aircraft/[id]/route.ts  # Aircraft management
```

This radar implementation provides a comprehensive, real-time air traffic control radar display system with accurate positioning, smooth animations, and professional-grade visual elements that closely simulate real-world ATC radar screens.
