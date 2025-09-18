'use client';

import { useState, useMemo } from 'react';
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

// Mock data generator
function makeMockLogs(count: number): AtcLogEntry[] {
  const callsigns = ['DAL123', 'UAL456', 'AAL789', 'SWA234', 'JBU567', 'VRG890', 'ASA123', 'QFA456'];
  const aircraftTypes = ['A320', 'B738', 'E175', 'A321', 'B737', 'A220', 'B757', 'A388'];
  const sectors = ['TWR', 'GND', 'APP', 'CTR'];
  const frequencies = ['118.7', '120.95', '121.65', '124.47', '127.0', '119.1', '122.8', '125.2'];
  const directions: LogDirection[] = ['TX', 'RX', 'CPDLC', 'XFER', 'SYS'];
  
  const logs: AtcLogEntry[] = [];
  
  for (let i = 0; i < count; i++) {
    const callsign = callsigns[Math.floor(Math.random() * callsigns.length)];
    const aircraftType = aircraftTypes[Math.floor(Math.random() * aircraftTypes.length)];
    const sector = sectors[Math.floor(Math.random() * sectors.length)];
    const frequency = frequencies[Math.floor(Math.random() * frequencies.length)];
    const direction = directions[Math.floor(Math.random() * directions.length)];
    const arrival = Math.random() > 0.5;
    const hasAudio = Math.random() < 0.1; // 10% have audio
    
    let summary = '';
    let handoffFrom = '';
    let handoffTo = '';
    
    switch (direction) {
      case 'TX':
        summary = arrival 
          ? `${callsign}, wind 270 at 10, cleared to land 24R.`
          : `${callsign}, wind 270 at 10, cleared for takeoff 24R.`;
        break;
      case 'RX':
        summary = arrival
          ? `Cleared to land 24R, ${callsign}.`
          : `Cleared for takeoff 24R, ${callsign}.`;
        break;
      case 'CPDLC':
        summary = Math.random() > 0.5 ? 'Climb FL180.' : 'WILCO.';
        break;
      case 'XFER':
        handoffFrom = 'TWR';
        handoffTo = 'APP';
        summary = `${callsign} handoff ${handoffFrom} → ${handoffTo}`;
        break;
      case 'SYS':
        summary = 'RWY 24R RVR < 1200, Low Vis Ops active.';
        break;
    }
    
    // Add arrival/departure prefix for some entries
    if (direction === 'TX' || direction === 'RX') {
      const prefix = arrival ? 'ARRIVAL:' : 'DEPARTURE:';
      summary = `${prefix} ${callsign} (${aircraftType}) ${summary}`;
    }
    
    logs.push({
      id: `log_${Date.now()}_${i}`,
      ts: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
      callsign,
      sector,
      frequency,
      direction,
      summary,
      arrival: direction === 'TX' || direction === 'RX' ? arrival : undefined,
      flight: {
        type: aircraftType,
        from: 'KJFK',
        to: 'KLAX',
        squawk: Math.floor(Math.random() * 9000 + 1000).toString()
      },
      audioUrl: hasAudio ? `/audio/sample${Math.floor(Math.random() * 5) + 1}.mp3` : undefined,
      transcript: hasAudio ? summary : undefined,
      handoffFrom: direction === 'XFER' ? handoffFrom : undefined,
      handoffTo: direction === 'XFER' ? handoffTo : undefined
    });
  }
  
  return logs.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
}

export default function Logs() {
  const [logs, setLogs] = useState<AtcLogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilters, setActiveFilters] = useState<Set<LogDirection>>(new Set(['TX', 'RX', 'CPDLC', 'XFER', 'SYS']));
  const [arrivalFilter, setArrivalFilter] = useState<'all' | 'arrival' | 'departure'>('all');
  const [sectorFilter, setSectorFilter] = useState<Set<string>>(new Set(['TWR', 'GND', 'APP', 'CTR']));
  
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
  
  const handleGenerateMock = () => {
    setLogs(makeMockLogs(50));
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
              <h3 style={{ color: '#00ff00', marginBottom: '10px' }}>No logs yet</h3>
              <p style={{ color: '#888', marginBottom: '20px' }}>Generate mock logs to see communication history</p>
              <button
                onClick={handleGenerateMock}
                style={{
                  padding: '8px 16px',
                  background: '#2a2a4e',
                  border: '1px solid #00ff00',
                  color: '#00ff00',
                  cursor: 'pointer',
                  fontSize: '12px',
                  transition: '0.3s',
                  fontFamily: 'Courier New, monospace'
                }}
              >
                Generate Mock Logs
              </button>
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
              {filteredLogs.map((log) => (
                <tr key={log.id} style={{
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
