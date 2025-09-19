'use client';

import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, Tooltip, CircleMarker } from 'react-leaflet';
import type { GeoJsonObject, Feature, Geometry } from 'geojson';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

import { calculateBoundsFromRunways } from '../utils/coordinateUtils';

// No hardcoded center or bbox - everything calculated from API data

type AnyFeature = Feature<Geometry, any>;

interface GroundMapYYZProps {
  airport?: string;
}

export default function GroundMapYYZ({ airport = 'CYYZ' }: GroundMapYYZProps) {
  const [data, setData] = useState<GeoJsonObject | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [mapCenter, setMapCenter] = useState<[number, number]>([43.675, -79.63]); // Default fallback

  // Fetch GeoJSON from our API
  useEffect(() => {
    const url = `/api/airport/${airport}`; // No hardcoded bbox - let API use default
    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((geo) => {
        setData(geo);
        
        // Calculate center dynamically from the actual API data
        if (geo.features && geo.features.length > 0) {
          const calculatedBounds = calculateBoundsFromRunways(geo.features);
          if (calculatedBounds) {
            const centerLat = (calculatedBounds.minLat + calculatedBounds.maxLat) / 2;
            const centerLon = (calculatedBounds.minLon + calculatedBounds.maxLon) / 2;
            setMapCenter([centerLat, centerLon]);
          }
        }
      })
      .catch((e) => setError(e.message || 'Failed to load'));
  }, [airport]);

  // Styling by feature tags - different themes
  // Style function for GeoJSON features (non-runways)
  const styleFn = useMemo(
    () =>
      ((feat: AnyFeature) => {
        const aeroway = feat.properties?.aeroway || feat.properties?.tags?.aeroway;
        const building = feat.properties?.building || feat.properties?.tags?.building;
        const highway = feat.properties?.highway || feat.properties?.tags?.highway;
        
        if (isDarkMode) {
          // Dark ATC theme
          if (aeroway === 'taxiway') {
            return { color: '#00b3ff', weight: 2, opacity: 0.8 };
          }
          if (aeroway === 'apron') {
            return { color: '#00ff00', weight: 1, fillColor: '#1a1a2e', fillOpacity: 0.3 };
          }
          if (building === 'terminal') {
            return { color: '#00ff00', weight: 2, fillColor: '#2a2a4e', fillOpacity: 0.7 };
          }
          // Highway/road styling - red with less thickness than taxiways
          if (highway) {
            return { color: '#ff4444', weight: 1, opacity: 0.7 };
          }
          return { color: '#00ff00', weight: 1, opacity: 0.6 };
        } else {
          // Light theme (original)
          if (aeroway === 'taxiway') {
            return { color: '#00b3ff', weight: 2, opacity: 0.7 };
          }
          if (aeroway === 'apron') {
            return { color: '#006400', weight: 1, fillColor: '#0b2b2b', fillOpacity: 0.5 };
          }
          if (building === 'terminal') {
            return { color: '#cccccc', weight: 1, fillColor: '#222', fillOpacity: 0.6 };
          }
          // Highway/road styling - red with less thickness than taxiways
          if (highway) {
            return { color: '#ff4444', weight: 1, opacity: 0.6 };
          }
          return { color: '#555', weight: 1, opacity: 0.5 };
        }
      }) as L.StyleFunction,
    [isDarkMode]
  );

  // Style function for runways with white highlight
  const runwayStyleFn = useMemo(
    () =>
      ((feat: AnyFeature) => {
        const aeroway = feat.properties?.aeroway || feat.properties?.tags?.aeroway;
        
        if (isDarkMode) {
          // Dark ATC theme - white highlight for runways
          return { 
            color: '#ffffff', 
            weight: 6, 
            opacity: 1.0, 
            lineCap: 'round',
            lineJoin: 'round'
          };
        } else {
          // Light theme - white highlight for runways
          return { 
            color: '#ffffff', 
            weight: 5, 
            opacity: 1.0,
            lineCap: 'round',
            lineJoin: 'round'
          };
        }
      }) as L.StyleFunction,
    [isDarkMode]
  );

  // Style function for runways with original green color
  const runwayGreenStyleFn = useMemo(
    () =>
      ((feat: AnyFeature) => {
        const aeroway = feat.properties?.aeroway || feat.properties?.tags?.aeroway;
        
        if (isDarkMode) {
          // Dark ATC theme - original green for runways
          return { 
            color: '#00ff00', 
            weight: 4, 
            opacity: 1.0, 
            lineCap: 'round',
            lineJoin: 'round'
          };
        } else {
          // Light theme - original green for runways
          return { 
            color: '#00ff00', 
            weight: 3, 
            opacity: 0.9,
            lineCap: 'round',
            lineJoin: 'round'
          };
        }
      }) as L.StyleFunction,
    [isDarkMode]
  );

  // Helper function to filter runways from data
  const getRunwayData = useMemo(() => {
    if (!data || !data.features) return null;
    return {
      ...data,
      features: data.features.filter((feat: AnyFeature) => 
        feat.properties?.aeroway === 'runway' || feat.properties?.tags?.aeroway === 'runway'
      )
    };
  }, [data]);

  // Helper function to filter non-runways from data
  const getNonRunwayData = useMemo(() => {
    if (!data || !data.features) return null;
    return {
      ...data,
      features: data.features.filter((feat: AnyFeature) => 
        feat.properties?.aeroway !== 'runway' && feat.properties?.tags?.aeroway !== 'runway'
      )
    };
  }, [data]);

  // Points (gates) as circle markers with labels
  const pointToLayer = (feat: AnyFeature, latlng: L.LatLng) => {
    const props = feat.properties || {};
    const ref = props.ref || props.tags?.ref || props.name || props.tags?.name || 'Gate';
    const marker = L.circleMarker(latlng, {
      radius: 4,
      color: isDarkMode ? '#00ff00' : '#222',
      weight: 1,
      fillColor: isDarkMode ? '#00ff00' : '#ffff00',
      fillOpacity: 0.9
    });
    marker.bindTooltip(ref, { 
      permanent: false, 
      direction: 'top', 
      offset: L.point(0, -6),
      className: isDarkMode ? 'dark-tooltip' : ''
    });
    return marker;
  };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* Back Button */}
      <button
        onClick={() => window.location.href = '/'}
        style={{
          position: 'absolute',
          top: 20,
          left: 20,
          zIndex: 10000,
          background: isDarkMode ? '#1a1a2e' : '#ffffff',
          color: isDarkMode ? '#00ff00' : '#000000',
          border: `1px solid ${isDarkMode ? '#00ff00' : '#000000'}`,
          borderRadius: '4px',
          padding: '6px 10px',
          fontFamily: 'monospace',
          fontSize: '11px',
          fontWeight: 'bold',
          cursor: 'pointer',
          boxShadow: isDarkMode ? '0 0 6px #00ff00' : '0 1px 4px rgba(0,0,0,0.2)',
          transition: 'all 0.3s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.02)';
          e.currentTarget.style.boxShadow = isDarkMode ? '0 0 8px #00ff00' : '0 2px 6px rgba(0,0,0,0.3)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = isDarkMode ? '0 0 6px #00ff00' : '0 1px 4px rgba(0,0,0,0.2)';
        }}
      >
        ← OPS
      </button>

      {/* Toggle Button */}
      <button
        onClick={() => setIsDarkMode(!isDarkMode)}
        style={{
          position: 'absolute',
          top: 20,
          right: 20,
          zIndex: 10000,
          background: isDarkMode ? '#1a1a2e' : '#ffffff',
          color: isDarkMode ? '#00ff00' : '#000000',
          border: `1px solid ${isDarkMode ? '#00ff00' : '#000000'}`,
          borderRadius: '4px',
          padding: '6px 10px',
          fontFamily: 'monospace',
          fontSize: '11px',
          fontWeight: 'bold',
          cursor: 'pointer',
          boxShadow: isDarkMode ? '0 0 6px #00ff00' : '0 1px 4px rgba(0,0,0,0.2)',
          transition: 'all 0.3s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.02)';
          e.currentTarget.style.boxShadow = isDarkMode ? '0 0 8px #00ff00' : '0 2px 6px rgba(0,0,0,0.3)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = isDarkMode ? '0 0 6px #00ff00' : '0 1px 4px rgba(0,0,0,0.2)';
        }}
      >
        {isDarkMode ? '🌙 ATC' : '☀️ MAP'}
      </button>

      <MapContainer
        center={mapCenter}
        zoom={14}
        minZoom={11}
        maxZoom={19}
        scrollWheelZoom
        style={{ 
          width: '100%', 
          height: '100%',
          background: isDarkMode ? '#1a1a2e' : '#ffffff'
        }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url={isDarkMode 
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          }
        />

        {error && (
          <div
            style={{
              position: 'absolute',
              zIndex: 9999,
              top: 12,
              left: 12,
              background: isDarkMode ? '#2a2a4e' : '#ffffff',
              color: isDarkMode ? '#ff6060' : '#ff0000',
              border: `1px solid ${isDarkMode ? '#ff6060' : '#ff0000'}`,
              padding: '6px 10px',
              borderRadius: 4,
              fontFamily: 'monospace',
              fontSize: '12px'
            }}
          >
            Data unavailable: {error}
          </div>
        )}

        {data && (
          <>
            {/* Render runways with white highlight (background layer) */}
            {getRunwayData && (
              <GeoJSON
                data={getRunwayData as GeoJsonObject}
                style={runwayStyleFn}
                // Optional: show some tooltips for runways
                onEachFeature={(feature, layer) => {
                  const props = (feature as AnyFeature).properties || {};
                  const label = props.ref || props.tags?.ref || props.name || props.tags?.name || 'Runway';
                  if (label && layer instanceof L.Path) {
                    layer.bindTooltip(String(label), { direction: 'auto' });
                  }
                }}
              />
            )}
            
            {/* Render runways with original green color (foreground layer) */}
            {getRunwayData && (
              <GeoJSON
                data={getRunwayData as GeoJsonObject}
                style={runwayGreenStyleFn}
                // Optional: show some tooltips for runways
                onEachFeature={(feature, layer) => {
                  const props = (feature as AnyFeature).properties || {};
                  const label = props.ref || props.tags?.ref || props.name || props.tags?.name || 'Runway';
                  if (label && layer instanceof L.Path) {
                    layer.bindTooltip(String(label), { direction: 'auto' });
                  }
                }}
              />
            )}
            
            {/* Render non-runway features (taxiways, aprons, terminals, gates) */}
            {getNonRunwayData && (
              <GeoJSON
                data={getNonRunwayData as GeoJsonObject}
                style={styleFn}
                pointToLayer={pointToLayer as any}
                // Optional: show some tooltips for polys/lines
                onEachFeature={(feature, layer) => {
                  const props = (feature as AnyFeature).properties || {};
                  const label =
                    props.ref ||
                    props.tags?.ref ||
                    props.name ||
                    props.tags?.name ||
                    props.aeroway ||
                    props.tags?.aeroway ||
                    props.building ||
                    props.tags?.building ||
                    props.highway ||
                    props.tags?.highway ||
                    (feature.geometry.type as string);
                  if (label && layer instanceof L.Path) {
                    layer.bindTooltip(String(label), { direction: 'auto' });
                  }
                }}
              />
            )}
          </>
        )}
      </MapContainer>
    </div>
  );
}
