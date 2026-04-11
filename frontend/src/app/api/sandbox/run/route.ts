import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const baseUrl = (process.env.API_BASE_URL || 'http://backend:8000/api/v1').replace('/v1', '');
    const backendUrl = `${baseUrl}/sandbox/run`;
    const body = await request.json();

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Backend sandbox responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in Sandbox Proxy:', error);
    return NextResponse.json({
      success: false,
      message: 'Proxy Error: Unable to run simulation.'
    }, { status: 503 });
  }
}
