// Shared coordinate transformation utilities for consistent runway positioning
// between RunwayDisplay and GroundMapYYZ components

export interface BoundingBox {
  minLat: number;
  maxLat: number;
  minLon: number;
  maxLon: number;
}

// No hardcoded bounds - everything will be calculated from API data

/**
 * Transform geographic coordinates to CSS percentage coordinates
 * This ensures both RunwayDisplay and GroundMapYYZ use the same transformation
 */
export function geoToCssPercent(
  coord: [number, number], 
  bounds: BoundingBox
): { x: number; y: number } {
  const [lon, lat] = coord;
  
  const x = ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * 100;
  const y = ((bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat)) * 100;
  
  return { x, y };
}

/**
 * Calculate runway configuration from start and end coordinates
 * Uses consistent transformation for both components
 */
export function calculateRunwayConfig(
  startCoord: [number, number],
  endCoord: [number, number],
  ref: string,
  bounds: BoundingBox
) {
  const start = geoToCssPercent(startCoord, bounds);
  const end = geoToCssPercent(endCoord, bounds);
  
  // Calculate runway center, length, and angle
  const centerX = (start.x + end.x) / 2;
  const centerY = (start.y + end.y) / 2;
  const length = Math.sqrt(Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2));
  const angle = Math.atan2(end.y - start.y, end.x - start.x) * (180 / Math.PI);
  
  // Scale runways to fit better in the display area
  const scaleFactor = 0.8; // Scale down to fit better
  const widthPercent = Math.min(length * scaleFactor, 70); // Cap at 70% with scaling
  
  // Minimal margin to match ground map positioning
  const margin = 8; // 8% margin from edges
  
  return {
    style: {
      position: 'absolute' as const,
      top: `${Math.max(margin, Math.min(100-margin, centerY - 1))}%`,
      left: `${Math.max(margin, Math.min(100-margin, centerX - widthPercent/2))}%`,
      width: `${widthPercent}%`,
      height: '8px',
      transform: `rotate(${angle}deg)`,
      transformOrigin: 'center'
    },
    labelTop: `${Math.max(margin-2, Math.min(100-margin+2, centerY - 3))}%`,
    labelLeft: `${Math.max(margin-2, Math.min(100-margin+2, centerX - 5))}%`
  };
}

/**
 * Calculate bounding box from an array of runway features
 */
export function calculateBoundsFromRunways(features: any[]): BoundingBox | null {
  if (features.length === 0) return null;
  
  let minLat = Infinity, maxLat = -Infinity, minLon = Infinity, maxLon = -Infinity;
  
  features.forEach((feature) => {
    const geometry = feature.geometry;
    if (geometry && geometry.type === 'LineString' && 'coordinates' in geometry) {
      const coordinates = geometry.coordinates as [number, number][];
      coordinates.forEach((coord: [number, number]) => {
        const [lon, lat] = coord;
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
      });
    }
  });
  
  if (minLat === Infinity) return null;
  
  // Add some padding to the bounds
  const latPadding = (maxLat - minLat) * 0.1;
  const lonPadding = (maxLon - minLon) * 0.1;
  
  return {
    minLat: minLat - latPadding,
    maxLat: maxLat + latPadding,
    minLon: minLon - lonPadding,
    maxLon: maxLon + lonPadding
  };
}
