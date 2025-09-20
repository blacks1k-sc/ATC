'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import L, { GeoJSON as LGeoJSON, Layer, PathOptions, LatLng } from 'leaflet';
import type { Feature, FeatureCollection, Geometry, GeoJsonObject } from 'geojson';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

import { calculateBoundsFromRunways } from '../utils/coordinateUtils';

type AnyFeat = Feature<Geometry, Record<string, any>>;
type FC = FeatureCollection<Geometry, Record<string, any>>;

const featureId = (f: AnyFeat) =>
  (f.properties?.id as string) ||
  (f.properties?.['@id'] as string) ||
  `${f.geometry?.type}-${Math.random().toString(36).slice(2)}`;

const tooltipHTML = (p: Record<string, any>) => {
  const rows = Object.entries(p)
    .filter(([k]) => !k.startsWith('@')) // hide internal keys
    .map(([k, v]) => `<tr><td>${k}</td><td>${String(v)}</td></tr>`)
    .join('');
  return `<div class="dark-tooltip__inner"><table>${rows}</table></div>`;
};

const styleFor =
  (selectedId: string | null) =>
  (f: AnyFeat): PathOptions => {
    const t = f.properties?.aeroway;
    const id = featureId(f);
    const sel = selectedId && id === selectedId;

    if (t === 'runway')  return { color: sel ? '#00ffaa' : '#00ff66', weight: sel ? 5 : 4, opacity: 0.95 };
    if (t === 'taxiway') return { color: sel ? '#55ccff' : '#00b3ff', weight: sel ? 4 : 2.5, opacity: 0.85 };
    if (t === 'apron')   return { color: sel ? '#22aa88' : '#0b2b2b', weight: sel ? 3 : 2, fillColor: '#0b2b2b', fillOpacity: 0.5, opacity: 0.7 };
    if (f.properties?.building === 'terminal')
      return { color: sel ? '#eeeeee' : '#cccccc', weight: sel ? 2.5 : 1.5, fillColor: '#222', fillOpacity: 0.6, opacity: 0.9 };

    // roads (service/unclassified/etc.) keep your red theme
    if (f.properties?.highway)
      return { color: sel ? '#ff8080' : '#ff2d2d', weight: sel ? 2 : 1, opacity: 0.6 };

    return { color: '#444', weight: 1, opacity: 0.5 };
  };

// Keep only GATE nodes as points; strip other point features.
const onlyGatesForPoints = (fc: FC): FC => ({
  type: 'FeatureCollection',
  features: fc.features.map((f) => {
    if (f.geometry?.type === 'Point' && f.properties?.aeroway !== 'gate') {
      return { ...f, geometry: { type: 'Point', coordinates: [Infinity, Infinity] } as any }; // effectively hidden
    }
    return f;
  }),
});

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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const geoRef = useRef<LGeoJSON | null>(null);

  // Fetch GeoJSON from our API
  useEffect(() => {
    const url = `/api/airport/${airport}`; // No hardcoded bbox - let API use default
    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((geo) => {
        const filtered = onlyGatesForPoints(geo);
        setData(filtered);
        
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
        {...({ center: mapCenter } as any)}
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
          {...({ attribution: "&copy; OpenStreetMap contributors" } as any)}
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
            {/* Background aprons - non-interactive */}
            <GeoJSON
              data={{
                type: 'FeatureCollection',
                features: (data as any).features.filter((f: AnyFeat) => f.properties?.aeroway === 'apron')
              }}
              style={() => ({ 
                color: '#0b2b2b', 
                weight: 2, 
                fillColor: '#0b2b2b', 
                fillOpacity: 0.5, 
                opacity: 0.7 
              })}
              interactive={false}
            />
            
            {/* Interactive features (everything except aprons) */}
            <GeoJSON
              {...({ ref: geoRef, data: {
                type: 'FeatureCollection',
                features: (data as any).features.filter((f: AnyFeat) => f.properties?.aeroway !== 'apron')
              }, style: styleFor(selectedId) } as any)}
              pointToLayer={(feature: AnyFeat, latlng: LatLng) => {
                if (feature.properties?.aeroway === 'gate') {
                  return L.circleMarker(latlng, {
                    radius: 3.5,
                    color: '#111',
                    weight: 1,
                    fillColor: '#e6ff00',
                    fillOpacity: 0.95,
                  });
                }
                // hide any other points safely
                return L.circleMarker(latlng, { radius: 0, opacity: 0, fillOpacity: 0 });
              }}
              onEachFeature={(feature: AnyFeat, layer: Layer) => {
                layer.on('mouseover', (e: any) => {
                  const l = e.target;
                  const html = tooltipHTML(feature.properties || {});
                  l.bindTooltip(html, {
                    className: 'dark-tooltip',
                    sticky: true,
                    direction: 'top',
                    opacity: 0.95,
                  }).openTooltip();

                  // bump style on hover
                  const base = styleFor(selectedId)(feature);
                  const hover: PathOptions = { ...base, weight: (base.weight || 1) + 1, color: '#ffffff' };
                  // setStyle is only for Path layers
                  (l as any).setStyle?.(hover);
                  (l as any).bringToFront?.();
                });

                layer.on('mouseout', (e: any) => {
                  e.target.closeTooltip?.();
                  (geoRef.current as any)?.resetStyle?.(e.target);
                });

                layer.on('click', () => {
                  setSelectedId(featureId(feature));
                });
              }}
            />
          </>
        )}
      </MapContainer>
    </div>
  );
}
