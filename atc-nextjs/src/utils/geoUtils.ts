/**
 * Geographic utility functions for coordinate conversion and distance calculations.
 * Uses the same flat-earth approximation as the Python engine for consistency.
 */

// CYYZ VOR coordinates (airport center)
export const CYYZ_LAT = 43.6777;
export const CYYZ_LON = -79.6248;

/**
 * Calculate distance from aircraft to CYYZ airport using flat-earth approximation.
 * This matches the calculation used in the Python engine for consistency.
 * 
 * @param lat - Aircraft latitude in degrees
 * @param lon - Aircraft longitude in degrees
 * @param airportLat - Airport latitude (defaults to CYYZ)
 * @param airportLon - Airport longitude (defaults to CYYZ)
 * @returns Distance in nautical miles
 */
export function calculateDistanceToAirport(
  lat: number, 
  lon: number, 
  airportLat: number = CYYZ_LAT,
  airportLon: number = CYYZ_LON
): number {
  const deltaLat = lat - airportLat;
  const deltaLon = lon - airportLon;
  
  // Convert to nautical miles using flat-earth approximation
  // 1 degree latitude ≈ 60 NM
  const x_nm = deltaLon * 60 * Math.cos((airportLat * Math.PI) / 180);
  const y_nm = deltaLat * 60;
  
  return Math.sqrt(x_nm * x_nm + y_nm * y_nm);
}

/**
 * Calculate heading from one point to another.
 * 
 * @param fromLat - Starting latitude
 * @param fromLon - Starting longitude
 * @param toLat - Destination latitude
 * @param toLon - Destination longitude
 * @returns Heading in degrees (0-360)
 */
export function calculateHeading(
  fromLat: number,
  fromLon: number,
  toLat: number,
  toLon: number
): number {
  const dLon = (toLon - fromLon) * Math.PI / 180;
  const lat1 = fromLat * Math.PI / 180;
  const lat2 = toLat * Math.PI / 180;
  
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  
  let heading = Math.atan2(y, x) * 180 / Math.PI;
  return (heading + 360) % 360; // Normalize to 0-360
}

/**
 * Calculate sector based on distance from airport.
 * 
 * @param distance - Distance in nautical miles
 * @returns Sector name
 */
export function calculateSector(distance: number): string {
  if (distance > 30) return 'ENTRY';
  if (distance > 10) return 'ENROUTE';
  if (distance > 3) return 'APPROACH';
  return 'RUNWAY';
}

/**
 * Calculate glideslope altitude based on distance from airport.
 * Standard 3-degree glideslope approximation.
 * 
 * @param distance - Distance in nautical miles
 * @param airportElevation - Airport elevation in feet (defaults to CYYZ: 569 ft)
 * @returns Target altitude in feet
 */
export function calculateGlideslopeAltitude(
  distance: number, 
  airportElevation: number = 569
): number {
  // 3-degree glideslope: altitude = distance * 318 + airport_elevation
  // 318 ft per NM is the standard 3-degree glideslope
  return Math.max(airportElevation, distance * 318 + airportElevation);
}

/**
 * Generate realistic aircraft position for arrivals.
 * Uses proper distance calculation instead of hardcoded approximations.
 * 
 * @param flightType - Type of flight (ARRIVAL/DEPARTURE)
 * @returns Position object with calculated distance
 */
export function generateRealisticPosition(flightType: string = 'ARRIVAL'): {
  lat: number;
  lon: number;
  altitude_ft: number;
  heading: number;
  speed_kts: number;
  distance_to_airport_nm: number;
} {
  if (flightType === 'ARRIVAL') {
    // Generate aircraft at 70-80 NM from YYZ with proper distance calculation
    const targetDistance = Math.random() * 10 + 70; // 70-80 NM
    const bearing = Math.random() * 360; // Random direction around YYZ
    const bearingRad = (bearing * Math.PI) / 180;
    
    // Convert distance and bearing to lat/lon using proper calculation
    const lat = CYYZ_LAT + (targetDistance / 60) * Math.cos(bearingRad);
    const lon = CYYZ_LON + (targetDistance / (60 * Math.cos((CYYZ_LAT * Math.PI) / 180))) * Math.sin(bearingRad);
    
    // Calculate actual distance (should be close to targetDistance)
    const actualDistance = calculateDistanceToAirport(lat, lon);
    
    // Calculate heading toward YYZ with small variation
    const headingToYYZ = calculateHeading(lat, lon, CYYZ_LAT, CYYZ_LON);
    const headingVariation = (Math.random() - 0.5) * 30; // ±15 degrees variation
    const finalHeading = (headingToYYZ + headingVariation + 360) % 360;
    
    return {
      lat: lat,
      lon: lon,
      altitude_ft: Math.floor(Math.random() * 5000) + 20000, // 20,000-25,000 ft
      heading: Math.floor(finalHeading),
      speed_kts: Math.floor(Math.random() * 50) + 300, // 300-350 kts
      distance_to_airport_nm: actualDistance
    };
  } else {
    // Departures start at airport
    return {
      lat: CYYZ_LAT + (Math.random() - 0.5) * 0.01,
      lon: CYYZ_LON + (Math.random() - 0.5) * 0.01,
      altitude_ft: Math.floor(Math.random() * 1000) + 500, // 500-1500 ft
      heading: Math.floor(Math.random() * 360),
      speed_kts: Math.floor(Math.random() * 50) + 150, // 150-200 kts
      distance_to_airport_nm: calculateDistanceToAirport(
        CYYZ_LAT + (Math.random() - 0.5) * 0.01,
        CYYZ_LON + (Math.random() - 0.5) * 0.01
      )
    };
  }
}
