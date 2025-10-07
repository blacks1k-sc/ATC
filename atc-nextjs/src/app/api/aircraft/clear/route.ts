import { NextResponse } from 'next/server';
import { 
  pool, 
  withTransaction, 
  AircraftInstanceRepository, 
  EventRepository 
} from '@/lib/database';

// DELETE /api/aircraft/clear - Clear all aircraft instances and related events
export async function DELETE() {
  try {
    if (!pool) {
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      );
    }

    const result = await withTransaction(async (client) => {
      const aircraftRepo = new AircraftInstanceRepository(client);
      const eventRepo = new EventRepository(client);
      
      // Get count of aircraft before deletion
      const aircraftCount = await aircraftRepo.count();
      
      // Clear all aircraft instances
      const aircraftResult = await aircraftRepo.clearAll();
      
      // Clear all events
      const eventResult = await eventRepo.clearAll();
      
      return {
        aircraftDeleted: aircraftResult,
        eventsDeleted: eventResult,
        aircraftCount
      };
    });

    return NextResponse.json({
      success: true,
      message: 'All aircraft and events cleared successfully',
      deletedCount: result
    });

  } catch (error) {
    console.error('Error clearing aircraft:', error);
    return NextResponse.json(
      { error: 'Failed to clear aircraft' },
      { status: 500 }
    );
  }
}
