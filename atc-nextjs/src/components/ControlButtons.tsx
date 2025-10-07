'use client';

import Link from 'next/link';
import { useState } from 'react';
import AircraftSelector from './AircraftSelector';

interface ControlButtonsProps {
  onStartSystem: () => void;
  onAddAircraft: () => void;
  onSimulateEmergency: () => void;
}

export default function ControlButtons({ onStartSystem, onAddAircraft, onSimulateEmergency }: ControlButtonsProps) {
  const [showAircraftSelector, setShowAircraftSelector] = useState(false);

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
