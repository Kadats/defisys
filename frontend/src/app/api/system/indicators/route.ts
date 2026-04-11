import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const baseUrl = (process.env.API_BASE_URL || 'http://backend:8000/api/v1').replace('/v1', '');
    const backendUrl = `${baseUrl}/system/indicators`;
    const response = await fetch(backendUrl, { next: { revalidate: 0 } });

    if (!response.ok) {
      throw new Error(`Backend indicators responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in Indicators Proxy:', error);
    return NextResponse.json({
      rsi: 50,
      fear_and_greed: 50,
      market_regime: 'offline'
    }, { status: 503 });
  }
}
