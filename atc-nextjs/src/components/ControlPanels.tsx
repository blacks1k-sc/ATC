'use client';

import { useState, useEffect } from 'react';
import { FlightStrip, LLMClearance } from '@/types/atc';

interface ControlPanelsProps {
  flightStrips: FlightStrip[];
  emergencyCoord: boolean;
}

export default function ControlPanels({ flightStrips, emergencyCoord }: ControlPanelsProps) {
  const [clearances, setClearances] = useState<LLMClearance[]>([]);
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
    // Refresh every 2 seconds
    const interval = setInterval(fetchClearances, 2000);
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
          {flightStrips.map((strip) => (
            <div
              key={strip.id}
              className={`flight-strip ${strip.status === 'active' ? 'active' : ''} ${strip.status === 'emergency' ? 'emergency' : ''}`}
            >
              <strong>{strip.callsign}</strong> {strip.type} {strip.route}<br/>
              <span className="strip-phase">{strip.phase}</span><br/>
              {strip.details}
            </div>
          ))}
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
