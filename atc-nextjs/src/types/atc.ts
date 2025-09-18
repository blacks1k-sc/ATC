export interface Aircraft {
  id: string;
  callsign: string;
  type: string;
  status: 'airborne' | 'ground' | 'taxiing' | 'takeoff' | 'emergency';
  position: {
    top: string;
    left: string;
  };
  label: {
    top: string;
    left: string;
    borderColor: string;
    content: string;
  };
  route?: string;
  altitude?: string;
  heading?: string;
}

export interface FlightStrip {
  id: string;
  callsign: string;
  type: string;
  route: string;
  phase: string;
  status: 'active' | 'emergency' | 'normal';
  details: string;
}

export interface StageMessage {
  id: string;
  stage: 'entryExit' | 'enroute' | 'seq' | 'runway' | 'groundMove' | 'gate';
  kind: 'departure' | 'arrival';
  flight: string;
  type: string;
  text: string;
  timestamp: Date;
}

export interface SystemStatus {
  towerAI: 'active' | 'warning' | 'emergency';
  groundAI: 'active' | 'warning' | 'emergency';
  weather: 'active' | 'warning' | 'emergency';
  emergency: 'active' | 'warning' | 'emergency';
}

export interface ControllerTab {
  id: string;
  name: string;
  active: boolean;
}

export interface WeatherData {
  wind: string;
  visibility: string;
  ceiling: string;
  altimeter: string;
  alerts: string[];
}

export type Sector = 'TOWER' | 'GROUND' | 'APPROACH' | 'CENTER' | 'COORD';
export type Direction = 'TX' | 'RX';

export interface LogEntry {
  id: string;
  timeUtc: string;           // ISO string
  sector: Sector;            // which AI controller
  callsign: string;
  frequency: string;         // e.g., "121.65"
  direction: Direction;      // TX/RX
  summary: string;           // short transcript summary
  lat?: number; lon?: number;
  altFt?: number; spdKt?: number; hdg?: number;
  phase?: 'ENTRY'|'ENROUTE'|'SEQ'|'RUNWAY'|'GROUND'|'GATE';
  arrivalOrDeparture?: 'ARRIVAL'|'DEPARTURE';
}

// --- New/extended types for logs ---
export type LogDirection = 'TX' | 'RX' | 'CPDLC' | 'XFER' | 'SYS';

export interface AtcLogEntry {
  id: string;                 // uuid
  ts: string;                 // ISO string
  callsign?: string;          // e.g., "DAL123"
  sector?: string;            // e.g., "TWR", "GND", "APP", "CTR"
  frequency?: string;         // e.g., "120.95"
  direction: LogDirection;    // TX | RX | CPDLC | XFER | SYS
  summary: string;            // short message shown in UI
  arrival?: boolean;          // arrivals (red) vs departures (green). If undefined, neutral.
  flight?: {
    type?: string;            // A320, B738, etc.
    from?: string;            // ICAO
    to?: string;              // ICAO
    squawk?: string;
  };
  // Voice-ready fields (optional for future):
  audioUrl?: string;          // if present, show play button
  transcript?: string;        // searchable text of the audio
  // For handoffs:
  handoffFrom?: string;       // e.g., "TWR"
  handoffTo?: string;         // e.g., "APP"
}
