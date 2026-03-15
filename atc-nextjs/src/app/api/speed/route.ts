import { NextRequest, NextResponse } from 'next/server';
import { redis } from '@/lib/eventBus';

const VALID_MULTIPLIERS = new Set([1, 2, 4, 8]);

export async function GET() {
  try {
    const val = redis ? await redis.get('atc:speed_multiplier') : null;
    return NextResponse.json({ multiplier: val ? parseInt(val) : 1 });
  } catch {
    return NextResponse.json({ multiplier: 1 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const { multiplier } = await request.json();
    const m = parseInt(multiplier);
    if (!VALID_MULTIPLIERS.has(m)) {
      return NextResponse.json({ success: false, error: 'Invalid multiplier' }, { status: 400 });
    }
    if (redis) await redis.set('atc:speed_multiplier', m.toString());
    return NextResponse.json({ success: true, multiplier: m });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
