'use client';

import { Aircraft } from '@/types/atc';
import { useRef, useEffect, useState } from 'react';

interface RadarDisplayProps {
  aircraft: Aircraft[];
  emergencyAircraft: Aircraft | null;
  emergencyAlert: boolean;
}

export default function RadarDisplay({ aircraft, emergencyAircraft, emergencyAlert }: RadarDisplayProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);


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
