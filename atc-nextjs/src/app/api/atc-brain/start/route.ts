/**
 * API route to start the Python ATC Brain service
 * Proxies request to Python FastAPI service
 */

import { NextRequest, NextResponse } from 'next/server';

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    console.log('🚀 Starting ATC Brain via Python service...');
    
    // Proxy request to Python service
    const response = await fetch(`${PYTHON_SERVICE_URL}/api/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Python service error:', errorText);
      return NextResponse.json(
        { 
          error: 'Failed to start ATC Brain',
          details: errorText 
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('✅ ATC Brain started successfully:', data);
    
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('❌ Error starting ATC Brain:', error);
    return NextResponse.json(
      { 
        error: 'Failed to connect to ATC Brain service',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
