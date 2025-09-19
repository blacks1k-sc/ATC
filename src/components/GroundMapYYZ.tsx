'use client';

import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, Tooltip, CircleMarker } from 'react-leaflet';
import type { GeoJsonObject, Feature, Geometry } from 'geojson';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// YYZ center + default bbox (keep in sync with API)
const YYZ_CENTER: [number, number] = [43.6777, -79.6248];
const YYZ_BBOX = [43.66, -79.65, 43.69, -79.60] as const;

type AnyFeature = Feature<Geometry, any>;

export default function GroundMapYYZ() {
  const [data, setData] = useState<GeoJsonObject | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch GeoJSON from our API
  useEffect(() => {
    const url = `/api/airport/CYYZ?bbox=${YYZ_BBOX.join(',')}`;
    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((geo) => setData(geo))
      .catch((e) => setError(e.message || 'Failed to load'));
  }, []);

  // Styling by feature tags
  const styleFn = useMemo(
    () =>
      ((feat: AnyFeature) => {
        const tags = feat.properties?.tags || {};
        // Runways: neon green outline
        if (tags.aeroway === 'runway') {
          return { color: '#00ff00', weight: 3, opacity: 0.9 };
        }
        // Taxiways: blue-ish
        if (tags.aeroway === 'taxiway') {
          return { color: '#00b3ff', weight: 2, opacity: 0.7 };
        }
        // Aprons: filled dark teal
        if (tags.aeroway === 'apron') {
          return { color: '#006400', weight: 1, fillColor: '#0b2b2b', fillOpacity: 0.5 };
        }
        // Terminals (buildings)
        if (tags.building === 'terminal') {
          return { color: '#cccccc', weight: 1, fillColor: '#222', fillOpacity: 0.6 };
        }
        // Default faint
        return { color: '#555', weight: 1, opacity: 0.5 };
      }) as L.StyleFunction,
    []
  );

  // Points (gates) as circle markers with labels
  const pointToLayer = (feat: AnyFeature, latlng: L.LatLng) => {
    const tags = feat.properties?.tags || {};
    const ref = tags.ref || tags.name || 'Gate';
    const marker = new CircleMarker(latlng, {
      radius: 4,
      color: '#222',
      weight: 1,
      fillColor: '#ffff00',
      fillOpacity: 0.9
    });
    marker.bindTooltip(ref, { permanent: false, direction: 'top', offset: L.point(0, -6) });
    return marker;
  };

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <MapContainer
        center={YYZ_CENTER}
        zoom={14}
        minZoom={11}
        maxZoom={19}
        scrollWheelZoom
        style={{ width: '100%', height: '100%' }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {error && (
          <div
            style={{
              position: 'absolute',
              zIndex: 9999,
              top: 12,
              left: 12,
              background: '#2a2a4e',
              color: '#ff6060',
              border: '1px solid #ff6060',
              padding: '6px 10px',
              borderRadius: 4
            }}
          >
            Data unavailable: {error}
          </div>
        )}

        {data && (
          <GeoJSON
            data={data as GeoJsonObject}
            style={styleFn}
            pointToLayer={pointToLayer as any}
            // Optional: show some tooltips for polys/lines
            onEachFeature={(feature, layer) => {
              const tags = (feature as AnyFeature).properties?.tags || {};
              const label =
                tags.ref ||
                tags.name ||
                tags.aeroway ||
                tags.building ||
                (feature.geometry.type as string);
              if (label && layer instanceof L.Path) {
                layer.bindTooltip(String(label), { direction: 'auto' });
              }
            }}
          />
        )}
      </MapContainer>
    </div>
  );
}
