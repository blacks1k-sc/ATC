'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import AircraftSelector from './AircraftSelector';

interface ControlButtonsProps {
  onStartSystem: () => void;
  onAddAircraft: () => void;
  onSimulateEmergency: () => void;
}

export default function ControlButtons({ onStartSystem, onAddAircraft, onSimulateEmergency }: ControlButtonsProps) {
  const [showAircraftSelector, setShowAircraftSelector] = useState(false);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);

  useEffect(() => {
    fetch('/api/speed').then(r => r.json()).then(d => setSpeedMultiplier(d.multiplier || 1)).catch(() => {});
  }, []);

  const setSpeed = async (m: number) => {
    await fetch('/api/speed', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ multiplier: m }) });
    setSpeedMultiplier(m);
  };

  const handleAircraftGenerated = (aircraft: any) => {
    console.log('New aircraft generated:', aircraft);
    // Here you can add the aircraft to the system or handle it as needed
    setShowAircraftSelector(false);
  };

  return (
    <>
      <div className="control-buttons">
        <button className="control-btn" onClick={onStartSystem}>
          START SYSTEM
        </button>
        <button className="control-btn" onClick={() => setShowAircraftSelector(true)}>
          GENERATE AIRCRAFT
        </button>
        <button className="control-btn emergency" onClick={onSimulateEmergency}>
          SIMULATE EMERGENCY
        </button>
        {([1, 2, 4, 8] as const).map(m => (
          <button
            key={m}
            className="control-btn"
            style={speedMultiplier === m ? { borderColor: '#00ff9d', color: '#00ff9d' } : {}}
            onClick={() => setSpeed(m)}
          >
            {m}X
          </button>
        ))}
        <Link href="/ground" className="control-btn">
          GROUND OPS
        </Link>
        <Link href="/engine-ops" className="control-btn">
          ENGINE OPS
        </Link>
        <Link href="/logs" className="control-btn">
          LOGS
        </Link>
      </div>

      <AircraftSelector
        isOpen={showAircraftSelector}
        onClose={() => setShowAircraftSelector(false)}
        onAircraftGenerated={handleAircraftGenerated}
      />
    </>
  );
}
