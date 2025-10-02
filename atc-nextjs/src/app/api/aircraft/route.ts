import { NextRequest, NextResponse } from 'next/server';
import { 
  pool, 
  withTransaction, 
  AircraftInstanceRepository 
} from '@/lib/database';
import { eventBus } from '@/lib/eventBus';

// GET /api/aircraft - List active aircraft
export async function GET(request: NextRequest) {
  try {
    if (!pool) {
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      );
    }

    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status') || 'active';
    const limit = parseInt(searchParams.get('limit') || '100');

    const aircraft = await withTransaction(async (client) => {
      const aircraftRepo = new AircraftInstanceRepository(client);
      
      if (status === 'active') {
        return await aircraftRepo.findAllActive();
      } else {
        // For other statuses, we'd need to implement a more flexible query
        return await aircraftRepo.findAllActive();
      }
    });

    return NextResponse.json({
      success: true,
      aircraft: aircraft.slice(0, limit),
      count: aircraft.length
    });

  } catch (error) {
    console.error('Error fetching aircraft:', error);
    return NextResponse.json(
      { error: 'Failed to fetch aircraft' },
      { status: 500 }
    );
  }
}
