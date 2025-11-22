'use client';

import { Aircraft } from '@/types/atc';
import { useRef, useEffect, useState, useCallback } from 'react';

type LiveAircraft = {
  id: string;
  callsign: string;
  icao24?: string;
  lat: number;
  lon: number;
  altitude_ft?: number;
  heading?: number;
  speed_kts?: number;
  status?: string;
  controller?: string;
  phase?: string;
  squawk_code?: string;
  updatedAt: number;
};

const AIRCRAFT_EVENTS = {
  POSITION_UPDATED: 'aircraft.position_updated',
  CREATED: 'aircraft.created',
  STATUS_CHANGED: 'aircraft.status_changed',
} as const;

const SSE_ENDPOINT =
  '/api/events/stream?type=aircraft.position_updated&type=aircraft.created&type=aircraft.status_changed';

const BROADCAST_INTERVAL_MS = 200;
const STALE_TIMEOUT_MS = 30000;

interface RadarDisplayProps {
  aircraft: Aircraft[];
  emergencyAircraft: Aircraft | null;
  emergencyAlert: boolean;
}

export default function RadarDisplay({ aircraft, emergencyAircraft, emergencyAlert }: RadarDisplayProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [trackedCount, setTrackedCount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'open' | 'closed'>('connecting');

  const aircraftStateRef = useRef<Map<string, LiveAircraft>>(new Map());
  const needsBroadcastRef = useRef(false);
  const iframeReadyRef = useRef(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const sanitizeCallsign = useCallback((value?: string | null) => {
    if (!value) return 'UNK';
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed.toUpperCase() : 'UNK';
  }, []);

  const sanitizeIdentifier = useCallback((value: any): string | undefined => {
    if (value === undefined || value === null) return undefined;
    const text = String(value).trim();
    return text.length > 0 ? text : undefined;
  }, []);

  const toNumber = useCallback((value: any): number | undefined => {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = parseFloat(value);
      return Number.isFinite(parsed) ? parsed : undefined;
    }
    return undefined;
  }, []);

  const broadcastSnapshot = useCallback(() => {
    if (!iframeRef.current?.contentWindow) return;
    const snapshot = Array.from(aircraftStateRef.current.values()).map((item) => ({
      id: item.id,
      callsign: item.callsign,
      lat: item.lat,
      lon: item.lon,
      altitude_ft: item.altitude_ft,
      heading: item.heading,
      speed_kts: item.speed_kts,
      status: item.status,
      controller: item.controller,
      phase: item.phase,
      squawk_code: item.squawk_code,
      updatedAt: item.updatedAt,
      icao24: item.icao24,
    }));

    iframeRef.current.contentWindow.postMessage(
      {
        type: 'AIRCRAFT_SNAPSHOT',
        aircraft: snapshot,
      },
      '*',
    );

    setTrackedCount(snapshot.length);
  }, []);

  const upsertLiveAircraft = useCallback(
    (payload: LiveAircraft) => {
      const current = aircraftStateRef.current.get(payload.id);
      if (current) {
        aircraftStateRef.current.set(payload.id, { ...current, ...payload, updatedAt: Date.now() });
      } else {
        aircraftStateRef.current.set(payload.id, { ...payload, updatedAt: Date.now() });
      }
      needsBroadcastRef.current = true;
    },
    [],
  );

  const removeLiveAircraft = useCallback((id: string) => {
    if (aircraftStateRef.current.delete(id)) {
      needsBroadcastRef.current = true;
    }
  }, []);

  const buildLiveAircraft = useCallback(
    (source: any, positionOverride?: any): LiveAircraft | null => {
      if (!source) return null;

      const base = source.aircraft ?? source;
      const position = positionOverride || source.position || base.position || {};

      const lat = toNumber(position.lat);
      const lon = toNumber(position.lon);
      if (lat === undefined || lon === undefined) {
        return null;
      }

      const primaryId =
        sanitizeIdentifier(base.icao24) ??
        sanitizeIdentifier(base.callsign) ??
        sanitizeIdentifier(base.id ?? source.id ?? base.aircraft_id);
      if (!primaryId) return null;

      return {
        id: primaryId,
        callsign: sanitizeCallsign(base.callsign ?? source.callsign),
        icao24: sanitizeIdentifier(base.icao24),
        lat,
        lon,
        altitude_ft: toNumber(position.altitude_ft),
        heading: toNumber(position.heading),
        speed_kts: toNumber(position.speed_kts),
        status: base.status ?? source.status,
        controller: base.controller ?? source.controller,
        phase: base.phase ?? source.phase,
        squawk_code: base.squawk_code ?? source.squawk_code,
        updatedAt: Date.now(),
      };
    },
    [sanitizeCallsign, toNumber],
  );

  // Waypoint data - in a real app, this would come from an API
  const waypoints = [
    { name: 'ADREB', lat: 43.96306, lon: -79.76333, category: 'Common', altitude: 5058 },
    { name: 'AGBEK', lat: 43.55833, lon: -79.46806, category: 'Common', altitude: 8346 },
    { name: 'ALKUB', lat: 43.59444, lon: -79.36361, category: 'Common', altitude: 9757 },
    { name: 'APMAM', lat: 43.61028, lon: -79.55417, category: 'Common', altitude: 5246 },
    { name: 'BEFNI', lat: 43.80361, lon: -79.78861, category: 'Common', altitude: 13582 },
    { name: 'BERIG', lat: 43.56944, lon: -79.33361, category: 'Common', altitude: 6914 },
    { name: 'BLOOS', lat: 43.85194, lon: -79.87083, category: 'Common', altitude: 11833 },
    { name: 'BOBTA', lat: 43.81444, lon: -79.65861, category: 'Common', altitude: 12527 },
    { name: 'BORID', lat: 43.59361, lon: -79.56528, category: 'Common', altitude: 10110 },
    { name: 'BOXAN', lat: 43.35083, lon: -79.70639, category: 'Common', altitude: 11592 },
    { name: 'CALVY', lat: 43.80167, lon: -79.47833, category: 'Common', altitude: 9177 },
    { name: 'DAROG', lat: 43.89333, lon: -79.6025, category: 'Common', altitude: 9549 },
    { name: 'DEPRU', lat: 43.27889, lon: -79.92361, category: 'Common', altitude: 6190 },
    { name: 'DEPTU', lat: 43.92694, lon: -79.29444, category: 'Common', altitude: 11944 },
    { name: 'DULPA', lat: 43.56833, lon: -79.81694, category: 'Common', altitude: 9213 },
    { name: 'DUVUM', lat: 43.61333, lon: -79.43194, category: 'Common', altitude: 12395 },
    { name: 'APNUS', lat: 43.23639, lon: -79.09111, category: 'Common', altitude: 9492 },
    { name: 'EBDAL', lat: 43.78778, lon: -79.43833, category: 'Common', altitude: 8144 },
    { name: 'EBGAP', lat: 43.61667, lon: -79.35361, category: 'Common', altitude: 10798 },
    { name: 'EDLIB', lat: 43.74333, lon: -79.70917, category: 'Common', altitude: 8574 },
    { name: 'ELGYN', lat: 43.92167, lon: -79.43361, category: 'Common', altitude: 6093 },
    { name: 'ELTOT', lat: 43.74028, lon: -79.16111, category: 'Common', altitude: 5357 },
    { name: 'EMBOP', lat: 43.58611, lon: -79.52278, category: 'Common', altitude: 12379 },
    { name: 'ERBAN', lat: 43.55417, lon: -79.48111, category: 'Common', altitude: 9896 },
    { name: 'ERBUS', lat: 43.74611, lon: -79.72278, category: 'Common', altitude: 10230 },
    { name: 'FAYOL', lat: 43.55111, lon: -79.7825, category: 'Common', altitude: 11680 },
    { name: 'GUBAL', lat: 43.67222, lon: -79.26222, category: 'Common', altitude: 9987 },
    { name: 'GUBOV', lat: 43.60417, lon: -79.40139, category: 'Common', altitude: 5108 },
    { name: 'HOFFS', lat: 43.74361, lon: -79.72806, category: 'Common', altitude: 12247 },
    { name: 'IKBAM', lat: 43.58556, lon: -79.48917, category: 'Common', altitude: 9005 },
    { name: 'IKDOP', lat: 43.72028, lon: -79.42778, category: 'Common', altitude: 12892 },
    { name: 'IKMEX', lat: 43.47944, lon: -79.38444, category: 'Common', altitude: 11842 },
    { name: 'ILEGI', lat: 43.58944, lon: -79.245, category: 'Common', altitude: 6359 },
    { name: 'ILIMO', lat: 43.355, lon: -79.20556, category: 'Common', altitude: 14520 },
    { name: 'JNB39', lat: 43.66069, lon: -79.6232, category: 'Common', altitude: 7008 },
    { name: 'KEDIS', lat: 43.2325, lon: -79.83194, category: 'Common', altitude: 14626 },
    { name: 'KENBA', lat: 43.51278, lon: -79.26611, category: 'Common', altitude: 12445 },
    { name: 'KENGU', lat: 43.995, lon: -79.29389, category: 'Common', altitude: 6513 },
    { name: 'KIREX', lat: 43.72917, lon: -79.51889, category: 'Common', altitude: 5389 },
    { name: 'LESOD', lat: 43.49944, lon: -79.85167, category: 'Common', altitude: 6764 },
    { name: 'LINNG', lat: 43.3025, lon: -79.35472, category: 'Common', altitude: 12437 },
    { name: 'LISDU', lat: 43.78417, lon: -79.43833, category: 'Common', altitude: 7542 },
    { name: 'LOBKO', lat: 43.54833, lon: -79.78083, category: 'Common', altitude: 13004 },
    { name: 'LOBNI', lat: 43.80333, lon: -79.30806, category: 'Common', altitude: 7046 },
    { name: 'LORLI', lat: 43.71556, lon: -79.40611, category: 'Common', altitude: 7392 },
    { name: 'MALTN', lat: 43.71833, lon: -79.67333, category: 'Common', altitude: 10460 },
    { name: 'MERKI', lat: 43.42389, lon: -79.31333, category: 'Common', altitude: 5452 },
    { name: 'MESNO', lat: 43.41361, lon: -79.63139, category: 'Common', altitude: 9714 },
    { name: 'METLU', lat: 43.98833, lon: -79.50472, category: 'Common', altitude: 6960 },
    { name: 'MIDPA', lat: 43.82361, lon: -79.53944, category: 'Common', altitude: 9753 },
    { name: 'MIRUG', lat: 43.725, lon: -79.555, category: 'Common', altitude: 8683 },
    { name: 'MIZEN', lat: 43.44056, lon: -79.52833, category: 'Common', altitude: 12671 },
    { name: 'MODUL', lat: 43.59611, lon: -79.5175, category: 'Common', altitude: 10802 },
    { name: 'MUSET', lat: 43.36667, lon: -79.51667, category: 'Common', altitude: 9004 },
    { name: 'MUVOK', lat: 43.65417, lon: -79.69278, category: 'Common', altitude: 9080 },
    { name: 'MUXIG', lat: 43.28722, lon: -79.74611, category: 'Common', altitude: 8125 },
    // Landing waypoints
    { name: 'DULPA', lat: 43.47, lon: -79.26, category: 'Landing', altitude: 6495 },
    { name: 'FAYOL', lat: 43.44, lon: -79.43, category: 'Landing', altitude: 6239 },
    { name: 'CALVY', lat: 43.32, lon: -79.46, category: 'Landing', altitude: 4896 },
    { name: 'EBDAL', lat: 43.33, lon: -79.28, category: 'Landing', altitude: 4427 },
    { name: 'LOBKO', lat: 43.33, lon: -79.47, category: 'Landing', altitude: 3748 },
    { name: 'LISDU', lat: 43.47, lon: -79.26, category: 'Landing', altitude: 3636 },
    { name: 'VERKO', lat: 43.51, lon: -79.33, category: 'Landing', altitude: 9481 },
    { name: 'ROKTO', lat: 43.48, lon: -79.48, category: 'Landing', altitude: 4555 },
    { name: 'MIRUG', lat: 43.44, lon: -79.43, category: 'Landing', altitude: 3708 },
    { name: 'PILKI', lat: 43.4, lon: -79.39, category: 'Landing', altitude: 9867 },
    { name: 'BEFNI', lat: 43.43, lon: -79.33, category: 'Landing', altitude: 3170 },
    { name: 'AGBEK', lat: 44.0, lon: -79.59, category: 'Landing', altitude: 9548 },
    // Takeoff waypoints
    { name: 'YTP', lat: 43.4, lon: -79.39, category: 'Takeoff', altitude: 11933 },
    { name: 'MALTN', lat: 43.43, lon: -79.4, category: 'Takeoff', altitude: 4746 },
    { name: 'PEARSON', lat: 43.4, lon: -79.37, category: 'Takeoff', altitude: 11635 },
  ];

  const handleSearch = (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    const filtered = waypoints.filter(waypoint =>
      waypoint.name.toLowerCase().includes(query.toLowerCase())
    );
    
    setSearchResults(filtered);
    setShowSearchResults(filtered.length > 0);
  };

  const handleWaypointSelect = (waypoint: any) => {
    // Send message to iframe to trigger waypoint tooltip
    if (iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage({
        type: 'SEARCH_WAYPOINT',
        waypoint: waypoint
      }, '*');
    }
    
    setSearchQuery('');
    setShowSearchResults(false);
  };

  const handleGridToggle = () => {
    const newGridState = !showGrid;
    setShowGrid(newGridState);
    
    // Send message to iframe to toggle grid
    if (iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage({
        type: 'TOGGLE_GRID'
      }, '*');
    }
  };

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) {
      return;
    }

    const handleLoad = () => {
      iframeReadyRef.current = true;
      needsBroadcastRef.current = true;
      broadcastSnapshot();
    };

    iframe.addEventListener('load', handleLoad);
    return () => {
      iframe.removeEventListener('load', handleLoad);
    };
  }, [broadcastSnapshot]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      if (!iframeReadyRef.current) return;
      if (!needsBroadcastRef.current) return;
      needsBroadcastRef.current = false;
      broadcastSnapshot();
    }, BROADCAST_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [broadcastSnapshot]);

  useEffect(() => {
    const sweepInterval = window.setInterval(() => {
      const now = Date.now();
      let changed = false;

      aircraftStateRef.current.forEach((value, key) => {
        if (now - value.updatedAt > STALE_TIMEOUT_MS) {
          aircraftStateRef.current.delete(key);
          changed = true;
        }
      });

      if (changed) {
        needsBroadcastRef.current = true;
      }
    }, Math.max(5000, STALE_TIMEOUT_MS / 4));

    return () => {
      window.clearInterval(sweepInterval);
    };
  }, []);

  useEffect(() => {
    const abortController = new AbortController();
    let cancelled = false;

    const loadInitialAircraft = async () => {
      try {
        const response = await fetch('/api/aircraft', { signal: abortController.signal });
        if (!response.ok) {
          throw new Error('Failed to fetch aircraft');
        }

        const payload = await response.json();
        if (cancelled) return;

        const activeAircraft = Array.isArray(payload?.aircraft) ? payload.aircraft : [];
        activeAircraft.forEach((item: any) => {
          const live = buildLiveAircraft(item);
          if (live) {
            upsertLiveAircraft(live);
          }
        });
      } catch (error: any) {
        if (error?.name === 'AbortError') {
          return;
        }
        console.error('RadarDisplay: failed to load initial aircraft', error);
      }
    };

    loadInitialAircraft();

    return () => {
      cancelled = true;
      abortController.abort();
    };
  }, [buildLiveAircraft, upsertLiveAircraft]);

  useEffect(() => {
    setConnectionStatus('connecting');
    const source = new EventSource(SSE_ENDPOINT);
    eventSourceRef.current = source;

    source.onopen = () => {
      setConnectionStatus('open');
    };

    source.onerror = (error) => {
      console.error('RadarDisplay SSE error', error);
      setConnectionStatus('connecting');
    };

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const eventType: string | undefined = payload?.type;
        const data = payload?.data;
        if (!eventType) return;

        if (eventType === AIRCRAFT_EVENTS.POSITION_UPDATED) {
          const live = buildLiveAircraft(data?.aircraft, data?.position);
          if (live) {
            upsertLiveAircraft(live);
          }
        } else if (eventType === AIRCRAFT_EVENTS.CREATED) {
          const live = buildLiveAircraft(data?.aircraft);
          if (live) {
            upsertLiveAircraft(live);
          }
        } else if (eventType === AIRCRAFT_EVENTS.STATUS_CHANGED) {
          const newStatus: string | undefined = data?.newStatus;
          const aircraftPayload = data?.aircraft;
          const candidateIds = [
            sanitizeIdentifier(aircraftPayload?.icao24),
            sanitizeIdentifier(aircraftPayload?.callsign),
            sanitizeIdentifier(aircraftPayload?.id ?? data?.aircraft_id),
          ];
          const resolvedId = candidateIds.find(Boolean);

          if (typeof newStatus === 'string' && newStatus !== 'active') {
            if (resolvedId) {
              removeLiveAircraft(resolvedId);
            }
            return;
          }

          const live = buildLiveAircraft(aircraftPayload);
          if (live) {
            if (typeof newStatus === 'string') {
              live.status = newStatus;
            }
            upsertLiveAircraft(live);
          }
        }
      } catch (error) {
        console.error('RadarDisplay: failed to parse SSE payload', error);
      }
    };

    return () => {
      source.close();
      if (eventSourceRef.current === source) {
        eventSourceRef.current = null;
      }
    };
  }, [buildLiveAircraft, removeLiveAircraft, sanitizeIdentifier, upsertLiveAircraft]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'RADAR_READY') {
        iframeReadyRef.current = true;
        needsBroadcastRef.current = true;
        broadcastSnapshot();
        return;
      }

      if (event.data.type === 'WAYPOINT_FOUND') {
        // Handle successful waypoint location
        console.log('Waypoint found:', event.data.waypoint);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [broadcastSnapshot]);

  return (
    <div className="display-area" id="airspaceDisplay" style={{ position: 'relative' }}>
      {/* Interactive Map iframe */}
      <iframe
        ref={iframeRef}
        src="/radar-map.html"
        width="100%"
        height="100%"
        style={{
          border: 'none',
          borderRadius: '8px',
          position: 'absolute',
          top: 0,
          left: 0,
          zIndex: 1
        }}
        title="Radar Map"
      />

      {/* Search Overlay */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          zIndex: 4,
          background: 'rgba(0, 0, 0, 0.8)',
          borderRadius: '8px',
          padding: '10px',
          minWidth: '300px',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ color: '#00ff00', fontSize: '16px' }}>🔍</div>
          <input
            type="text"
            placeholder="Search waypoint (e.g., ADREB, BEFNI)"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              handleSearch(e.target.value);
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'white',
              outline: 'none',
              flex: 1,
              fontSize: '14px',
              padding: '4px 0'
            }}
          />
        </div>

        <div
          style={{
            marginTop: '6px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '11px',
            color: '#8fffa0',
          }}
        >
          <span>{trackedCount} aircraft</span>
          <span
            style={{
              color:
                connectionStatus === 'open'
                  ? '#00ff88'
                  : connectionStatus === 'connecting'
                  ? '#ffd166'
                  : '#ff6b6b',
            }}
          >
            {connectionStatus === 'open'
              ? 'Live'
              : connectionStatus === 'connecting'
              ? 'Connecting\u2026'
              : 'Offline'}
          </span>
        </div>
        
        {/* Search Results */}
        {showSearchResults && searchResults.length > 0 && (
          <div
            style={{
              marginTop: '8px',
              maxHeight: '200px',
              overflowY: 'auto',
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              paddingTop: '8px'
            }}
          >
            {searchResults.map((waypoint, index) => (
              <div
                key={index}
                onClick={() => handleWaypointSelect(waypoint)}
                style={{
                  padding: '6px 8px',
                  cursor: 'pointer',
                  borderRadius: '4px',
                  fontSize: '12px',
                  color: 'white',
                  background: 'transparent',
                  transition: 'background 0.2s',
                  border: '1px solid transparent'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(0, 255, 0, 0.1)';
                  e.currentTarget.style.borderColor = 'rgba(0, 255, 0, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.borderColor = 'transparent';
                }}
              >
                <div style={{ fontWeight: 'bold', color: '#00ff00' }}>
                  {waypoint.name}
                </div>
                <div style={{ color: '#ccc', fontSize: '11px' }}>
                  {waypoint.category} • {waypoint.altitude.toLocaleString()} ft
                </div>
                <div style={{ color: '#999', fontSize: '10px' }}>
                  {waypoint.lat.toFixed(5)}, {waypoint.lon.toFixed(5)}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {showSearchResults && searchResults.length === 0 && (
          <div
            style={{
              marginTop: '8px',
              padding: '8px',
              color: '#ff6b6b',
              fontSize: '12px',
              textAlign: 'center',
              borderTop: '1px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            No waypoints found
          </div>
        )}
      </div>

      {/* Grid Toggle Button - positioned beside zoom controls on the left */}
      <div
        style={{
          position: 'absolute',
          top: '10px',
          left: '50px', // Position to the right of zoom controls
          zIndex: 4,
          background: 'rgba(0, 0, 0, 0.8)',
          borderRadius: '8px',
          padding: '8px',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        <button
          onClick={handleGridToggle}
          style={{
            background: showGrid ? 'rgba(0, 255, 0, 0.2)' : 'rgba(255, 255, 255, 0.1)',
            border: showGrid ? '1px solid rgba(0, 255, 0, 0.5)' : '1px solid rgba(255, 255, 255, 0.2)',
            color: showGrid ? '#00ff00' : '#ffffff',
            padding: '8px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 'bold',
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = showGrid ? 'rgba(0, 255, 0, 0.3)' : 'rgba(255, 255, 255, 0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = showGrid ? 'rgba(0, 255, 0, 0.2)' : 'rgba(255, 255, 255, 0.1)';
          }}
        >
          <span style={{ fontSize: '14px' }}>⊞</span>
          {showGrid ? 'Hide Grid' : 'Show Grid'}
        </button>
      </div>

      {/* Emergency Alert Overlay */}
      {emergencyAlert && (
        <div
          className="emergency-alert-overlay"
          style={{
            position: 'absolute',
            top: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(255, 0, 0, 0.9)',
            color: 'white',
            padding: '10px 20px',
            borderRadius: '5px',
            fontSize: '16px',
            fontWeight: 'bold',
            zIndex: 3,
            animation: 'flash 1s infinite'
          }}
        >
          ⚠️ EMERGENCY: SWA1234 ENGINE FAILURE
        </div>
      )}

    </div>
  );
}
