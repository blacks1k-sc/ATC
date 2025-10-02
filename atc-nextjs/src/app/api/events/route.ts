import { NextRequest, NextResponse } from 'next/server';
import { 
  pool, 
  withTransaction, 
  EventRepository 
} from '@/lib/database';

// GET /api/events - List events with filters
export async function GET(request: NextRequest) {
  try {
    if (!pool) {
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      );
    }

    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '100');
    const level = searchParams.get('level');
    const type = searchParams.get('type');
    const aircraft_id = searchParams.get('aircraft_id');
    const sector = searchParams.get('sector');

    const filters: any = {};
    if (level) filters.level = level;
    if (type) filters.type = type;
    if (aircraft_id) filters.aircraft_id = parseInt(aircraft_id);
    if (sector) filters.sector = sector;

    const events = await withTransaction(async (client) => {
      const eventRepo = new EventRepository(client);
      return await eventRepo.findRecent(limit, filters);
    });

    return NextResponse.json({
      success: true,
      events,
      count: events.length,
      filters
    });

  } catch (error) {
    console.error('Error fetching events:', error);
    return NextResponse.json(
      { error: 'Failed to fetch events' },
      { status: 500 }
    );
  }
}
