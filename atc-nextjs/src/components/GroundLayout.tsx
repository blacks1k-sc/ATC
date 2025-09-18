'use client';

import { Aircraft } from '@/types/atc';

interface GroundLayoutProps {
  groundAircraft: Aircraft[];
}

export default function GroundLayout({ groundAircraft }: GroundLayoutProps) {
  return (
    <div className="display-area ground-radar" id="groundDisplay">
      <div className="airport-layout">
        {/* Runways */}
        <div className="runway runway-25L">
          <div className="runway-label" style={{ top: '-20px', left: '10%' }}>25L</div>
          <div className="runway-label" style={{ top: '-20px', right: '10%' }}>07R</div>
        </div>
        <div className="runway runway-25R">
          <div className="runway-label" style={{ top: '-20px', left: '10%' }}>25R</div>
          <div className="runway-label" style={{ top: '-20px', right: '10%' }}>07L</div>
        </div>
        <div className="runway runway-07L">
          <div className="runway-label" style={{ top: '-20px', left: '50%' }}>07L</div>
        </div>

        {/* Taxiways */}
        <div className="taxiway taxiway-a">
          <div className="taxiway-label" style={{ top: '-15px', left: '5px' }}>A</div>
        </div>
        <div className="taxiway taxiway-b">
          <div className="taxiway-label" style={{ top: '-15px', left: '5px' }}>B</div>
        </div>
        <div className="taxiway taxiway-c">
          <div className="taxiway-label" style={{ left: '-15px', top: '8px' }}>C</div>
        </div>
        <div className="taxiway taxiway-d">
          <div className="taxiway-label" style={{ left: '-15px', top: '8px' }}>D</div>
        </div>

        {/* Terminal */}
        <div className="terminal">
          <div style={{ color: '#fff', fontSize: '10px', textAlign: 'center', marginTop: '15px' }}>
            TERMINAL
          </div>
        </div>

        {/* Gates */}
        <div className="gate" style={{ top: '15%', left: '75%' }}></div>
        <div className="gate" style={{ top: '20%', left: '75%' }}></div>
        <div className="gate" style={{ top: '25%', left: '75%' }}></div>

        {/* Ground Aircraft */}
        {groundAircraft.map((plane) => (
          <div
            key={plane.id}
            className={`aircraft-ground ${plane.status}`}
            style={{
              top: plane.position.top,
              left: plane.position.left
            }}
          >
            <div
              className="aircraft-label"
              style={{
                top: plane.label.top,
                left: plane.label.left,
                borderColor: plane.label.borderColor
              }}
              dangerouslySetInnerHTML={{ __html: plane.label.content }}
            />
          </div>
        ))}

        {/* Ground Vehicles */}
        <div className="ground-vehicle" style={{ top: '40%' }}></div>
        <div className="ground-vehicle" style={{ top: '55%', animationDelay: '-5s' }}></div>
      </div>
    </div>
  );
}
