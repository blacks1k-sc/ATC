'use client';

import { useState, useEffect } from 'react';
import { LLMClearance } from '@/types/atc';

interface ControlPanelsProps {
  emergencyCoord: boolean;
}

interface LiveAircraft {
  id: number;
  callsign: string;
  registration?: string;
  aircraft_type?: { icao_type: string };
  airline?: { icao: string };
  position?: { altitude_ft?: number; speed_kts?: number };
  phase?: string;
  distance_to_airport_nm?: number;
  status?: string;
}

export default function ControlPanels({ emergencyCoord }: ControlPanelsProps) {
  const [clearances, setClearances] = useState<LLMClearance[]>([]);
  const [liveAircraft, setLiveAircraft] = useState<LiveAircraft[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchClearances = async () => {
      try {
        const response = await fetch('/api/clearances?limit=10&status=ACTIVE');
        const data = await response.json();
        if (data.success) {
          setClearances(data.clearances || []);
        }
      } catch (error) {
        console.error('Error fetching clearances:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchClearances();
    const interval = setInterval(fetchClearances, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchAircraft = async () => {
      try {
        const r = await fetch('/api/aircraft?limit=20');
        const d = await r.json();
        if (d.aircraft) setLiveAircraft(d.aircraft.slice(0, 10));
      } catch {}
    };
    fetchAircraft();
    const interval = setInterval(fetchAircraft, 2000);
    return () => clearInterval(interval);
  }, []);

  const formatClearance = (clearance: LLMClearance) => {
    const { callsign, clearance_type, instructions, validated, issued_by } = clearance;
    const inst = instructions || {};
    
    let text = '';
    if (issued_by === 'AIR_LLM') {
      // Air clearances
      if (inst.target_altitude_ft) text += `ALT ${inst.target_altitude_ft}ft `;
      if (inst.target_speed_kts) text += `SPD ${inst.target_speed_kts}kts `;
      if (inst.target_heading_deg) text += `HDG ${inst.target_heading_deg}° `;
      if (inst.runway) text += `RWY ${inst.runway}`;
    } else {
      // Ground clearances
      if (inst.assigned_gate) text += `GATE ${inst.assigned_gate} `;
      if (inst.taxi_route && inst.taxi_route.length > 0) {
        text += `TAXI ${inst.taxi_route.join('-')}`;
      }
      if (inst.runway) text += `RWY ${inst.runway}`;
    }
    
    return {
      callsign,
      type: clearance_type,
      text: text.trim() || clearance_type,
      validated: validated !== false,
      issued_by
    };
  };

  const airClearances = clearances.filter(c => c.issued_by === 'AIR_LLM').slice(0, 5);
  const groundClearances = clearances.filter(c => c.issued_by === 'GROUND_LLM').slice(0, 5);

  return (
    <div className="control-panels">
      <div className="panel">
        <h4>ACTIVE FLIGHT STRIPS</h4>
        <div className="strip-container">
          {liveAircraft.length === 0 ? (
            <div style={{ color: '#666', fontSize: '9px' }}>No active aircraft</div>
          ) : liveAircraft.map((ac) => {
            const alt = ac.position?.altitude_ft;
            const fl = alt ? `FL${Math.round(alt / 100)}` : 'N/A';
            const dist = ac.distance_to_airport_nm ? `${Number(ac.distance_to_airport_nm).toFixed(0)}NM` : '';
            const phase = ac.phase || 'CRUISE';
            return (
              <div key={ac.id} className={`flight-strip ${ac.status === 'active' ? 'active' : ''}`}>
                <strong>{ac.callsign}</strong> {ac.aircraft_type?.icao_type || ''} {ac.airline?.icao || ''}<br/>
                <span className="strip-phase">{phase}</span><br/>
                {fl} {dist}
              </div>
            );
          })}
        </div>
      </div>

      <div className="panel">
        <h4>LLM AIR CLEARANCES</h4>
        <div style={{ fontSize: '9px' }}>
          {loading ? (
            <div style={{ color: '#00ff00' }}>Loading...</div>
          ) : airClearances.length === 0 ? (
            <div style={{ color: '#666' }}>No active air clearances</div>
          ) : (
            airClearances.map((clearance) => {
              const formatted = formatClearance(clearance);
              return (
                <div 
                  key={clearance.id} 
                  style={{ 
                    color: formatted.validated ? '#00ff00' : '#ff6600', 
                    marginBottom: '5px',
                    borderLeft: formatted.validated ? '2px solid #00ff00' : '2px solid #ff6600',
                    paddingLeft: '5px'
                  }}
                >
                  <strong>{formatted.callsign}:</strong> {formatted.type}<br/>
                  <span style={{ fontSize: '8px' }}>{formatted.text}</span>
                  {!formatted.validated && (
                    <span style={{ color: '#ff0000', fontSize: '7px' }}> ⚠️ NOT VALIDATED</span>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="panel">
        <h4>LLM GROUND CLEARANCES</h4>
        <div style={{ fontSize: '9px' }}>
          {loading ? (
            <div style={{ color: '#0066cc' }}>Loading...</div>
          ) : groundClearances.length === 0 ? (
            <div style={{ color: '#666' }}>No active ground clearances</div>
          ) : (
            groundClearances.map((clearance) => {
              const formatted = formatClearance(clearance);
              return (
                <div 
                  key={clearance.id} 
                  style={{ 
                    color: formatted.validated ? '#0066cc' : '#ff6600', 
                    marginBottom: '5px',
                    borderLeft: formatted.validated ? '2px solid #0066cc' : '2px solid #ff6600',
                    paddingLeft: '5px'
                  }}
                >
                  <strong>{formatted.callsign}:</strong> {formatted.type}<br/>
                  <span style={{ fontSize: '8px' }}>{formatted.text}</span>
                  {!formatted.validated && (
                    <span style={{ color: '#ff0000', fontSize: '7px' }}> ⚠️ NOT VALIDATED</span>
                  )}
                </div>
              );
            })
          )}
          {emergencyCoord && (
            <div style={{ color: '#ff0000', marginTop: '8px' }}>
              <strong>EMERGENCY:</strong><br/> Priority handling active
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
