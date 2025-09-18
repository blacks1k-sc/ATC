'use client';

import { StageMessage } from '@/types/atc';

interface CommunicationsProps {
  messages: { [key: string]: StageMessage[] };
  systemEmergency: boolean;
}

export default function Communications({ messages, systemEmergency }: CommunicationsProps) {
  const panels = [
    { id: 'entryExit', title: 'AIRSPACE ENTRY / EXIT' },
    { id: 'enroute', title: 'EN-ROUTE OPERATIONS' },
    { id: 'seq', title: 'APPROACH/DEPARTURE SEQUENCING' },
    { id: 'runway', title: 'RUNWAY OPERATIONS' },
    { id: 'groundMove', title: 'GROUND MOVEMENT' },
    { id: 'gate', title: 'GATE OPERATIONS' },
  ];

  const renderMessage = (message: StageMessage) => {
    const isDep = message.kind === 'departure';
    return (
      <div key={message.id} className={`stage-message ${isDep ? 'dep' : 'arr'}`}>
        <span className={`badge ${isDep ? 'dep' : 'arr'}`}>
          {isDep ? 'DEPARTURE' : 'ARRIVAL'}
        </span>
        <span className={`flight ${isDep ? 'dep' : 'arr'}`}>
          {message.flight} {message.type}
        </span>
        <span className={`msg ${isDep ? 'dep' : 'arr'}`}>
          {message.text}
        </span>
      </div>
    );
  };

  return (
    <div className="communications-area">
      {panels.map((panel) => (
        <div key={panel.id} className="comm-panel">
          <h4>{panel.title}</h4>
          <div className="comm-messages">
            {messages[panel.id]?.slice(-5).map(renderMessage) || []}
          </div>
        </div>
      ))}

      {/* System Status */}
      <div className="comm-panel">
        <h4>SYSTEM STATUS</h4>
        <div style={{ fontSize: '9px' }}>
          <div style={{ color: 'var(--neon)', marginBottom: '5px' }}>
            ✓ AI CONTROLLERS: 4/4 ACTIVE<br/>
            ✓ RADAR: OPERATIONAL<br/>
            ✓ COMMS: ALL FREQUENCIES
          </div>
          <div style={{ color: '#ffff00', marginBottom: '5px' }}>
            ⚠️ WEATHER: LOW VISIBILITY<br/>
            ⚠️ TRAFFIC: HEAVY VOLUME
          </div>
          {systemEmergency && (
            <div style={{ color: '#ff0000' }}>
              🚨 EMERGENCY: 1 ACTIVE<br/>
              🚨 RUNWAY: 25R CLOSED
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
