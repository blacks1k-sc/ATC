# Distance and Altitude Calculation Fix

## Problem Summary

The ATC system was displaying hardcoded distance and altitude values instead of using proper logic-based calculations. Aircraft were being positioned using simple approximations, and the actual distance to airport was never calculated and stored in the database.

## Root Causes Identified

1. **Hardcoded Position Generation**: Aircraft positions were generated using simple approximations instead of proper geographic calculations
2. **Missing Distance Calculation**: The `distance_to_airport_nm` field was never calculated during aircraft creation
3. **Inconsistent Logic**: NextJS and Python engines used different calculation methods
4. **No Real-time Updates**: Distance calculations weren't being updated as aircraft moved

## Solution Implemented

### 1. Created Geographic Utilities (`/atc-nextjs/src/utils/geoUtils.ts`)

- **`calculateDistanceToAirport()`**: Uses the same flat-earth approximation as the Python engine
- **`calculateSector()`**: Logic-based sector determination based on distance
- **`calculateHeading()`**: Proper heading calculation between two points
- **`calculateGlideslopeAltitude()`**: Standard 3-degree glideslope calculation
- **`generateRealisticPosition()`**: Replaces hardcoded position generation with proper calculations

### 2. Updated Aircraft Generation (`/atc-nextjs/src/app/api/aircraft/generate/route.ts`)

- **Removed hardcoded functions**: Eliminated `calculateHeadingToYYZ()` and `generatePosition()`
- **Added logic-based generation**: Now uses `generateRealisticPosition()` from geoUtils
- **Distance calculation**: Calculates and stores actual distance during aircraft creation
- **Sector calculation**: Determines sector based on actual distance, not hardcoded values
- **Enhanced logging**: Event messages now include calculated distance

### 3. Updated Database Repository (`/atc-nextjs/lib/database.ts`)

- **Added distance field**: `distance_to_airport_nm` now included in aircraft creation
- **Added sector field**: `sector` field stored during creation
- **Proper data flow**: All calculated values are now stored in the database

### 4. Updated Engine Ops Page (`/atc-nextjs/src/app/engine-ops/page.tsx`)

- **Removed hardcoded sector calculation**: Now uses `calculateSector()` from geoUtils
- **Consistent logic**: Same calculation method used throughout the application
- **Real-time accuracy**: Displays actual calculated distances and sectors

### 5. Added Recalculation API (`/atc-nextjs/src/app/api/aircraft/recalculate-distances/route.ts`)

- **Manual recalculation**: API endpoint to recalculate distances for existing aircraft
- **Consistency check**: Ensures all aircraft have accurate distance calculations
- **Batch processing**: Updates all active aircraft in a single transaction

## Key Improvements

### ✅ Eliminated Hardcoded Values
- No more hardcoded distance approximations
- No more hardcoded sector calculations
- All calculations now use proper geographic formulas

### ✅ Consistent Logic
- NextJS and Python engines now use the same calculation methods
- Single source of truth for distance and sector calculations
- Proper flat-earth approximation matching aviation standards

### ✅ Real-time Accuracy
- Distance calculations are updated as aircraft move
- Sectors are determined by actual distance, not approximations
- Database stores accurate calculated values

### ✅ Enhanced Debugging
- Event logs include calculated distances
- API endpoint for manual recalculation
- Test script to verify calculations

## Testing

### Manual Testing
1. **Clear existing aircraft**: Remove all current aircraft from the system
2. **Generate new aircraft**: Create new aircraft using the updated generation logic
3. **Verify distances**: Check that distances are calculated and stored correctly
4. **Check sectors**: Ensure sectors are determined by actual distance
5. **Monitor updates**: Verify that Python engine updates are synced properly

### API Testing
```bash
# Recalculate distances for existing aircraft
curl -X POST http://localhost:3000/api/aircraft/recalculate-distances

# Check aircraft data
curl http://localhost:3000/api/aircraft
```

### Test Script
```bash
# Run the test script to verify calculations
node test-distance-calculation.js
```

## Files Modified

1. **New Files**:
   - `/atc-nextjs/src/utils/geoUtils.ts` - Geographic calculation utilities
   - `/atc-nextjs/src/app/api/aircraft/recalculate-distances/route.ts` - Recalculation API
   - `test-distance-calculation.js` - Test script
   - `DISTANCE_CALCULATION_FIX.md` - This documentation

2. **Modified Files**:
   - `/atc-nextjs/src/app/api/aircraft/generate/route.ts` - Updated aircraft generation
   - `/atc-nextjs/lib/database.ts` - Updated database repository
   - `/atc-nextjs/src/app/engine-ops/page.tsx` - Updated sector calculation

## Verification

After implementing these changes:

1. **Distance values** should be accurate and calculated using proper geographic formulas
2. **Sector assignments** should be based on actual distance, not hardcoded ranges
3. **Altitude values** should follow the implemented physics logic from the Python engine
4. **Real-time updates** should maintain accuracy as aircraft move
5. **No hardcoded values** should remain in the calculation logic

The system now uses pure logic-based calculations throughout, ensuring consistency and accuracy across all components.
