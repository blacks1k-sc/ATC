import { NextRequest, NextResponse } from 'next/server';
import { 
  pool, 
  withTransaction, 
  AircraftInstanceRepository,
  EventRepository 
} from '@/lib/database';
import { eventBus } from '@/lib/eventBus';

// GET /api/aircraft/[id] - Get specific aircraft
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    if (!pool) {
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      );
    }

    const aircraftId = parseInt(params.id);
    if (isNaN(aircraftId)) {
      return NextResponse.json(
        { error: 'Invalid aircraft ID' },
        { status: 400 }
      );
    }

    const aircraft = await withTransaction(async (client) => {
      const aircraftRepo = new AircraftInstanceRepository(client);
      return await aircraftRepo.findById(aircraftId);
    });

    if (!aircraft) {
      return NextResponse.json(
        { error: 'Aircraft not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      aircraft
    });

  } catch (error) {
    console.error('Error fetching aircraft:', error);
    return NextResponse.json(
      { error: 'Failed to fetch aircraft' },
      { status: 500 }
    );
  }
}

// PUT /api/aircraft/[id] - Update aircraft
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    if (!pool) {
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      );
    }

    const aircraftId = parseInt(params.id);
    if (isNaN(aircraftId)) {
      return NextResponse.json(
        { error: 'Invalid aircraft ID' },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { position, status, squawk_code, flight_plan } = body;

    const result = await withTransaction(async (client) => {
      const aircraftRepo = new AircraftInstanceRepository(client);
      const eventRepo = new EventRepository(client);

      // Get current aircraft data
      const currentAircraft = await aircraftRepo.findById(aircraftId);
      if (!currentAircraft) {
        throw new Error('Aircraft not found');
      }

      const changes: any = {};
      const events: any[] = [];

      // Update position if provided
      if (position) {
        await aircraftRepo.updatePosition(aircraftId, position);
        changes.position = position;
        events.push({
          level: 'INFO',
          type: 'aircraft.position_updated',
          message: `Aircraft ${currentAircraft.callsign} position updated`,
          details: { position },
          aircraft_id: aircraftId,
          sector: 'TWR',
          direction: 'SYS',
        });
      }

      // Update status if provided
      if (status && status !== currentAircraft.status) {
        await aircraftRepo.updateStatus(aircraftId, status);
        changes.status = { from: currentAircraft.status, to: status };
        events.push({
          level: 'INFO',
          type: 'aircraft.status_changed',
          message: `Aircraft ${currentAircraft.callsign} status changed from ${currentAircraft.status} to ${status}`,
          details: { oldStatus: currentAircraft.status, newStatus: status },
          aircraft_id: aircraftId,
          sector: 'TWR',
          direction: 'SYS',
        });
      }

      // Update other fields if provided
      if (squawk_code || flight_plan) {
        const updateFields: string[] = [];
        const updateValues: any[] = [];
        let paramCount = 0;

        if (squawk_code !== undefined) {
          paramCount++;
          updateFields.push(`squawk_code = $${paramCount}`);
          updateValues.push(squawk_code);
          changes.squawk_code = squawk_code;
        }

        if (flight_plan !== undefined) {
          paramCount++;
          updateFields.push(`flight_plan = $${paramCount}`);
          updateValues.push(JSON.stringify(flight_plan));
          changes.flight_plan = flight_plan;
        }

        if (updateFields.length > 0) {
          paramCount++;
          updateFields.push(`updated_at = NOW()`);
          updateValues.push(aircraftId);

          await client.query(
            `UPDATE aircraft_instances SET ${updateFields.join(', ')} WHERE id = $${paramCount}`,
            updateValues
          );
        }
      }

      // Create events for the changes
      const createdEvents = [];
      for (const eventData of events) {
        const event = await eventRepo.create(eventData);
        createdEvents.push(event);
      }

      // Get updated aircraft data
      const updatedAircraft = await aircraftRepo.findById(aircraftId);

      return { aircraft: updatedAircraft, events: createdEvents, changes };
    });

    // Publish events to Redis
    for (const event of result.events) {
      await eventBus.publishEventCreated(event);
    }

    if (result.changes.position) {
      await eventBus.publishAircraftPositionUpdated(result.aircraft, result.changes.position);
    }

    if (result.changes.status) {
      await eventBus.publishAircraftStatusChanged(
        result.aircraft, 
        result.changes.status.from, 
        result.changes.status.to
      );
    }

    return NextResponse.json({
      success: true,
      aircraft: result.aircraft,
      events: result.events,
      changes: result.changes,
      message: 'Aircraft updated successfully'
    });

  } catch (error: any) {
    console.error('Error updating aircraft:', error);
    
    if (error.message.includes('not found')) {
      return NextResponse.json(
        { error: error.message },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to update aircraft' },
      { status: 500 }
    );
  }
}
