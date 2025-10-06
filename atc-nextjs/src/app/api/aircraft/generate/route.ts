import { NextRequest, NextResponse } from 'next/server';
import { 
  pool, 
  withTransaction, 
  AircraftTypeRepository, 
  AirlineRepository, 
  AircraftInstanceRepository, 
  EventRepository 
} from '@/lib/database';
import { eventBus } from '@/lib/eventBus';

interface GenerateAircraftRequest {
  aircraftType: string;
  airline: string;
}

// Generate random ICAO24 address (6-character hex)
function generateICAO24(): string {
  const chars = '0123456789ABCDEF';
  let result = '';
  for (let i = 0; i < 6; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

// Generate random callsign
function generateCallsign(airlineICAO: string): string {
  const numbers = Math.floor(Math.random() * 9000) + 1000; // 1000-9999
  return `${airlineICAO}${numbers}`;
}

// Generate random registration
function generateRegistration(airlineICAO: string): string {
  const numbers = Math.floor(Math.random() * 9000) + 1000; // 1000-9999
  return `${airlineICAO}${numbers}`;
}

// Generate random position around Toronto (arrivals start further out)
function generatePosition(flightType: string = 'ARRIVAL'): { lat: number; lon: number; altitude_ft: number; heading: number; speed_kts: number } {
  const baseLat = 43.6777;
  const baseLon = -79.6248;
  
  if (flightType === 'ARRIVAL') {
    // Start arrivals 30-50 NM away at cruise altitude
    const distance_nm = Math.random() * 20 + 30; // 30-50 NM
    const bearing = Math.random() * 360; // Random direction
    const bearing_rad = (bearing * Math.PI) / 180;
    
    // Convert NM to degrees (approximately)
    const lat = baseLat + (distance_nm / 60) * Math.cos(bearing_rad);
    const lon = baseLon + (distance_nm / (60 * Math.cos((baseLat * Math.PI) / 180))) * Math.sin(bearing_rad);
    
    return {
      lat: lat,
      lon: lon,
      altitude_ft: Math.floor(Math.random() * 10000) + 15000, // 15000-25000 ft
      heading: Math.floor(Math.random() * 360),
      speed_kts: Math.floor(Math.random() * 100) + 250 // 250-350 kts
    };
  } else {
    // Departures start at airport
    return {
      lat: baseLat + (Math.random() - 0.5) * 0.01,
      lon: baseLon + (Math.random() - 0.5) * 0.01,
      altitude_ft: Math.floor(Math.random() * 1000) + 500, // 500-1500 ft
      heading: Math.floor(Math.random() * 360),
      speed_kts: Math.floor(Math.random() * 50) + 150 // 150-200 kts
    };
  }
}

// Generate flight plan
function generateFlightPlan(flightType: string, airline: string): any {
  const origins = ['KJFK', 'KORD', 'KLAX', 'LFPG', 'EGLL', 'OMDB', 'RJTT', 'YSSY'];
  const destinations = ['CYYZ']; // Always Toronto for now
  const runways = ['05L', '05R', '23L', '23R'];
  const entryWaypoints = ['LINNG', 'BOXUM', 'PEDGA', 'DUVNO', 'IMEBA', 'NUBER'];
  
  if (flightType === 'ARRIVAL') {
    return {
      type: 'ARRIVAL',
      origin: origins[Math.floor(Math.random() * origins.length)],
      destination: 'CYYZ',
      entry_waypoint: entryWaypoints[Math.floor(Math.random() * entryWaypoints.length)],
      runway: runways[Math.floor(Math.random() * runways.length)]
    };
  } else {
    return {
      type: 'DEPARTURE',
      origin: 'CYYZ',
      destination: origins[Math.floor(Math.random() * origins.length)],
      runway: runways[Math.floor(Math.random() * runways.length)],
      sid: 'VECTOR' // Simplified
    };
  }
}

// Generate squawk code
function generateSquawkCode(): string {
  return Math.floor(Math.random() * 7777).toString().padStart(4, '0');
}

export async function POST(request: NextRequest) {
  try {
    const { aircraftType, airline }: GenerateAircraftRequest = await request.json();

    if (!aircraftType || !airline) {
      return NextResponse.json(
        { error: 'Aircraft type and airline are required' },
        { status: 400 }
      );
    }

    if (!pool) {
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      );
    }

    // Parse airline (format: "ICAO-Name")
    const [airlineICAO, airlineName] = airline.split('-', 2);

    try {
      const result = await withTransaction(async (client) => {
        const aircraftTypeRepo = new AircraftTypeRepository(client);
        const airlineRepo = new AirlineRepository(client);
        const aircraftRepo = new AircraftInstanceRepository(client);
        const eventRepo = new EventRepository(client);

        // Find the selected aircraft type
        const selectedAircraftType = await aircraftTypeRepo.findByIcaoType(aircraftType);
        if (!selectedAircraftType) {
          throw new Error('Aircraft type not found');
        }

        // Find the selected airline
        const selectedAirline = await airlineRepo.findByIcao(airlineICAO);
        if (!selectedAirline) {
          throw new Error('Airline not found');
        }

        // Generate unique identifiers with retry logic
        let icao24: string;
        let callsign: string;
        let registration: string;
        let attempts = 0;
        const maxAttempts = 10;

        do {
          icao24 = generateICAO24();
          callsign = generateCallsign(airlineICAO);
          registration = generateRegistration(airlineICAO);
          attempts++;

          // Check for uniqueness
          const existingIcao24 = await aircraftRepo.findByIcao24(icao24);
          const existingCallsign = await aircraftRepo.findByCallsign(callsign);
          
          if (!existingIcao24 && !existingCallsign) {
            break;
          }

          if (attempts >= maxAttempts) {
            throw new Error('Failed to generate unique identifiers after maximum attempts');
          }
        } while (true);

        // Force ARRIVAL for current development phase
        const flightType = 'ARRIVAL';
        
        // Generate position and flight data
        const position = generatePosition(flightType);
        const squawkCode = generateSquawkCode();
        const flightPlan = generateFlightPlan(flightType, airlineName);

        // Create aircraft instance
        const aircraft = await aircraftRepo.create({
          icao24,
          registration,
          callsign,
          aircraft_type_id: selectedAircraftType.id,
          airline_id: selectedAirline.id,
          position,
          status: 'active',
          squawk_code: squawkCode,
          flight_plan: flightPlan,
          flight_type: flightType,
          controller: 'ENGINE'
        });

        // Create event
        const event = await eventRepo.create({
          level: 'INFO',
          type: 'aircraft.created',
          message: `Aircraft ${callsign} (${selectedAircraftType.icao_type}) ${flightType} created for ${selectedAirline.name}`,
          details: {
            aircraft_type: selectedAircraftType.icao_type,
            airline: selectedAirline.name,
            flight_type: flightType,
            position,
            squawk_code: squawkCode,
            flight_plan: flightPlan,
          },
          aircraft_id: aircraft.id,
          sector: flightType === 'ARRIVAL' ? 'APP' : 'TWR',
          direction: 'SYS',
        });

        // Get the full aircraft data with joins
        const fullAircraft = await aircraftRepo.findById(aircraft.id);

        return { aircraft: fullAircraft, event };
      });

      // Publish events to Redis
      await eventBus.publishAircraftCreated(result.aircraft);
      await eventBus.publishEventCreated(result.event);

      return NextResponse.json({
        success: true,
        aircraft: result.aircraft,
        event: result.event,
        message: 'Aircraft created successfully'
      });

    } catch (error: any) {
      console.error('Error creating aircraft:', error);
      
      if (error.message.includes('not found')) {
        return NextResponse.json(
          { error: error.message },
          { status: 404 }
        );
      }
      
      if (error.message.includes('unique') || error.message.includes('duplicate')) {
        return NextResponse.json(
          { error: 'Aircraft with this identifier already exists' },
          { status: 409 }
        );
      }

      return NextResponse.json(
        { error: 'Failed to create aircraft' },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('Error generating aircraft:', error);
    return NextResponse.json(
      { error: 'Failed to generate aircraft' },
      { status: 500 }
    );
  }
}