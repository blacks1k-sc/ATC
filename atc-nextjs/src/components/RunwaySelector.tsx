'use client';

import { useState } from 'react';

const RUNWAY_OPTIONS = [
  { id: '23',  label: 'RWY 23  — HDG 230° (Preferred, into prevailing wind)' },
  { id: '05',  label: 'RWY 05  — HDG 050°' },
  { id: '24R', label: 'RWY 24R — HDG 240°' },
  { id: '06L', label: 'RWY 06L — HDG 060°' },
  { id: '24L', label: 'RWY 24L — HDG 240°' },
  { id: '06R', label: 'RWY 06R — HDG 060°' },
  { id: '33R', label: 'RWY 33R — HDG 330°' },
  { id: '15L', label: 'RWY 15L — HDG 150°' },
  { id: '33L', label: 'RWY 33L — HDG 330°' },
  { id: '15R', label: 'RWY 15R — HDG 150°' },
];

interface RunwaySelectorProps {
  onSelectRunway: (runway: string) => void;
}

export default function RunwaySelector({ onSelectRunway }: RunwaySelectorProps) {
  const [selected, setSelected] = useState('23');
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    setLoading(true);
    try {
      await fetch('/api/runway', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ runway: selected }),
      });
    } catch (e) {
      console.warn('Could not persist active runway (Redis may be unavailable):', e);
    }
    onSelectRunway(selected);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        fontFamily: 'monospace',
      }}
    >
      <div
        style={{
          background: '#0a1628',
          border: '1px solid #00ff9d',
          borderRadius: 8,
          padding: '32px 40px',
          minWidth: 420,
          boxShadow: '0 0 40px rgba(0,255,157,0.15)',
        }}
      >
        <div style={{ color: '#00ff9d', fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
          CYYZ — ATC SIMULATION
        </div>
        <div style={{ color: '#8899aa', fontSize: 13, marginBottom: 24 }}>
          Select the active arrival runway before starting the simulation.
          Aircraft will intercept the ILS and fly a proper final approach.
        </div>

        <div style={{ marginBottom: 24 }}>
          {RUNWAY_OPTIONS.map((rwy) => (
            <label
              key={rwy.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 12px',
                marginBottom: 4,
                borderRadius: 4,
                cursor: 'pointer',
                background: selected === rwy.id ? 'rgba(0,255,157,0.08)' : 'transparent',
                border: selected === rwy.id ? '1px solid rgba(0,255,157,0.3)' : '1px solid transparent',
                transition: 'all 0.15s',
              }}
            >
              <input
                type="radio"
                name="runway"
                value={rwy.id}
                checked={selected === rwy.id}
                onChange={() => setSelected(rwy.id)}
                style={{ accentColor: '#00ff9d' }}
              />
              <span style={{ color: selected === rwy.id ? '#00ff9d' : '#ccd6e0', fontSize: 13 }}>
                {rwy.label}
              </span>
            </label>
          ))}
        </div>

        <button
          onClick={handleStart}
          disabled={loading}
          style={{
            width: '100%',
            padding: '12px 0',
            background: loading ? '#1a2a1a' : '#00ff9d',
            color: '#001a0e',
            border: 'none',
            borderRadius: 4,
            fontFamily: 'monospace',
            fontWeight: 700,
            fontSize: 14,
            cursor: loading ? 'not-allowed' : 'pointer',
            letterSpacing: 1,
          }}
        >
          {loading ? 'STARTING...' : `START SIMULATION — RWY ${selected}`}
        </button>
      </div>
    </div>
  );
}
