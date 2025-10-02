import { NextResponse } from 'next/server';
import { checkDatabaseConnection, checkRedisConnection } from '@/lib/database';
import { checkRedisHealth } from '@/lib/eventBus';

// GET /api/health - Health check endpoint
export async function GET() {
  try {
    const [dbHealthy, redisHealthy] = await Promise.all([
      checkDatabaseConnection(),
      checkRedisHealth()
    ]);

    const status = {
      database: {
        healthy: dbHealthy,
        status: dbHealthy ? 'connected' : 'disconnected'
      },
      redis: {
        healthy: redisHealthy,
        status: redisHealthy ? 'connected' : 'disconnected'
      },
      overall: dbHealthy && redisHealthy ? 'healthy' : 'degraded',
      timestamp: new Date().toISOString()
    };

    const httpStatus = status.overall === 'healthy' ? 200 : 503;

    return NextResponse.json(status, { status: httpStatus });

  } catch (error) {
    console.error('Health check failed:', error);
    return NextResponse.json(
      {
        database: { healthy: false, status: 'error' },
        redis: { healthy: false, status: 'error' },
        overall: 'unhealthy',
        error: 'Health check failed',
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }
}
