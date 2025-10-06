import Redis from 'ioredis';
import { Event } from './database';

// Redis configuration
const REDIS_CONFIG = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD,
  retryDelayOnFailover: 100,
  maxRetriesPerRequest: 3,
};

// Redis connections (separate for publishing and subscribing)
export const redis = process.env.SKIP_REDIS === 'true' ? null : new Redis(REDIS_CONFIG);
export const redisPublisher = process.env.SKIP_REDIS === 'true' ? null : new Redis(REDIS_CONFIG);

// Event bus configuration
export const EVENT_CHANNEL = process.env.EVENT_CHANNEL || 'atc:events';
export const EVENT_TYPES = {
  AIRCRAFT_CREATED: 'aircraft.created',
  AIRCRAFT_UPDATED: 'aircraft.updated',
  AIRCRAFT_STATUS_CHANGED: 'aircraft.status_changed',
  AIRCRAFT_POSITION_UPDATED: 'aircraft.position_updated',
  EVENT_CREATED: 'event.created',
  SYSTEM_STATUS: 'system.status',
  COMMUNICATION: 'communication',
} as const;

export type EventType = typeof EVENT_TYPES[keyof typeof EVENT_TYPES];

export interface EventBusMessage {
  type: EventType;
  timestamp: string;
  data: any;
  event?: Event;
}

export class EventBus {
  private redis: Redis | null;
  private redisPublisher: Redis | null;
  private subscribers: Map<string, Set<(message: EventBusMessage) => void>> = new Map();

  constructor(redis: Redis | null, redisPublisher: Redis | null) {
    this.redis = redis;
    this.redisPublisher = redisPublisher;
    if (this.redis) {
      this.setupSubscriber();
    }
  }

  private async setupSubscriber() {
    if (!this.redis) return;

    try {
      await this.redis.subscribe(EVENT_CHANNEL);
      console.log(`📡 Subscribed to Redis channel: ${EVENT_CHANNEL}`);

      this.redis.on('message', (channel, message) => {
        if (channel === EVENT_CHANNEL) {
          try {
            const eventMessage: EventBusMessage = JSON.parse(message);
            this.notifySubscribers(eventMessage);
          } catch (error) {
            console.error('Failed to parse event message:', error);
          }
        }
      });
    } catch (error) {
      console.error('Failed to setup Redis subscriber:', error);
    }
  }

  private notifySubscribers(message: EventBusMessage) {
    const subscribers = this.subscribers.get(message.type) || new Set();
    subscribers.forEach(callback => {
      try {
        callback(message);
      } catch (error) {
        console.error('Error in event subscriber:', error);
      }
    });
  }

  async publish(type: EventType, data: any, event?: Event): Promise<void> {
    if (!this.redisPublisher) {
      console.log('Redis publisher not available, event not published:', { type, data });
      return;
    }

    try {
      const message: EventBusMessage = {
        type,
        timestamp: new Date().toISOString(),
        data,
        event,
      };

      await this.redisPublisher.publish(EVENT_CHANNEL, JSON.stringify(message));
      console.log(`📤 Published event: ${type}`);
    } catch (error) {
      console.error('Failed to publish event:', error);
    }
  }

  subscribe(type: EventType, callback: (message: EventBusMessage) => void): () => void {
    if (!this.subscribers.has(type)) {
      this.subscribers.set(type, new Set());
    }
    
    this.subscribers.get(type)!.add(callback);

    // Return unsubscribe function
    return () => {
      const subscribers = this.subscribers.get(type);
      if (subscribers) {
        subscribers.delete(callback);
        if (subscribers.size === 0) {
          this.subscribers.delete(type);
        }
      }
    };
  }

  async publishAircraftCreated(aircraft: any): Promise<void> {
    await this.publish(EVENT_TYPES.AIRCRAFT_CREATED, { aircraft });
  }

  async publishAircraftUpdated(aircraft: any, changes: any): Promise<void> {
    await this.publish(EVENT_TYPES.AIRCRAFT_UPDATED, { aircraft, changes });
  }

  async publishAircraftStatusChanged(aircraft: any, oldStatus: string, newStatus: string): Promise<void> {
    await this.publish(EVENT_TYPES.AIRCRAFT_STATUS_CHANGED, { 
      aircraft, 
      oldStatus, 
      newStatus 
    });
  }

  async publishAircraftPositionUpdated(aircraft: any, position: any): Promise<void> {
    await this.publish(EVENT_TYPES.AIRCRAFT_POSITION_UPDATED, { 
      aircraft, 
      position 
    });
  }

  async publishEventCreated(event: Event): Promise<void> {
    await this.publish(EVENT_TYPES.EVENT_CREATED, { event }, event);
  }

  async publishSystemStatus(status: any): Promise<void> {
    await this.publish(EVENT_TYPES.SYSTEM_STATUS, { status });
  }

  async publishCommunication(communication: any): Promise<void> {
    await this.publish(EVENT_TYPES.COMMUNICATION, { communication });
  }
}

// Global event bus instance
export const eventBus = new EventBus(redis, redisPublisher);

// Helper functions for common event publishing patterns
export async function publishAircraftEvent(
  type: 'created' | 'updated' | 'status_changed' | 'position_updated',
  aircraft: any,
  additionalData?: any
): Promise<void> {
  const eventType = `aircraft.${type}` as EventType;
  await eventBus.publish(eventType, { aircraft, ...additionalData });
}

export async function publishSystemEvent(
  type: 'status' | 'communication',
  data: any
): Promise<void> {
  const eventType = `system.${type}` as EventType;
  await eventBus.publish(eventType, { [type]: data });
}

// Health check for Redis connection
export async function checkRedisHealth(): Promise<boolean> {
  if (!redis || !redisPublisher) {
    console.log('Redis connection skipped (SKIP_REDIS=true)');
    return false;
  }
  
  try {
    await redis.ping();
    await redisPublisher.ping();
    return true;
  } catch (error) {
    console.error('Redis health check failed:', error);
    return false;
  }
}
