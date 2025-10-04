/**
 * API route to get the health status of the Python ATC Brain service
 * Proxies request to Python FastAPI service
 */

import { NextRequest, NextResponse } from 'next/server';

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://127.0.0.1:8000';

export async function GET(request: NextRequest) {
  try {
    console.log('🏥 Getting ATC Brain health status...');
    
    // Proxy request to Python service
    const response = await fetch(`${PYTHON_SERVICE_URL}/api/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Python service error:', errorText);
      return NextResponse.json(
        { 
          error: 'Failed to get ATC Brain health',
          details: errorText,
          status: 'unhealthy'
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('✅ ATC Brain health retrieved:', data);
    
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('❌ Error getting ATC Brain health:', error);
    return NextResponse.json(
      { 
        error: 'Failed to connect to ATC Brain service',
        details: error instanceof Error ? error.message : 'Unknown error',
        status: 'unhealthy'
      },
      { status: 500 }
    );
  }
}
