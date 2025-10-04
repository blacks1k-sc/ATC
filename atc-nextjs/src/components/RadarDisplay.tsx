'use client';

import { Aircraft } from '@/types/atc';

interface RadarDisplayProps {
  aircraft: Aircraft[];
  emergencyAircraft: Aircraft | null;
  emergencyAlert: boolean;
}

export default function RadarDisplay({ aircraft, emergencyAircraft, emergencyAlert }: RadarDisplayProps) {
  // Responsive circle sizes based on percentage of container
  const radarCircles = [12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]; // percentages
  const degreeMarks = [
    { degree: '0', style: { top: '0', left: '50%', transform: 'translateX(-50%) translateY(-2.5%)' } },
    { degree: '30', style: { top: '13.4%', right: '13.4%', transform: 'translate(2.5%,-50%)' } },
    { degree: '60', style: { top: '50%', right: '0', transform: 'translateY(-50%) translateX(2.5%)' } },
    { degree: '90', style: { top: '50%', right: '0', transform: 'translateY(-50%) translateX(2.5%)' } },
    { degree: '120', style: { bottom: '13.4%', right: '13.4%', transform: 'translate(2.5%,50%)' } },
    { degree: '150', style: { bottom: '0', left: '50%', transform: 'translateX(-50%) translateY(2.5%)' } },
    { degree: '180', style: { bottom: '0', left: '50%', transform: 'translateX(-50%) translateY(2.5%)' } },
    { degree: '210', style: { bottom: '13.4%', left: '13.4%', transform: 'translate(-2.5%,50%)' } },
    { degree: '240', style: { top: '50%', left: '0', transform: 'translateY(-50%) translateX(-2.5%)' } },
    { degree: '270', style: { top: '50%', left: '0', transform: 'translateY(-50%) translateX(-2.5%)' } },
    { degree: '300', style: { top: '13.4%', left: '13.4%', transform: 'translate(-2.5%,-50%)' } },
    { degree: '330', style: { top: '0', left: '50%', transform: 'translateX(-50%) translateY(-2.5%)' } },
  ];

  return (
    <div className="display-area" id="airspaceDisplay">
      <div className="radar-circles">
        {radarCircles.map((size, index) => (
          <div
            key={index}
            className="radar-circle"
            style={{ '--circle-size': size } as React.CSSProperties}
          />
        ))}
      </div>

      <div className="degree-markings">
        {degreeMarks.map((mark, index) => (
          <div
            key={index}
            className="degree-mark"
            style={mark.style}
          >
            {mark.degree}
          </div>
        ))}
      </div>

      <div className="radar-sweep-wedge">
        <div className="sweep-wedge"></div>
      </div>

      {/* Sample airborne markers */}
      {aircraft.map((plane) => (
        <div
          key={plane.id}
          className={`aircraft-airborne ${plane.status === 'emergency' ? 'emergency' : ''}`}
          style={{
            top: plane.position.top,
            left: plane.position.left,
            display: plane.status === 'emergency' && !emergencyAircraft ? 'none' : 'block'
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

      {emergencyAircraft && (
        <div
          className="aircraft-airborne"
          style={{
            top: emergencyAircraft.position.top,
            left: emergencyAircraft.position.left,
            display: emergencyAlert ? 'block' : 'none'
          }}
        >
          <div
            className="aircraft-label"
            style={{
              top: emergencyAircraft.label.top,
              left: emergencyAircraft.label.left,
              borderColor: emergencyAircraft.label.borderColor
            }}
            dangerouslySetInnerHTML={{ __html: emergencyAircraft.label.content }}
          />
        </div>
      )}

      <div className={`emergency-alert ${emergencyAlert ? 'show' : ''}`}>
        ⚠️ EMERGENCY: SWA1234 ENGINE FAILURE
      </div>
    </div>
  );
}
