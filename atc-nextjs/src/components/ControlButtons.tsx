'use client';

import Link from 'next/link';

interface ControlButtonsProps {
  onStartSystem: () => void;
  onAddAircraft: () => void;
  onSimulateEmergency: () => void;
}

export default function ControlButtons({ onStartSystem, onAddAircraft, onSimulateEmergency }: ControlButtonsProps) {
  return (
    <div className="control-buttons">
      <button className="control-btn" onClick={onStartSystem}>
        START SYSTEM
      </button>
      <button className="control-btn" onClick={onAddAircraft}>
        ADD AIRCRAFT
      </button>
      <button className="control-btn emergency" onClick={onSimulateEmergency}>
        SIMULATE EMERGENCY
      </button>
      <Link href="/logs" className="control-btn">
        LOGS
      </Link>
    </div>
  );
}
