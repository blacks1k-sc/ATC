import { NextRequest, NextResponse } from 'next/server';
import { withTransaction } from '@/lib/database';
import { AircraftInstanceRepository } from '@/lib/database';
import { calculateDistanceToAirport, calculateSector } from '@/utils/geoUtils';

/**
 * API endpoint to recalculate distances and sectors for all active aircraft.
 * This ensures consistency between the NextJS and Python engines.
 */
export async function POST(request: NextRequest) {
  try {
    const result = await withTransaction(async (client) => {
      const aircraftRepo = new AircraftInstanceRepository(client);
      
      // Get all active aircraft
      const aircraft = await aircraftRepo.findAllActive();
      
      let updatedCount = 0;
      const updates = [];
      
      for (const ac of aircraft) {
        if (ac.position?.lat && ac.position?.lon) {
          // Calculate actual distance using the same logic as Python engine
          const distanceToAirport = calculateDistanceToAirport(
            ac.position.lat, 
            ac.position.lon
          );
          
          // Calculate sector based on actual distance
          const sector = calculateSector(distanceToAirport);
          
          // Update the aircraft in database
          await client.query(`
            UPDATE aircraft_instances 
            SET distance_to_airport_nm = $1, phase = $2, updated_at = NOW()
            WHERE id = $3
          `, [distanceToAirport, sector, ac.id]);
          
          updates.push({
            id: ac.id,
            callsign: ac.callsign,
            old_distance: ac.distance_to_airport_nm,
            new_distance: distanceToAirport,
            old_sector: ac.sector,
            new_sector: sector
          });
          
          updatedCount++;
        }
      }
      
      return { updatedCount, updates };
    });

    return NextResponse.json({
      success: true,
      message: `Recalculated distances for ${result.updatedCount} aircraft`,
      updatedCount: result.updatedCount,
      updates: result.updates
    });

  } catch (error: any) {
    console.error('Error recalculating distances:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: 'Failed to recalculate distances',
        details: error.message 
      },
      { status: 500 }
    );
  }
}
