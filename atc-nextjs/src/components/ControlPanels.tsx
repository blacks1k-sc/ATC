'use client';

import { FlightStrip, WeatherData } from '@/types/atc';

interface ControlPanelsProps {
  flightStrips: FlightStrip[];
  weatherData: WeatherData;
  emergencyCoord: boolean;
}

export default function ControlPanels({ flightStrips, weatherData, emergencyCoord }: ControlPanelsProps) {
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
        <h4>COORDINATION</h4>
        <div style={{ fontSize: '9px' }}>
          <div style={{ color: '#ff6600', marginBottom: '5px' }}>
            <strong>HANDOFF:</strong><br/> UAL245 → APPROACH
          </div>
          <div style={{ color: '#0066cc', marginBottom: '5px' }}>
            <strong>GROUND COORD:</strong><br/> JBU890 RDY TAXI
          </div>
          {emergencyCoord && (
            <div style={{ color: '#ff0000', marginBottom: '5px' }}>
              <strong>EMERGENCY:</strong><br/> SWA1234 PRIORITY
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <h4>WEATHER &amp; NOTAMS</h4>
        <div className="weather-data">
          <div className="weather-item">
            <span>WIND:</span><span>{weatherData.wind}</span>
          </div>
          <div className="weather-item">
            <span>VIS:</span><span>{weatherData.visibility}</span>
          </div>
          <div className="weather-item">
            <span>CEIL:</span><span>{weatherData.ceiling}</span>
          </div>
          <div className="weather-item">
            <span>ALT:</span><span>{weatherData.altimeter}</span>
          </div>
          <div style={{ color: '#ff6600', marginTop: '8px', fontSize: '8px' }}>
            {weatherData.alerts.map((alert, index) => (
              <div key={index}>⚠️ {alert}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
