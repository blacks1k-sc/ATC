'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import Link from 'next/link';
import { AtcLogEntry, LogDirection } from '@/types/atc';

// Direction badge component
function DirBadge({ d }: { d: LogDirection }) {
  const map: Record<LogDirection, { label: string; bg: string }> = {
    TX:   { label: 'TX',    bg: '#0f3' },
    RX:   { label: 'RX',    bg: '#09f' },
    CPDLC:{ label: 'CPDLC', bg: '#a0f' }, // purple
    XFER: { label: 'XFER',  bg: '#08f' }, // blue
    SYS:  { label: 'SYS',   bg: '#777' }, // gray
  };
  const { label, bg } = map[d];
  return (
    <span style={{
      display:'inline-block', padding:'2px 6px', fontSize:10,
      border:'1px solid #004400', background:bg, color:'#000', borderRadius:3
    }}>{label}</span>
  );
}

// Event interface for SSE
interface SSEEvent {
  type: 'initial' | 'realtime' | 'initial_complete' | 'error';
  event?: any;
  count?: number;
  message?: string;
}

export default function Logs() {
  const [logs, setLogs] = useState<AtcLogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilters, setActiveFilters] = useState<Set<LogDirection>>(new Set(['TX', 'RX', 'CPDLC', 'XFER', 'SYS'] as LogDirection[]));
  const [arrivalFilter, setArrivalFilter] = useState<'all' | 'arrival' | 'departure'>('all');
  const [sectorFilter, setSectorFilter] = useState<Set<string>>(new Set(['TWR', 'GND', 'APP', 'CTR']));
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string>('');
  const eventSourceRef = useRef<EventSource | null>(null);
  
  const filteredLogs = useMemo(() => {
    return logs.filter(log => {
      // Filter by direction
      if (!activeFilters.has(log.direction)) return false;
      
      // Filter by arrival/departure
      if (arrivalFilter !== 'all') {
        if (arrivalFilter === 'arrival' && log.arrival !== true) return false;
        if (arrivalFilter === 'departure' && log.arrival !== false) return false;
      }
      
      // Filter by sector
      if (log.sector && !sectorFilter.has(log.sector)) return false;
      
      // Filter by search term
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        return (
          log.callsign?.toLowerCase().includes(searchLower) ||
          log.summary.toLowerCase().includes(searchLower) ||
          log.transcript?.toLowerCase().includes(searchLower)
        );
      }
      
      return true;
    });
  }, [logs, searchTerm, activeFilters, arrivalFilter, sectorFilter]);

  // Convert database event to AtcLogEntry
  const convertEventToLog = (event: any): AtcLogEntry => {
    return {
      id: event.id.toString(),
      ts: event.timestamp,
      callsign: event.aircraft?.callsign || event.callsign,
      sector: event.sector,
      frequency: event.frequency,
      direction: event.direction || 'SYS',
      summary: event.message,
      arrival: event.details?.arrival,
      flight: event.aircraft ? {
        type: event.aircraft.aircraft_type?.icao_type,
        from: event.details?.from,
        to: event.details?.to,
        squawk: event.aircraft.squawk_code
      } : undefined,
      audioUrl: event.details?.audioUrl,
      transcript: event.details?.transcript,
      handoffFrom: event.details?.handoffFrom,
      handoffTo: event.details?.handoffTo
    };
  };

  // Load initial events and setup SSE
  useEffect(() => {
    const loadInitialEvents = async () => {
      try {
        setLoading(true);
        setError('');
        
        // Build query parameters
        const params = new URLSearchParams();
        params.set('limit', '100');
        if (activeFilters.size < 5) {
          // If not all directions are selected, we'd need to filter on the server
          // For now, we'll load all and filter client-side
        }
        
        const response = await fetch(`/api/events?${params.toString()}`);
        if (!response.ok) {
          throw new Error('Failed to load events');
        }
        
        const data = await response.json();
        if (data.success) {
          const convertedLogs = data.events.map(convertEventToLog);
          setLogs(convertedLogs);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load events');
        console.error('Error loading initial events:', err);
      } finally {
        setLoading(false);
      }
    };

    loadInitialEvents();
  }, []);

  // Setup SSE connection
  useEffect(() => {
    const setupSSE = () => {
      try {
        // Build SSE URL with filters
        const params = new URLSearchParams();
        params.set('limit', '50');
        
        const eventSource = new EventSource(`/api/events/stream?${params.toString()}`);
        eventSourceRef.current = eventSource;
        
        eventSource.onopen = () => {
          setConnected(true);
          setError('');
        };
        
        eventSource.onmessage = (event) => {
          try {
            const data: SSEEvent = JSON.parse(event.data);
            
            if (data.type === 'initial') {
              // Add initial event
              const log = convertEventToLog(data.event);
              setLogs(prev => [log, ...prev]);
            } else if (data.type === 'realtime') {
              // Add real-time event
              const log = convertEventToLog(data.event);
              setLogs(prev => [log, ...prev]);
            } else if (data.type === 'initial_complete') {
              console.log(`Loaded ${data.count} initial events`);
            } else if (data.type === 'error') {
              setError(data.message || 'SSE error');
            }
          } catch (err) {
            console.error('Error parsing SSE event:', err);
          }
        };
        
        eventSource.onerror = (err) => {
          console.error('SSE error:', err);
          setConnected(false);
          setError('Connection lost');
          
          // Attempt to reconnect after 5 seconds
          setTimeout(() => {
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
            }
            setupSSE();
          }, 5000);
        };
        
      } catch (err) {
        console.error('Error setting up SSE:', err);
        setError('Failed to connect to real-time stream');
      }
    };

    setupSSE();

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  const handleGenerateMock = () => {
    // This is now handled by the real API, but we can keep it for testing
    console.log('Mock generation is now handled by the real API');
  };
  
  const toggleFilter = (direction: LogDirection) => {
    const newFilters = new Set(activeFilters);
    if (newFilters.has(direction)) {
      newFilters.delete(direction);
    } else {
      newFilters.add(direction);
    }
    setActiveFilters(newFilters);
  };
  
  const formatTime = (ts: string) => {
    return new Date(ts).toLocaleTimeString('en-US', {
      hour12: false,
      timeZone: 'UTC',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };
  
  const formatMessage = (log: AtcLogEntry) => {
    let message = log.summary;
    
    // Apply arrival/departure styling
    if (log.arrival === true) {
      message = message.replace(/ARRIVAL:/, '<span style="color: #ff4444; font-weight: bold;">ARRIVAL:</span>');
      // Highlight callsign and aircraft type with red glow
      const callsignMatch = log.callsign;
      if (callsignMatch) {
        message = message.replace(
          new RegExp(`(${callsignMatch})\\s*\\(([^)]+)\\)`, 'g'),
          '<span style="text-decoration: underline; text-shadow: 0 0 3px #ff4444; color: #ff4444;">$1 ($2)</span>'
        );
      }
    } else if (log.arrival === false) {
      message = message.replace(/DEPARTURE:/, '<span style="color: #00ff88; font-weight: bold;">DEPARTURE:</span>');
      // Highlight callsign and aircraft type with green glow
      const callsignMatch = log.callsign;
      if (callsignMatch) {
        message = message.replace(
          new RegExp(`(${callsignMatch})\\s*\\(([^)]+)\\)`, 'g'),
          '<span style="text-decoration: underline; text-shadow: 0 0 3px #00ff88; color: #00ff88;">$1 ($2)</span>'
        );
      }
    }
    
    return message;
  };
  
  return (
    <div style={{
      height: '100vh',
      background: '#0a0a1a',
      color: '#00ff00',
      fontFamily: 'Courier New, monospace',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        background: '#1a1a2e',
        padding: '10px 20px',
        borderBottom: '2px solid #00ff00',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Link href="/" style={{
            color: '#00ff00',
            textDecoration: 'none',
            padding: '5px 10px',
            border: '1px solid #00ff00',
            borderRadius: '3px',
            fontSize: '12px',
            transition: '0.3s'
          }}>
            ← OPS
          </Link>
          <h1 style={{ color: '#00ff00', fontSize: '18px', margin: 0 }}>COMMUNICATION LOGS</h1>
          
          {/* Connection Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: connected ? '#00ff00' : loading ? '#ffaa00' : '#ff4444',
              opacity: connected ? 1 : 0.7,
              transition: 'opacity 0.5s ease-in-out'
            }} />
            <span style={{
              fontSize: '10px',
              color: connected ? '#00ff00' : loading ? '#ffaa00' : '#ff4444'
            }}>
              {loading ? 'LOADING...' : connected ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>
          
          {error && (
            <div style={{
              fontSize: '10px',
              color: '#ff4444',
              background: '#2a1a1a',
              padding: '2px 6px',
              border: '1px solid #ff4444',
              borderRadius: '3px'
            }}>
              {error}
            </div>
          )}
        </div>
        
        {/* Top Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          {/* Direction Filter Chips */}
          <div style={{ display: 'flex', gap: '5px' }}>
            {(['TX', 'RX', 'CPDLC', 'XFER', 'SYS'] as LogDirection[]).map(direction => (
              <button
                key={direction}
                onClick={() => toggleFilter(direction)}
                style={{
                  padding: '4px 8px',
                  background: activeFilters.has(direction) ? '#00ff00' : '#2a2a4e',
                  border: '1px solid #004400',
                  color: activeFilters.has(direction) ? '#000' : '#00ff00',
                  cursor: 'pointer',
                  fontSize: '9px',
                  borderRadius: '3px',
                  transition: '0.3s'
                }}
              >
                {direction}
              </button>
            ))}
          </div>
          
          {/* Arrival/Departure Filter */}
          <div style={{ display: 'flex', gap: '5px' }}>
            {(['all', 'arrival', 'departure'] as const).map(type => (
              <button
                key={type}
                onClick={() => setArrivalFilter(type)}
                style={{
                  padding: '4px 8px',
                  background: arrivalFilter === type ? (type === 'arrival' ? '#ff4444' : type === 'departure' ? '#00ff88' : '#00ff00') : '#2a2a4e',
                  border: '1px solid #004400',
                  color: arrivalFilter === type ? '#000' : '#00ff00',
                  cursor: 'pointer',
                  fontSize: '9px',
                  borderRadius: '3px',
                  transition: '0.3s',
                  textTransform: 'capitalize'
                }}
              >
                {type}
              </button>
            ))}
          </div>
          
          {/* Sector Filter */}
          <div style={{ display: 'flex', gap: '5px' }}>
            {(['TWR', 'GND', 'APP', 'CTR']).map(sector => (
              <button
                key={sector}
                onClick={() => {
                  const newSectors = new Set(sectorFilter);
                  if (newSectors.has(sector)) {
                    newSectors.delete(sector);
                  } else {
                    newSectors.add(sector);
                  }
                  setSectorFilter(newSectors);
                }}
                style={{
                  padding: '4px 8px',
                  background: sectorFilter.has(sector) ? '#00ff00' : '#2a2a4e',
                  border: '1px solid #004400',
                  color: sectorFilter.has(sector) ? '#000' : '#00ff00',
                  cursor: 'pointer',
                  fontSize: '9px',
                  borderRadius: '3px',
                  transition: '0.3s'
                }}
              >
                {sector}
              </button>
            ))}
          </div>
          
          {/* Search Box */}
          <input
            type="text"
            placeholder="Search callsign/transcript..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '4px 8px',
              background: '#2a2a4e',
              border: '1px solid #004400',
              color: '#00ff00',
              fontSize: '10px',
              fontFamily: 'Courier New, monospace',
              width: '200px'
            }}
          />
          
          {/* Generate Mock Button */}
          <button
            onClick={handleGenerateMock}
            style={{
              padding: '6px 12px',
              background: '#2a2a4e',
              border: '1px solid #00ff00',
              color: '#00ff00',
              cursor: 'pointer',
              fontSize: '10px',
              transition: '0.3s',
              fontFamily: 'Courier New, monospace'
            }}
          >
            Generate Mock Logs
          </button>
        </div>
      </div>
      
      {/* Table */}
      <div style={{ flex: 1, overflow: 'auto', padding: '10px' }}>
        {filteredLogs.length === 0 ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%'
          }}>
            <div style={{
              background: '#1a1a2e',
              border: '2px solid #00ff00',
              padding: '40px',
              textAlign: 'center',
              borderRadius: '5px'
            }}>
              <h3 style={{ color: '#00ff00', marginBottom: '10px' }}>
                {loading ? 'Loading events...' : 'No events yet'}
              </h3>
              <p style={{ color: '#888', marginBottom: '20px' }}>
                {loading 
                  ? 'Connecting to real-time event stream...' 
                  : connected 
                    ? 'Waiting for events to appear...' 
                    : 'Unable to connect to event stream'
                }
              </p>
              {!connected && !loading && (
                <div style={{
                  background: '#2a1a1a',
                  border: '1px solid #ff4444',
                  padding: '10px',
                  borderRadius: '3px',
                  marginBottom: '20px'
                }}>
                  <p style={{ color: '#ff4444', fontSize: '12px', margin: 0 }}>
                    Check database and Redis connections
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '9px',
            background: '#1a1a2e',
            border: '1px solid #00ff00'
          }}>
            <thead>
              <tr>
                <th style={{
                  background: '#2a2a4e',
                  color: '#00ff00',
                  padding: '8px 6px',
                  textAlign: 'left',
                  borderBottom: '1px solid #00ff00',
                  fontWeight: 'bold',
                  position: 'sticky',
                  top: 0,
                  zIndex: 10
                }}>Time (UTC)</th>
                <th style={{
                  background: '#2a2a4e',
                  color: '#00ff00',
                  padding: '8px 6px',
                  textAlign: 'left',
                  borderBottom: '1px solid #00ff00',
                  fontWeight: 'bold',
                  position: 'sticky',
                  top: 0,
                  zIndex: 10
                }}>Dir</th>
                <th style={{
                  background: '#2a2a4e',
                  color: '#00ff00',
                  padding: '8px 6px',
                  textAlign: 'left',
                  borderBottom: '1px solid #00ff00',
                  fontWeight: 'bold',
                  position: 'sticky',
                  top: 0,
                  zIndex: 10
                }}>Sector/Freq</th>
                <th style={{
                  background: '#2a2a4e',
                  color: '#00ff00',
                  padding: '8px 6px',
                  textAlign: 'left',
                  borderBottom: '1px solid #00ff00',
                  fontWeight: 'bold',
                  position: 'sticky',
                  top: 0,
                  zIndex: 10
                }}>Callsign</th>
                <th style={{
                  background: '#2a2a4e',
                  color: '#00ff00',
                  padding: '8px 6px',
                  textAlign: 'left',
                  borderBottom: '1px solid #00ff00',
                  fontWeight: 'bold',
                  position: 'sticky',
                  top: 0,
                  zIndex: 10
                }}>Message</th>
                <th style={{
                  background: '#2a2a4e',
                  color: '#00ff00',
                  padding: '8px 6px',
                  textAlign: 'left',
                  borderBottom: '1px solid #00ff00',
                  fontWeight: 'bold',
                  position: 'sticky',
                  top: 0,
                  zIndex: 10
                }}>Audio</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log, index) => (
                <tr key={`${log.id}-${log.ts}-${index}`} style={{
                  borderBottom: '1px solid #004400'
                }}>
                  <td style={{
                    padding: '6px',
                    color: '#888',
                    whiteSpace: 'nowrap'
                  }}>{formatTime(log.ts)}</td>
                  <td style={{ padding: '6px' }}>
                    <DirBadge d={log.direction} />
                  </td>
                  <td style={{
                    padding: '6px',
                    color: '#00ff00',
                    fontWeight: 'bold'
                  }}>
                    {log.sector}/{log.frequency}
                  </td>
                  <td style={{
                    padding: '6px',
                    color: '#fff',
                    fontWeight: 'bold'
                  }}>
                    {log.callsign}
                  </td>
                  <td style={{
                    padding: '6px',
                    color: log.arrival === true ? '#ff4444' : log.arrival === false ? '#00ff88' : '#fff',
                    maxWidth: '300px'
                  }}>
                    <span dangerouslySetInnerHTML={{ __html: formatMessage(log) }} />
                  </td>
                  <td style={{ padding: '6px', textAlign: 'center' }}>
                    {log.audioUrl && (
                      <button
                        onClick={() => {
                          const audio = new Audio(log.audioUrl);
                          audio.play().catch(console.error);
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#00ff00',
                          cursor: 'pointer',
                          fontSize: '12px',
                          padding: '2px'
                        }}
                        title="Play audio"
                      >
                        ▶
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
