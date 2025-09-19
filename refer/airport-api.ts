// atc-nextjs/src/app/api/airport/[icao]/route.ts
import { NextRequest } from 'next/server';

// NOTE: dynamic import because osmtogeojson uses DOM types
async function osmToGeoJSON(osmJson: any) {
  const mod = await import('osmtogeojson');
  // @ts-ignore – library lacks proper types in some setups
  return mod.default(osmJson);
}

// Default YYZ bounding box (SWlat, SWlon, NElat, NElon) - expanded to ensure top-left coverage
const DEFAULT_BBOX = [43.62, -79.72, 43.70, -79.54];

export async function GET(req: NextRequest, { params }: { params: { icao: string } }) {
  const { searchParams } = new URL(req.url);
  const bboxParam = searchParams.get('bbox');

  const bbox =
    bboxParam?.split(',').map(Number)?.length === 4
      ? bboxParam.split(',').map(Number)
      : DEFAULT_BBOX;

  const [sLat, sLon, nLat, nLon] = bbox as [number, number, number, number];

  // Build Overpass QL - only airport service roads, not city roads
  const overpassQL = `
[out:json][timeout:40];
(
  way["aeroway"="runway"](${sLat},${sLon},${nLat},${nLon});
  way["aeroway"="taxiway"](${sLat},${sLon},${nLat},${nLon});
  way["aeroway"="apron"](${sLat},${sLon},${nLat},${nLon});
  node["aeroway"="gate"](${sLat},${sLon},${nLat},${nLon});
  way["building"="terminal"](${sLat},${sLon},${nLat},${nLon});
  relation["building"="terminal"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="service"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="unclassified"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="residential"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="track"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="footway"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="path"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="tertiary"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="secondary"](${sLat},${sLon},${nLat},${nLon});
  way["highway"="primary"](${sLat},${sLon},${nLat},${nLon});
);
out body geom;
  `.trim();

  try {
    const resp = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body: new URLSearchParams({ data: overpassQL }),
      // Edge caching (CDN) hint — feel free to tune later
      next: { revalidate: 900 } // ~15 min
    });

    if (!resp.ok) {
      const text = await resp.text();
      return new Response(JSON.stringify({ error: 'Overpass error', detail: text }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const osmJson = await resp.json();
    const geo = await osmToGeoJSON(osmJson);

    return new Response(JSON.stringify(geo), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        // Cache on the edge and allow SWR
        'Cache-Control': 'public, s-maxage=900, stale-while-revalidate=86400'
      }
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err?.message || 'Unknown error' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
