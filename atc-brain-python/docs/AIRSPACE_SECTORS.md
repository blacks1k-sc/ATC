# Airspace Sectors - Multi-Sector ATC Operations

## Overview

The ATC system uses a **multi-sector airspace model** with concentric annuli (rings) around Toronto Pearson (CYYZ). Each sector has defined boundaries, altitude bands, and controller responsibilities.

## Sector Architecture

### Sector Definitions

```
┌─────────────────────────────────────────────────────────────────┐
│              AIRSPACE SECTORS AROUND CYYZ (YYZ)                 │
│                                                                 │
│     Center: 43.67667°N, 79.63056°W                             │
│     Elevation: 569 ft MSL                                       │
└─────────────────────────────────────────────────────────────────┘

                    ENTRY SECTOR (60 NM)
           ┌─────────────────────────────────────┐
           │  FL200-FL600 (20,000-60,000 ft)    │
           │  Controller: ENTRY_ATC               │
           │  Behavior: Random Drift             │
           │                                      │
           │       ENROUTE SECTOR (30 NM)        │
           │  ┌─────────────────────────────┐   │
           │  │ FL180-FL350 (18,000-35,000) │   │
           │  │ Controller: ENROUTE_ATC      │   │
           │  │ Behavior: Controlled Descent │   │
           │  │                               │   │
           │  │   APPROACH SECTOR (10 NM)    │   │
           │  │  ┌────────────────────────┐  │   │
           │  │  │ SFC-FL180 (0-18,000)  │  │   │
           │  │  │ Controller: APPROACH  │  │   │
           │  │  │ Behavior: Sequencing  │  │   │
           │  │  │                        │  │   │
           │  │  │  RUNWAY SECTOR (3 NM) │  │   │
           │  │  │ ┌──────────────────┐  │  │   │
           │  │  │ │ SFC-3000 ft      │  │  │   │
           │  │  │ │ Controller: TWR  │  │  │   │
           │  │  │ │ Behavior: Final  │  │  │   │
           │  │  │ │       🛬          │  │  │   │
           │  │  │ └──────────────────┘  │  │   │
           │  │  └────────────────────────┘  │   │
           │  └─────────────────────────────┘   │
           └─────────────────────────────────────┘
```

## Sector Specifications

### 1. ENTRY (Airspace Entry/Exit)
- **Type**: `ENTRY_EXIT`
- **Radial Bounds**: 30-60 NM from CYYZ
- **Altitude**: FL200-FL600 (20,000-60,000 ft MSL)
- **Controller**: `ENTRY_ATC`
- **Behavior**: Random drift with boundary reflection
- **Hysteresis**: 0.5 NM

**Movement Characteristics:**
- Heading drift: ±4° per second random walk
- Speed drift: ±5 kts within [250-350 kts]
- Altitude drift: ±200 fpm within sector band
- Boundary reflection: When reaching outer boundary (60 NM), heading reflects toward center ±20°

**Purpose**: Aircraft spawn in this sector and move randomly until captured by ENTRY_ATC (simulated). Once captured, they receive vectors toward entry fixes.

### 2. ENROUTE (En-Route Operations)
- **Type**: `ENROUTE`
- **Radial Bounds**: 10-30 NM from CYYZ
- **Altitude**: FL180-FL350 (18,000-35,000 ft MSL)
- **Controller**: `ENROUTE_ATC`
- **Behavior**: Controlled descent
- **Hysteresis**: 0.5 NM

**Movement Characteristics:**
- Target speed: 280-320 kts
- Glideslope start: 25 NM
- Descent rate: ~2000 fpm
- Vectors toward downwind/base legs

**Purpose**: Manage descent from cruise to approach altitude. Coordinate sequencing for approach handoff.

### 3. APPROACH (Approach/Departure Sequencing)
- **Type**: `APPROACH_DEPARTURE`
- **Radial Bounds**: 3-10 NM from CYYZ
- **Altitude**: Surface-FL180 (0-18,000 ft MSL)
- **Controller**: `APPROACH_ATC`
- **Behavior**: Approach sequencing
- **Hysteresis**: 0.3 NM

**Movement Characteristics:**
- Target speed: 180-220 kts
- Final intercept: ~8 NM
- Stabilized altitude: 3000 ft at outer marker
- Vectors to final approach course

**Purpose**: Vector aircraft to final approach course. Manage spacing and sequencing for runway operations.

### 4. RUNWAY (Runway Operations)
- **Type**: `RUNWAY_OPS`
- **Radial Bounds**: 0-3 NM from CYYZ
- **Altitude**: Surface-3000 ft AGL
- **Controller**: `TOWER_ATC`
- **Behavior**: Final approach
- **Hysteresis**: 0.2 NM

**Movement Characteristics:**
- Target speed: 140-170 kts
- Glideslope: 3° (standard ILS)
- Flare altitude: 50 ft AGL
- Touchdown: <50 ft AGL

**Purpose**: Final approach, landing clearance, and touchdown. Transfer to ground control after landing.

## Entry Fixes

Eight entry fixes are positioned at 30 NM radius around CYYZ:

| Fix Name | Bearing | Lat | Lon | Description |
|----------|---------|-----|-----|-------------|
| BOXUM | 000° (N) | 44.17767 | -79.63056 | North Entry |
| DUVOS | 045° (NE) | 44.03125 | -79.20739 | Northeast Entry |
| NUBER | 090° (E) | 43.67667 | -79.20739 | East Entry |
| KEDMA | 135° (SE) | 43.32209 | -79.20739 | Southeast Entry |
| PILMU | 180° (S) | 43.17667 | -79.63056 | South Entry |
| VERKO | 225° (SW) | 43.32209 | -80.05373 | Southwest Entry |
| IMEBA | 270° (W) | 43.67667 | -80.05373 | West Entry |
| RAGID | 315° (NW) | 44.03125 | -80.05373 | Northwest Entry |

## Handoff Thresholds

### ENTRY → ENROUTE
- **Distance**: 30.0 NM
- **Hysteresis**: 0.5 NM
- **Requires**: Inbound movement (distance decreasing)
- **Stable ticks**: 2 consecutive ticks

### ENROUTE → APPROACH
- **Distance**: 10.0 NM
- **Hysteresis**: 0.5 NM
- **Requires**: Inbound movement
- **Stable ticks**: 2 consecutive ticks

### APPROACH → RUNWAY
- **Distance**: 3.0 NM
- **Hysteresis**: 0.3 NM
- **Requires**: Inbound movement
- **Stable ticks**: 2 consecutive ticks

## Spawn Zones

### Arrivals
- **Sector**: ENTRY
- **Radius**: 40-60 NM (random within ring)
- **Altitude**: 25,000-35,000 ft MSL
- **Speed**: 280-350 kts
- **Bearing**: Random (0-360°)

### Departures (Future)
- **Sector**: RUNWAY
- **Radius**: <1 NM
- **Altitude**: 500-1500 ft MSL
- **Speed**: 150-200 kts

## Events

### Sector Events

#### `sector.captured`
Emitted when aircraft is first captured by a sector (stable inbound for 10s).

```json
{
  "type": "sector.captured",
  "data": {
    "sector": "ENTRY",
    "aircraft_id": 123,
    "callsign": "AC1234",
    "distance_nm": 55.2,
    "altitude_ft": 28000
  }
}
```

#### `sector.handoff`
Emitted when aircraft crosses sector boundary.

```json
{
  "type": "sector.handoff",
  "data": {
    "from_sector": "ENTRY",
    "to_sector": "ENROUTE",
    "aircraft_id": 123,
    "callsign": "AC1234",
    "distance_nm": 29.8
  }
}
```

#### `sector.boundary_reflection`
Emitted when aircraft bounces off outer boundary in ENTRY sector.

```json
{
  "type": "sector.boundary_reflection",
  "data": {
    "sector": "ENTRY",
    "aircraft_id": 123,
    "old_heading": 045,
    "new_heading": 225,
    "distance_nm": 60.1
  }
}
```

## Physics by Sector

### ENTRY Sector Physics
```python
# Random drift until captured
if not captured:
    heading += random.uniform(-4, 4)  # ±4° drift
    speed += random.uniform(-5, 5)    # ±5 kts drift
    altitude += random.uniform(-200, 200) / 60  # ±200 fpm
    
    # Boundary reflection at 60 NM
    if distance >= 60.0:
        heading = bearing_to_center + random.uniform(-20, 20)

# After capture, vector to entry fix
else:
    target_heading = bearing_to_entry_fix
    target_altitude = ENROUTE_band_upper  # FL350
    target_speed = 300
```

### ENROUTE Sector Physics
```python
# Controlled descent
target_speed = 280-320  # kts
target_altitude = glideslope_altitude(distance_nm)
target_heading = vector_to_downwind_leg

# Begin descent planning
if distance < 25:
    vertical_speed = -2000  # fpm
```

### APPROACH Sector Physics
```python
# Approach sequencing
target_speed = 180-220  # kts
target_heading = vector_to_final_course
target_altitude = 3000  # stabilized at outer marker

if distance < 8:
    # Intercept final
    target_heading = runway_heading
```

### RUNWAY Sector Physics
```python
# Final approach
target_speed = 140-170  # kts
target_altitude = glideslope_altitude_3deg(distance_nm)

if altitude_agl < 50:
    # Touchdown
    status = "landed"
    controller = "GROUND"
```

## Database Schema Updates

### aircraft_instances Table

New fields added:
```sql
sector VARCHAR(20) DEFAULT 'ENTRY',              -- Current sector
sector_entry_tick INTEGER,                        -- Tick when entered sector
sector_stable_ticks INTEGER DEFAULT 0,           -- Ticks stable in sector
last_distance_nm DECIMAL(8,2),                   -- Previous distance for inbound check
```

## Configuration

### Environment Variables
```bash
# Airspace configuration
AIRSPACE_CONFIG_PATH=airspace/yyz_sectors.json
```

### Config File Location
```
atc-brain-python/
  airspace/
    yyz_sectors.json          # Sector definitions
```

## State Flow

```
1. Aircraft Spawned
   ↓
2. Sector: ENTRY
   └─→ Random drift
   └─→ Boundary reflection at 60 NM
   └─→ sector.captured event (after 10s inbound)
   ↓
3. Sector: ENROUTE (cross 30 NM boundary)
   └─→ sector.handoff: ENTRY→ENROUTE
   └─→ Controlled descent begins
   └─→ Vector toward approach
   ↓
4. Sector: APPROACH (cross 10 NM boundary)
   └─→ sector.handoff: ENROUTE→APPROACH
   └─→ Sequencing for final
   └─→ Speed reduction
   ↓
5. Sector: RUNWAY (cross 3 NM boundary)
   └─→ sector.handoff: APPROACH→RUNWAY
   └─→ Final approach course
   └─→ Glideslope tracking
   ↓
6. Touchdown (<50 ft AGL)
   └─→ status: "landed"
   └─→ controller: "GROUND"
```

## Implementation Notes

### Hysteresis
- Prevents oscillation at boundaries
- Requires N consecutive ticks in new sector before handoff
- Buffer zone of 0.3-0.5 NM at boundaries

### Inbound Check
- Handoffs only occur when `distance_nm < last_distance_nm`
- Prevents spurious handoffs for aircraft maneuvering
- Stored in `last_distance_nm` field

### Phase vs Sector
- **Sector**: Geographic/controller responsibility (ENTRY, ENROUTE, APPROACH, RUNWAY)
- **Phase**: Flight phase (CRUISE, DESCENT, APPROACH, FINAL, TOUCHDOWN)
- Both are tracked independently

## Future Extensions

### ATC Controller Roles
Once ATC roles are implemented:
- `ENTRY_ATC`: Initial contact, vector to entry fixes
- `ENROUTE_ATC`: Descent management, sequencing
- `APPROACH_ATC`: Vectors to final, spacing
- `TOWER_ATC`: Landing clearance, runway assignment
- `GROUND_ATC`: Taxiway routing

### Real-World Integration
- Import actual FIR boundaries from NavCanada
- Use published waypoints and airways
- Integrate STAR (Standard Terminal Arrival) procedures
- Support multiple runway configurations

## References

- **YYZ Center**: 43.67667°N, 79.63056°W
- **Elevation**: 569 ft MSL
- **Magnetic Variation**: -10° (10°W)
- **Config File**: `atc-brain-python/airspace/yyz_sectors.json`
- **Module**: `atc-brain-python/engine/airspace.py`

