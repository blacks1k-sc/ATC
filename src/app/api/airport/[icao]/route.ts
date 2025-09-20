// atc-nextjs/src/app/api/airport/[icao]/route.ts
import { NextRequest } from 'next/server';

// NOTE: dynamic import because osmtogeojson uses DOM types
async function osmToGeoJSON(osmJson: any) {
  const mod = await import('osmtogeojson');
  // @ts-ignore – library lacks proper types in some setups
  return mod.default(osmJson);
}

// Default YYZ bounding box (SWlat, SWlon, NElat, NElon)
const DEFAULT_BBOX = [43.66, -79.65, 43.69, -79.60];

export async function GET(req: NextRequest, { params }: { params: { icao: string } }) {
  const { searchParams } = new URL(req.url);
  const bboxParam = searchParams.get('bbox');

  const bbox =
    bboxParam?.split(',').map(Number)?.length === 4
      ? bboxParam.split(',').map(Number)
      : DEFAULT_BBOX;

  // Build Overpass QL using aerodrome *area* (no city roads outside the fence)
  const icao = (params.icao || 'CYYZ').toUpperCase();

  const overpassQL = `
[out:json][timeout:60];

// Find the airport polygon by ICAO, then bind it as .a
area["aeroway"="aerodrome"]["icao"="${icao}"]->.a;

// Fallback if some airports miss ICAO (optional): uncomment to try IATA or name
// area["aeroway"="aerodrome"]["iata"="${icao}"]->.a;
// area["aeroway"="aerodrome"]["name"~"${icao}", i]->.a;

(
  // Core airport features
  way["aeroway"="runway"](area.a);
  way["aeroway"="taxiway"](area.a);
  way["aeroway"="apron"](area.a);
  node["aeroway"="gate"](area.a);

  // Terminals and related buildings
  way["building"="terminal"](area.a);
  relation["building"="terminal"](area.a);
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