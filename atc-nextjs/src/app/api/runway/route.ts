import { NextRequest, NextResponse } from 'next/server';
import { redis } from '@/lib/eventBus';

const VALID_RUNWAYS = new Set([
  '05', '23', '06L', '24R', '06R', '24L', '15L', '33R', '15R', '33L',
]);

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const runway: string = (body.runway ?? '').toString().trim().toUpperCase();

    if (!VALID_RUNWAYS.has(runway)) {
      return NextResponse.json(
        { success: false, error: `Unknown runway: ${runway}` },
        { status: 400 },
      );
    }

    if (redis) {
      await redis.set('atc:active_runway', runway);
    }

    return NextResponse.json({ success: true, runway });
  } catch (error: any) {
    console.error('Error setting active runway:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 },
    );
  }
}

export async function GET() {
  try {
    const runway = redis ? await redis.get('atc:active_runway') : null;
    return NextResponse.json({ runway: runway ?? '23' });
  } catch (error: any) {
    return NextResponse.json({ runway: '23' });
  }
}
