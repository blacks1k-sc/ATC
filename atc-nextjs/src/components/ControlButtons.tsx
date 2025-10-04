'use client';

import Link from 'next/link';
import { useState } from 'react';
import AircraftSelector from './AircraftSelector';

interface ControlButtonsProps {
  onStartSystem: () => void;
  onAddAircraft: () => void;
  onSimulateEmergency: () => void;
  onAircraftGenerated: (aircraft: any) => void;
}

export default function ControlButtons({ onStartSystem, onAddAircraft, onSimulateEmergency, onAircraftGenerated }: ControlButtonsProps) {
  const [showAircraftSelector, setShowAircraftSelector] = useState(false);

  const handleAircraftGenerated = (aircraft: any) => {
    console.log('New aircraft generated:', aircraft);
    onAircraftGenerated(aircraft);
    setShowAircraftSelector(false);
  };

  return (
    <>
      <div className="control-buttons">
        <button className="control-btn" onClick={onStartSystem}>
          START SYSTEM
        </button>
        <button className="control-btn" onClick={onAddAircraft}>
          ADD AIRCRAFT
        </button>
        <button className="control-btn" onClick={() => setShowAircraftSelector(true)}>
          GENERATE AIRCRAFT
        </button>
        <button className="control-btn emergency" onClick={onSimulateEmergency}>
          SIMULATE EMERGENCY
        </button>
        <Link href="/logs" className="control-btn">
          LOGS
        </Link>
        <Link href="/ground" className="control-btn">
          GROUND OPS
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
