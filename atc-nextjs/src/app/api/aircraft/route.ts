import { NextRequest, NextResponse } from 'next/server';
import { withTransaction } from '@/lib/database';
import { AircraftInstanceRepository } from '@/lib/database';

export async function GET(request: NextRequest) {
  try {
    const result = await withTransaction(async (client) => {
      const aircraftRepo = new AircraftInstanceRepository(client);
      
      // Get all active aircraft with joins
      const aircraft = await aircraftRepo.findAllActive();
      
      return { aircraft };
    });

    return NextResponse.json({
      success: true,
      aircraft: result.aircraft,
      count: result.aircraft.length,
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    console.error('Error fetching aircraft:', error);
    
    return NextResponse.json(
      { 
        success: false,
        error: 'Failed to fetch aircraft data',
        details: error.message 
      },
      { status: 500 }
    );
  }
}