'use client';

import { useState, useEffect, useCallback } from 'react';
import { Aircraft, FlightStrip, StageMessage, SystemStatus, WeatherData } from '@/types/atc';
import Header from './Header';
import RadarDisplay from './RadarDisplay';
import RunwayDisplay from './RunwayDisplay';
import ControlPanels from './ControlPanels';
import Communications from './Communications';
import ControlButtons from './ControlButtons';

export default function ATCSystem() {
  const [systemActive, setSystemActive] = useState(false);
  const [currentTime, setCurrentTime] = useState('');
  const [activeTab, setActiveTab] = useState('tower');
  const [emergencyAlert, setEmergencyAlert] = useState(false);
  const [emergencyCoord, setEmergencyCoord] = useState(false);
  const [systemEmergency, setSystemEmergency] = useState(false);
  const [currentAirport, setCurrentAirport] = useState('CYYZ'); // Default to YYZ

  // Aircraft data
  const [aircraft, setAircraft] = useState<Aircraft[]>([
    {
      id: 'ual245',
      callsign: 'UAL245',
      type: 'A320',
      status: 'airborne',
      position: { top: '25%', left: '70%' },
      label: {
        top: '-25px',
        left: '20px',
        borderColor: '#00ffff',
        content: 'UAL245<br/>FL350 M.82<br/>SFO-LAX'
      }
    },
    {
      id: 'aal891',
      callsign: 'AAL891',
      type: 'B738',
      status: 'airborne',
      position: { top: '65%', left: '30%' },
      label: {
        top: '-25px',
        left: '20px',
        borderColor: '#00ffff',
        content: 'AAL891<br/>FL280 M.78<br/>APCH 25L'
      }
    }
  ]);

  const [emergencyAircraft, setEmergencyAircraft] = useState<Aircraft | null>({
    id: 'swa1234',
    callsign: 'SWA1234',
    type: 'B737-800',
    status: 'emergency',
    position: { top: '40%', left: '85%' },
    label: {
      top: '-25px',
      left: '-70px',
      borderColor: '#ff0000',
      content: 'SWA1234<br/>FL310 EMERG<br/>ENG FAILURE'
    }
  });

  const [groundAircraft, setGroundAircraft] = useState<Aircraft[]>([
    {
      id: 'dal567',
      callsign: 'DAL567',
      type: 'B757',
      status: 'ground',
      position: { top: '18%', left: '78%' },
      label: {
        top: '-20px',
        left: '15px',
        borderColor: '#ffff00',
        content: 'DAL567<br/>GATE A12<br/>BOARDING'
      }
    },
    {
      id: 'jbu890',
      callsign: 'JBU890',
      type: 'A321',
      status: 'taxiing',
      position: { top: '45%', left: '35%' },
      label: {
        top: '-20px',
        left: '15px',
        borderColor: '#00ff00',
        content: 'JBU890<br/>TAXI A,B<br/>RWY 25L'
      }
    },
    {
      id: 'vrg123',
      callsign: 'VRG123',
      type: 'A320',
      status: 'takeoff',
      position: { top: '32%', left: '45%' },
      label: {
        top: '-20px',
        left: '15px',
        borderColor: '#ff0000',
        content: 'VRG123<br/>TAKEOFF<br/>RWY 25L'
      }
    }
  ]);

  const [flightStrips, setFlightStrips] = useState<FlightStrip[]>([
    {
      id: 'ual245',
      callsign: 'UAL245',
      type: 'A320 SFO-LAX',
      route: '',
      phase: 'EN ROUTE',
      status: 'active',
      details: 'FL350 HDG 250 STAR ARRIVAL'
    },
    {
      id: 'aal891',
      callsign: 'AAL891',
      type: 'B738 PHX-LAX',
      route: '',
      phase: 'APPROACH',
      status: 'normal',
      details: 'FL080 ILS 25L ESTABLISHED'
    },
    {
      id: 'jbu890',
      callsign: 'JBU890',
      type: 'A321 JFK-LAX',
      route: '',
      phase: 'TAXI',
      status: 'normal',
      details: 'GATE B15 → RWY 25L VIA A,B'
    },
    {
      id: 'dal567',
      callsign: 'DAL567',
      type: 'B757 SEA-LAX',
      route: '',
      phase: 'AT GATE',
      status: 'normal',
      details: 'GATE A12 - BOARDING'
    }
  ]);

  const [emergencyStrip, setEmergencyStrip] = useState<FlightStrip>({
    id: 'swa1234',
    callsign: 'SWA1234',
    type: 'B737-800',
    route: '',
    phase: 'EMERGENCY - ENGINE FAILURE',
    status: 'emergency',
    details: 'FL310 → VECTORS ILS 25L'
  });

  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    towerAI: 'active',
    groundAI: 'active',
    weather: 'warning',
    emergency: 'active'
  });

  const [weatherData, setWeatherData] = useState<WeatherData>({
    wind: '250/18G25',
    visibility: '6SM -RA',
    ceiling: 'BKN008 OVC015',
    altimeter: '29.92',
    alerts: ['LLWS ALERT RWY 25L', 'TSTM CELL 20NM W']
  });

  const [messages, setMessages] = useState<{ [key: string]: StageMessage[] }>({});

  // Update time every second
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const timeString = now.toLocaleTimeString('en-US', { hour12: false, timeZone: 'UTC' }) + ' UTC | RWY 25L/R ACTIVE';
      setCurrentTime(timeString);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Auto-start system after 1.2 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      startSystem();
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'l' || e.key === 'L') {
        e.preventDefault();
        window.location.href = '/logs';
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const addStageLog = useCallback((stage: string, kind: 'departure' | 'arrival', data: { flight: string; type: string; text: string }) => {
    const newMessage: StageMessage = {
      id: Date.now().toString(),
      stage: stage as any,
      kind,
      flight: data.flight,
      type: data.type,
      text: data.text,
      timestamp: new Date()
    };

    setMessages(prev => ({
      ...prev,
      [stage]: [...(prev[stage] || []), newMessage].slice(-5) // Keep last 5 messages
    }));
  }, []);

  const startSystem = useCallback(async () => {
    setSystemActive(true);
    
    // Load real aircraft events from database instead of hardcoded data
    try {
      const response = await fetch('/api/events?limit=9');
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.events) {
          console.log('Loaded 9 initial events');
          
          // Process real aircraft events and add them to stage logs
          data.events.forEach((event: any, index: number) => {
            const callsign = event.aircraft?.callsign || event.callsign;
            const aircraftType = event.aircraft?.aircraft_type?.icao_type || 'UNKNOWN';
            const operationType = event.details?.operation_type || 'ARRIVAL';
            const flightPhase = event.details?.flight_phase || 'ENROUTE';
            
            // Map flight phases to stage categories
            let stage = 'enroute';
            let kind: 'departure' | 'arrival' = operationType === 'ARRIVAL' ? 'arrival' : 'departure';
            let text = event.message;
            
            // Determine stage based on flight phase and operation type
            if (flightPhase === 'SPAWNING' || flightPhase === 'DEPARTURE') {
              stage = 'entryExit';
            } else if (flightPhase === 'ENROUTE') {
              stage = 'enroute';
            } else if (flightPhase === 'APPROACH') {
              stage = 'seq';
            } else if (flightPhase === 'FINAL' || flightPhase === 'LANDING') {
              stage = 'runway';
            } else if (flightPhase === 'TAXI') {
              stage = 'groundMove';
            } else if (flightPhase === 'GATE') {
              stage = 'gate';
            }
            
            // Add stage log with staggered timing
            setTimeout(() => {
              addStageLog(stage, kind, { 
                flight: callsign, 
                type: aircraftType, 
                text: text 
              });
            }, index * 10);
          });
        }
      }
    } catch (error) {
      console.error('Error loading real aircraft events:', error);
      // Fallback to hardcoded data if database fails
      setTimeout(() => addStageLog('entryExit', 'departure', { flight: 'AAL78', type: 'B737', text: 'requesting SID clearance' }), 0);
      setTimeout(() => addStageLog('entryExit', 'arrival', { flight: 'QFA12', type: 'A388', text: 'entering sector, FL370' }), 10);
      setTimeout(() => addStageLog('enroute', 'departure', { flight: 'DAL213', type: 'A321', text: 'climbing to FL350 via J65' }), 20);
      setTimeout(() => addStageLog('enroute', 'arrival', { flight: 'UAL267', type: 'A320', text: 'descend via ANJLL6' }), 30);
      setTimeout(() => addStageLog('seq', 'departure', { flight: 'ASA797', type: 'B737', text: 'line-up sequence RWY 25L' }), 40);
      setTimeout(() => addStageLog('seq', 'arrival', { flight: 'UAL788', type: 'B737', text: 'on vectors for ILS 25L' }), 50);
      setTimeout(() => addStageLog('runway', 'arrival', { flight: 'UAL891', type: 'B738', text: 'on final for 24L' }), 60);
      setTimeout(() => addStageLog('groundMove', 'departure', { flight: 'JBU890', type: 'A321', text: 'taxi A, B to 25L, hold short' }), 70);
      setTimeout(() => addStageLog('gate', 'arrival', { flight: 'ACA551', type: 'A220', text: 'arrived at GATE B15' }), 80);
    }
  }, [addStageLog]);

  const addAircraft = useCallback(() => {
    if (!systemActive) {
      alert('Please start the system first');
      return;
    }
    // Add something illustrative to Sequencing
    addStageLog('seq', 'arrival', { flight: 'ENY495', type: 'E175', text: 'join downwind runway 25L' });
  }, [systemActive, addStageLog]);

  const simulateEmergency = useCallback(() => {
    if (!systemActive) {
      alert('Please start the system first');
      return;
    }
    setEmergencyAlert(true);
    setEmergencyCoord(true);
    setSystemEmergency(true);
    setSystemStatus(prev => ({ ...prev, emergency: 'emergency' }));

    // Add emergency strip
    setFlightStrips(prev => [emergencyStrip, ...prev]);

    setTimeout(() => {
      resolveEmergency();
    }, 10000);
  }, [systemActive, emergencyStrip]);

  const resolveEmergency = useCallback(() => {
    setEmergencyAlert(false);
    setEmergencyCoord(false);
    setSystemEmergency(false);
    setSystemStatus(prev => ({ ...prev, emergency: 'active' }));
    setFlightStrips(prev => prev.filter(strip => strip.id !== 'swa1234'));
  }, []);

  const handleAircraftGenerated = useCallback((aircraft: any) => {
    console.log('New aircraft generated:', aircraft);
    
    // Extract aircraft information
    const callsign = aircraft.callsign;
    const aircraftType = aircraft.aircraft_type?.icao_type || 'UNKNOWN';
    const operationType = aircraft.flight_plan?.operation_type || 'ARRIVAL';
    const flightPhase = aircraft.flight_plan?.flight_phase || 'SPAWNING';
    
    // Map flight phases to stage categories
    let stage = 'enroute';
    let kind: 'departure' | 'arrival' = operationType === 'ARRIVAL' ? 'arrival' : 'departure';
    let text = `Aircraft ${callsign} (${aircraftType}) created for ${aircraft.airline?.name || 'Unknown Airline'}`;
    
    // Determine stage based on flight phase and operation type
    if (flightPhase === 'SPAWNING' || flightPhase === 'DEPARTURE') {
      stage = 'entryExit';
    } else if (flightPhase === 'ENROUTE') {
      stage = 'enroute';
    } else if (flightPhase === 'APPROACH') {
      stage = 'seq';
    } else if (flightPhase === 'FINAL' || flightPhase === 'LANDING') {
      stage = 'runway';
    } else if (flightPhase === 'TAXI') {
      stage = 'groundMove';
    } else if (flightPhase === 'GATE') {
      stage = 'gate';
    }
    
    // Add stage log
    addStageLog(stage, kind, { 
      flight: callsign, 
      type: aircraftType, 
      text: text 
    });
  }, [addStageLog]);

  const handleTabChange = useCallback((tabId: string) => {
    setActiveTab(tabId);
  }, []);

  return (
    <div className="atc-system">
      <ControlButtons
        onStartSystem={startSystem}
        onAddAircraft={addAircraft}
        onSimulateEmergency={simulateEmergency}
        onAircraftGenerated={handleAircraftGenerated}
      />

      <Header
        systemStatus={systemStatus}
        currentTime={currentTime}
        onTabChange={handleTabChange}
      />

      <RadarDisplay
        aircraft={aircraft}
        emergencyAircraft={emergencyAircraft}
        emergencyAlert={emergencyAlert}
      />

      <RunwayDisplay icao={currentAirport} />

      <ControlPanels
        flightStrips={flightStrips}
        weatherData={weatherData}
        emergencyCoord={emergencyCoord}
      />

      <Communications
        messages={messages}
        systemEmergency={systemEmergency}
      />
    </div>
  );
}
