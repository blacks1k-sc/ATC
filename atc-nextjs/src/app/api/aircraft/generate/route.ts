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
import { generateRealisticPosition, calculateDistanceToAirport, calculateSector } from '@/utils/geoUtils';

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

// Note: Position generation and distance calculation now handled by geoUtils.ts
// This ensures consistency with the Python engine and eliminates hardcoded values

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
        
        // Generate position and flight data using logic-based calculations
        const positionData = generateRealisticPosition(flightType);
        const { lat, lon, altitude_ft, heading, speed_kts, distance_to_airport_nm } = positionData;
        
        const position = { lat, lon, altitude_ft, heading, speed_kts };
        const squawkCode = generateSquawkCode();
        const flightPlan = generateFlightPlan(flightType, airlineName);
        
        // Calculate sector based on actual distance
        const sector = calculateSector(distance_to_airport_nm);

        // Create aircraft instance with calculated distance and sector
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
          controller: 'ENGINE',
          distance_to_airport_nm: distance_to_airport_nm,
          sector: sector
        });

        // Create event with calculated sector
        const event = await eventRepo.create({
          level: 'INFO',
          type: 'aircraft.created',
          message: `Aircraft ${callsign} (${selectedAircraftType.icao_type}) ${flightType} created for ${selectedAirline.name} at ${distance_to_airport_nm.toFixed(1)} NM`,
          details: {
            aircraft_type: selectedAircraftType.icao_type,
            airline: selectedAirline.name,
            flight_type: flightType,
            position,
            squawk_code: squawkCode,
            flight_plan: flightPlan,
            distance_to_airport_nm: distance_to_airport_nm,
            sector: sector
          },
          aircraft_id: aircraft.id,
          sector: sector,
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