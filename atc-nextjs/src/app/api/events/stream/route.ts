import { NextRequest } from 'next/server';
import { eventBus, EVENT_TYPES, type EventType } from '@/lib/eventBus';
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
  const typeParams = searchParams.getAll('type').filter(Boolean);
  const aircraft_id = searchParams.get('aircraft_id');
  const sector = searchParams.get('sector');

  const listenTypes = (typeParams.length > 0
    ? Array.from(new Set(typeParams))
    : [EVENT_TYPES.EVENT_CREATED]) as EventType[];

  const filters: any = {};
  if (level) filters.level = level;
  if (listenTypes.length === 1) {
    filters.type = listenTypes[0];
  }
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
      const unsubscribers: Array<() => void> = [];

      const handleMessage = (message: any) => {
        try {
          if (!message) return;

          if (message.type === EVENT_TYPES.EVENT_CREATED) {
            const event = message.event;
            if (!event) return;

            if (filters.level && event.level !== filters.level) {
              return;
            }

            if (filters.type && event.type !== filters.type) {
              return;
            }

            if (filters.aircraft_id && event.aircraft_id !== filters.aircraft_id) {
              return;
            }

            if (filters.sector && event.sector !== filters.sector) {
              return;
            }
          }

          const payload = {
            type: message.type,
            data: message.data,
            event: message.event,
            timestamp: message.timestamp,
          };

          const data = `data: ${JSON.stringify(payload)}\n\n`;
          if (controller.desiredSize !== null) {
            controller.enqueue(encoder.encode(data));
          }
        } catch (error) {
          console.error('Error processing real-time event:', error);
        }
      };

      listenTypes.forEach((eventType) => {
        const unsubscribe = eventBus.subscribe(eventType, handleMessage);
        unsubscribers.push(unsubscribe);
      });

      // Send initial events
      sendInitialEvents();

      // Handle client disconnect
      const cleanup = () => {
        unsubscribers.forEach((unsubscribe) => {
          try {
            unsubscribe();
          } catch (error) {
            console.error('Error unsubscribing from event bus:', error);
          }
        });
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
