'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { Feature, Geometry } from 'geojson';

type AnyFeature = Feature<Geometry, any>;

/* ---------------------------
   Types (lon/lat based)
---------------------------- */
type LonLat = [number, number];

interface RunwayDisplayProps {
  icao?: string;
  className?: string;
}

interface ExitPointLL {
  type: 'exit';
  lon: number;
  lat: number;
  meta?: any;
}

interface DeparturePointLL {
  type: 'departure';
  lon: number;
  lat: number;
  runwayRef?: string;
}

/* ---------------------------
   Utils: bbox + projector
---------------------------- */
function getFeatureCoords(f: AnyFeature): LonLat[] {
  // Overpass returns LineString for ways; sometimes MultiLineString
  const g = f.geometry;
  if (!g) return [];
  if (g.type === 'LineString') return (g.coordinates as number[][]) as LonLat[];
  if (g.type === 'MultiLineString') {
    const all = (g.coordinates as number[][][]).flat();
    return all as LonLat[];
  }
  // For nodes (gates), etc.
  if (g.type === 'Point') return [g.coordinates as LonLat];
  return [];
}

function bboxOf(features: AnyFeature[]) {
  let minLon = Number.POSITIVE_INFINITY,
      minLat = Number.POSITIVE_INFINITY,
      maxLon = Number.NEGATIVE_INFINITY,
      maxLat = Number.NEGATIVE_INFINITY;

  for (const f of features) {
    for (const [lon, lat] of getFeatureCoords(f)) {
      if (lon < minLon) minLon = lon;
      if (lat < minLat) minLat = lat;
      if (lon > maxLon) maxLon = lon;
      if (lat > maxLat) maxLat = lat;
    }
  }

  if (!isFinite(minLon) || !isFinite(minLat) || !isFinite(maxLon) || !isFinite(maxLat)) {
    // fallback bbox
    minLon = -79.65; minLat = 43.66;
    maxLon = -79.60; maxLat = 43.69;
  }
  return { minLon, minLat, maxLon, maxLat };
}

function makeProjector(
  paneW: number,
  paneH: number,
  bbox: { minLon: number; minLat: number; maxLon: number; maxLat: number },
  paddingPct = 0.06 // small padding → slightly zoomed out
) {
  const padW = paneW * paddingPct;
  const padH = paneH * paddingPct;
  const innerW = Math.max(1, paneW - padW * 2);
  const innerH = Math.max(1, paneH - padH * 2);

  const dLon = Math.max(1e-9, bbox.maxLon - bbox.minLon);
  const dLat = Math.max(1e-9, bbox.maxLat - bbox.minLat);

  return function project(lon: number, lat: number) {
    // x grows to the right with longitude, y grows down with inverted latitude
    const x = ((lon - bbox.minLon) / dLon) * innerW + padW;
    const y = ((bbox.maxLat - lat) / dLat) * innerH + padH;
    return { x, y };
  };
}

/* ---------------------------
   Geometry helpers
---------------------------- */
function lineSegIntersect(
  a1: LonLat, a2: LonLat, b1: LonLat, b2: LonLat
): LonLat | null {
  const [x1, y1] = a1, [x2, y2] = a2, [x3, y3] = b1, [x4, y4] = b2;
  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  if (Math.abs(denom) < 1e-12) return null;
  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom;
  const u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom;
  if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
    return [x1 + t * (x2 - x1), y1 + t * (y2 - y1)];
  }
  return null;
}

function clusterPointsLL<T extends { lon: number; lat: number }>(pts: T[], radiusMeters = 12): T[] {
  // Rough ~meters threshold using lat scale at YYZ; good enough to dedupe.
  const R = radiusMeters / 111_320; // ~deg per meter at equator
  const out: T[] = [];
  for (const p of pts) {
    const near = out.find(
      q => Math.abs(q.lon - p.lon) < R && Math.abs(q.lat - p.lat) < R
    );
    if (!near) out.push(p);
  }
  return out;
}

function bearingDeg(a: LonLat, b: LonLat) {
  const [lon1, lat1] = a.map(v => (v * Math.PI) / 180) as unknown as LonLat;
  const [lon2, lat2] = b.map(v => (v * Math.PI) / 180) as unknown as LonLat;
  const y = Math.sin(lon2 - lon1) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(lon2 - lon1);
  const brng = (Math.atan2(y, x) * 180) / Math.PI;
  return (brng + 360) % 360;
}

function deriveRunwayRef(a: LonLat, b: LonLat) {
  const brg = bearingDeg(a, b);
  const num1 = String(Math.round(brg / 10) % 36 || 36).padStart(2, '0');
  const num2 = String(((Math.round((brg + 180) / 10)) % 36) || 36).padStart(2, '0');
  return `${num1}/${num2}`;
}

/* ---------------------------
   Exit / DEP computation (lon/lat)
---------------------------- */
function computeExitPointsLL(runways: AnyFeature[], taxiways: AnyFeature[]): ExitPointLL[] {
  const exits: ExitPointLL[] = [];

  for (const rw of runways) {
    const rc = getFeatureCoords(rw);
    for (let i = 0; i < rc.length - 1; i++) {
      const a1 = rc[i], a2 = rc[i + 1];

      for (const tx of taxiways) {
        const tc = getFeatureCoords(tx);
        for (let j = 0; j < tc.length - 1; j++) {
          const b1 = tc[j], b2 = tc[j + 1];
          const hit = lineSegIntersect(a1, a2, b1, b2);
          if (hit) {
            exits.push({
              type: 'exit',
              lon: hit[0],
              lat: hit[1],
              meta: { runway: rw.properties?.ref, taxiway: tx.properties?.ref },
            });
          }
        }
      }
    }
  }

  return clusterPointsLL(exits, 10);
}

function computeDeparturePointsLL(runways: AnyFeature[]): DeparturePointLL[] {
  const out: DeparturePointLL[] = [];
  for (const rw of runways) {
    const coords = getFeatureCoords(rw);
    if (coords.length < 2) continue;
    const start = coords[0];
    const end = coords[coords.length - 1];
    const ref = rw.properties?.ref || deriveRunwayRef(start, end);
    out.push({ type: 'departure', lon: start[0], lat: start[1], runwayRef: ref });
    out.push({ type: 'departure', lon: end[0],   lat: end[1],   runwayRef: ref });
  }
  return out;
}

/* ---------------------------
   Component
---------------------------- */

export default function RunwayDisplay({
  icao = 'CYYZ',
  className = '',
}: RunwayDisplayProps) {
  const [runways, setRunways] = useState<AnyFeature[]>([]);
  const [taxiways, setTaxiways] = useState<AnyFeature[]>([]);
  const [exitLL, setExitLL] = useState<ExitPointLL[]>([]);
  const [depLL, setDepLL]   = useState<DeparturePointLL[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  // Measure panel
  const ref = useRef<HTMLDivElement>(null);
  const [pane, setPane] = useState({ w: 640, h: 480 });

  useLayoutEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(() => {
      const r = ref.current!.getBoundingClientRect();
      setPane({ w: Math.max(200, r.width), h: Math.max(200, r.height) });
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  // Fetch airport GeoJSON from your API route
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`/api/airport/${icao}`);
        if (!res.ok) throw new Error(`API ${res.status}`);
        const gj = await res.json();

        const rws = (gj.features ?? []).filter((f: AnyFeature) => f.properties?.aeroway === 'runway');
        const txs = (gj.features ?? []).filter((f: AnyFeature) => f.properties?.aeroway === 'taxiway');

        setRunways(rws);
        setTaxiways(txs);

        setExitLL(computeExitPointsLL(rws, txs));
        setDepLL(computeDeparturePointsLL(rws));
      } catch (e) {
        console.error(e);
        setError(e instanceof Error ? e.message : 'Load error');
        setRunways([]); setTaxiways([]); setExitLL([]); setDepLL([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [icao]);

  const bboxAll = useMemo(() => bboxOf([...runways, ...taxiways]), [runways, taxiways]);
  const project = useMemo(() => makeProjector(pane.w, pane.h, bboxAll, 0.06), [pane, bboxAll]);

  if (loading) {
    return (
      <div ref={ref} className={`runway-pane ${className}`} style={{ width: '100%', height: '100%' }}>
        <div style={{ color: '#00ff00', fontFamily: 'monospace', fontSize: 12, display: 'grid', placeItems: 'center', height: '100%' }}>
          Loading airport data…
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div ref={ref} className={`runway-pane ${className}`} style={{ width: '100%', height: '100%' }}>
        <div style={{ color: '#ff6060', fontFamily: 'monospace', fontSize: 12, display: 'grid', placeItems: 'center', height: '100%', textAlign: 'center', padding: 16 }}>
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div ref={ref} className={`runway-pane ${className}`} style={{ width: '100%', height: '100%' }}>
      <svg className="runway-svg" width={pane.w} height={pane.h} viewBox={`0 0 ${pane.w} ${pane.h}`}>
        {/* RUNWAYS */}
        {runways.map((rw, i) => {
          const pts = getFeatureCoords(rw).map(([lon, lat]) => project(lon, lat));
          if (pts.length < 2) return null;
          const d = pts.map(p => `${p.x},${p.y}`).join(' ');
          return (
            <g key={`rw-${i}`}>
              <polyline points={d} stroke="#072a12" strokeWidth={10} opacity={0.28} fill="none" />
              <polyline points={d} stroke="#00ff66" strokeWidth={4} opacity={0.95} fill="none" style={{ filter: 'drop-shadow(0 0 6px #00ff66)' }} />
            </g>
          );
        })}

        {/* EXIT DOTS (thinned a bit for clarity) */}
        {exitLL.filter((_, idx) => idx % 2 === 0).map((p, i) => {
          const { x, y } = project(p.lon, p.lat);
          return <circle key={`ex-${i}`} cx={x} cy={y} r={3.2} fill="#ffff00" stroke="#222" strokeWidth={1} style={{ filter: 'drop-shadow(0 0 3px #ffff00)' }} />;
        })}

        {/* DEP MARKERS */}
        {depLL.map((p, i) => {
          const { x, y } = project(p.lon, p.lat);
          return (
            <g key={`dep-${i}`} transform={`translate(${x},${y})`}>
              <rect x={-7} y={-7} width={14} height={14} rx={3} fill="#00ffaa" stroke="#002" strokeWidth={1} style={{ filter: 'drop-shadow(0 0 3px #00ffaa)' }} />
              <text x={0} y={3} textAnchor="middle" fontSize={8} fill="#001" fontFamily="Courier New, monospace">DEP</text>
            </g>
          );
        })}

        {/* LABELS (smaller, centered) */}
        {runways.map((rw, i) => {
          const coords = getFeatureCoords(rw);
          if (coords.length < 2) return null;
          const mid = coords[Math.floor(coords.length / 2)];
          const start = coords[0], end = coords[coords.length - 1];
          const { x, y } = project(mid[0], mid[1]);
          const refText = rw.properties?.ref || deriveRunwayRef(start, end);
        return (
            <text
              key={`lbl-${i}`}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="central"
              fontFamily="Courier New, monospace"
              fontSize={11}                 // smaller labels
              fill="#7dffc8"
              style={{
                paintOrder: 'stroke',
                stroke: 'rgba(0,0,0,0.65)',
                strokeWidth: 2,
                letterSpacing: 0.4,
              }}
            >
              {refText}
            </text>
        );
      })}
      </svg>
    </div>
  );
}

/* ---------------------------
   Notes:
   - This version computes a bbox from the actual features and
     builds a lon/lat → SVG projector, so everything fits that panel.
   - Label size is smaller (11px) and auto-derived if OSM ref is missing.
   - Exit dots are thinned (every other point); tweak the filter as you like.
---------------------------- */