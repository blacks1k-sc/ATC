# Fix for Engine Ops Display Issue

## Problem
- Aircraft are being generated (visible in logs)
- Engine Ops page shows error: "column ai.sector does not exist"
- Aircraft not displaying in the Engine Ops table

## Solution Applied

### 1. Removed Sector Column from Database Query
**File**: `atc-nextjs/lib/database.ts`

Changed the SQL query to NOT select the `sector` column since it doesn't exist in the database.

### 2. Added Client-Side Sector Calculation
**File**: `atc-nextjs/src/app/engine-ops/page.tsx`

Added a function to calculate sector based on distance:
```javascript
const calculateSector = (distance: number | undefined): string => {
  if (!distance) return 'UNKNOWN';
  if (distance > 30) return 'ENTRY';     // > 30 NM
  if (distance > 10) return 'ENROUTE';   // 10-30 NM
  if (distance > 3) return 'APPROACH';   // 3-10 NM
  return 'RUNWAY';                        // 0-3 NM
};
```

This matches the airspace sector definitions exactly!

## How to Verify the Fix

### Step 1: Restart Next.js Server
The server should auto-reload, but if not:

```bash
# Kill existing Next.js process
pkill -f "next dev"

# Start fresh
cd /Users/nrup/ATC-1/atc-nextjs
npm run dev
```

### Step 2: Check the API
```bash
curl http://localhost:3000/api/aircraft | jq '.'
```

You should see aircraft data with no errors.

### Step 3: View Engine Ops Page
Navigate to: **http://localhost:3000/engine-ops**

You should now see:
- Aircraft listed in the table
- Sectors automatically calculated (ENTRY, ENROUTE, APPROACH, RUNWAY)
- All columns populated with data
- Real-time updates working

## Expected Behavior

Aircraft will be assigned to sectors based on their distance from the airport:
- **ENTRY**: > 30 NM from airport (blue)
- **ENROUTE**: 10-30 NM from airport (green)
- **APPROACH**: 3-10 NM from airport (yellow)
- **RUNWAY**: 0-3 NM from airport (red)

## If Still Not Working

### Check 1: Verify Next.js is Running
```bash
curl http://localhost:3000/api/health
```

Should return health status.

### Check 2: Check for Aircraft in Database
```bash
psql atc_system -c "SELECT id, callsign, position->>'lat' as lat, position->>'lon' as lon, distance_to_airport_nm FROM aircraft_instances WHERE status = 'active';"
```

### Check 3: View Browser Console
Open Developer Tools (F12) and check for JavaScript errors.

### Check 4: Restart Both Services
```bash
# Terminal 1: Restart Next.js
cd /Users/nrup/ATC-1/atc-nextjs
npm run dev

# Terminal 2: Engine should already be running
# If not:
cd /Users/nrup/ATC-1/atc-brain-python
./scripts/start_engine.sh
```

## What the Fix Does

Instead of storing the sector in the database (which requires migration), we:
1. Calculate sector dynamically based on `distance_to_airport_nm`
2. Apply it client-side when fetching aircraft
3. Use it for filtering and display

This is actually MORE accurate because:
- Sector updates automatically as aircraft moves
- No database schema changes needed
- Matches the exact sector boundaries defined in `yyz_sectors.json`

## Complete Table Features

The Engine Ops table now shows:
- ✅ ID, Callsign, Registration
- ✅ Aircraft Type & Wake Category  
- ✅ Airline ICAO & Name
- ✅ ICAO24 Transponder & Squawk
- ✅ GPS Position (Lat/Lon)
- ✅ Distance to Airport
- ✅ Altitude (FL + feet)
- ✅ Speed (knots)
- ✅ Heading (degrees)
- ✅ Vertical Speed (fpm)
- ✅ **Sector** (calculated from distance)
- ✅ Phase (CRUISE, DESCENT, etc.)
- ✅ Controller Assignment
- ✅ Last Event Fired
- ✅ Target Values (ALT/SPD/HDG)
- ✅ Status Badge

The fix is complete and should work immediately after Next.js reloads!


