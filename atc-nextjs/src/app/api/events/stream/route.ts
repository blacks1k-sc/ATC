import { NextRequest } from 'next/server';
import { eventBus, EVENT_TYPES } from '@/lib/eventBus';
import { 
  pool, 
  withTransaction, 
  EventRepository 
} from '@/lib/database';

// SSE endpoint for real-time event streaming
export async function GET(request: NextRequest) {
  if (!pool) {
    return new Response('Database not available', { status: 503 });
  }

  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') || '50');
  const level = searchParams.get('level');
  const type = searchParams.get('type');
  const aircraft_id = searchParams.get('aircraft_id');
  const sector = searchParams.get('sector');

  const filters: any = {};
  if (level) filters.level = level;
  if (type) filters.type = type;
  if (aircraft_id) filters.aircraft_id = parseInt(aircraft_id);
  if (sector) filters.sector = sector;

  // Create a readable stream for SSE
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();

      // Send initial events from database
      const sendInitialEvents = async () => {
        try {
          const events = await withTransaction(async (client) => {
            const eventRepo = new EventRepository(client);
            return await eventRepo.findRecent(limit, filters);
          });

          // Send initial events
          for (const event of events.reverse()) { // Send oldest first
            const data = `data: ${JSON.stringify({
              type: 'initial',
              event
            })}\n\n`;
            if (controller.desiredSize !== null) {
              controller.enqueue(encoder.encode(data));
            }
          }

          // Send a marker that initial events are complete
          const marker = `data: ${JSON.stringify({
            type: 'initial_complete',
            count: events.length
          })}\n\n`;
          if (controller.desiredSize !== null) {
            controller.enqueue(encoder.encode(marker));
          }

        } catch (error) {
          console.error('Error sending initial events:', error);
          const errorData = `data: ${JSON.stringify({
            type: 'error',
            message: 'Failed to load initial events'
          })}\n\n`;
          if (controller.desiredSize !== null) {
            controller.enqueue(encoder.encode(errorData));
          }
        }
      };

      // Subscribe to real-time events
      const unsubscribe = eventBus.subscribe(EVENT_TYPES.EVENT_CREATED, (message) => {
        try {
          // Apply filters to real-time events
          const event = message.event;
          if (!event) return;

          let shouldSend = true;

          if (filters.level && event.level !== filters.level) {
            shouldSend = false;
          }

          if (filters.type && event.type !== filters.type) {
            shouldSend = false;
          }

          if (filters.aircraft_id && event.aircraft_id !== filters.aircraft_id) {
            shouldSend = false;
          }

          if (filters.sector && event.sector !== filters.sector) {
            shouldSend = false;
          }

          if (shouldSend) {
            const data = `data: ${JSON.stringify({
              type: 'realtime',
              event
            })}\n\n`;
            if (controller.desiredSize !== null) {
              controller.enqueue(encoder.encode(data));
            }
          }
        } catch (error) {
          console.error('Error processing real-time event:', error);
        }
      });

      // Send initial events
      sendInitialEvents();

      // Handle client disconnect
      const cleanup = () => {
        unsubscribe();
        controller.close();
      };

      // Set up cleanup on close
      request.signal?.addEventListener('abort', cleanup);
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control',
    },
  });
}
