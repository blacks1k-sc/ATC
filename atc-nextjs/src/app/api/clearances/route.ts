import { NextRequest, NextResponse } from 'next/server';
import { pool, withTransaction } from '@/lib/database';

// GET /api/clearances - Get recent LLM clearances
export async function GET(request: NextRequest) {
  try {
    if (!pool) {
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      );
    }

    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '10');
    const status = searchParams.get('status') || 'ACTIVE';

    const result = await withTransaction(async (client) => {
      // Check if clearances table exists
      const tableCheck = await client.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_schema = 'public' 
          AND table_name = 'clearances'
        )
      `);

      if (!tableCheck.rows[0].exists) {
        return { clearances: [], count: 0 };
      }

      // Fetch recent clearances with aircraft info
      // Note: validated is stored in instructions JSONB, not as separate column
      const query = `
        SELECT 
          c.id,
          c.aircraft_id,
          c.clearance_type,
          c.issued_by,
          c.issued_at,
          c.status,
          c.instructions,
          c.reason,
          c.confidence,
          ai.callsign,
          ai.current_zone,
          ai.phase
        FROM clearances c
        LEFT JOIN aircraft_instances ai ON c.aircraft_id = ai.id
        WHERE c.status = $1
        ORDER BY c.issued_at DESC
        LIMIT $2
      `;

      const result = await client.query(query, [status, limit]);
      
      const clearances = result.rows.map(row => {
        const instructions = typeof row.instructions === 'string' 
          ? JSON.parse(row.instructions) 
          : row.instructions;
        
        // Extract validated from instructions if present, default to true for active clearances
        const validated = instructions?.validated !== undefined 
          ? instructions.validated 
          : true; // Assume validated if not specified
        
        return {
          id: row.id,
          aircraft_id: row.aircraft_id,
          callsign: row.callsign || 'UNKNOWN',
          clearance_type: row.clearance_type,
          issued_by: row.issued_by,
          issued_at: row.issued_at,
          status: row.status,
          instructions: instructions,
          reason: row.reason,
          confidence: row.confidence,
          validated: validated,
          current_zone: row.current_zone,
          phase: row.phase
        };
      });

      return { clearances, count: clearances.length };
    });

    return NextResponse.json({
      success: true,
      clearances: result.clearances,
      count: result.count,
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    console.error('Error fetching clearances:', error);
    return NextResponse.json(
      { 
        success: false,
        error: 'Failed to fetch clearances',
        details: error.message 
      },
      { status: 500 }
    );
  }
}

