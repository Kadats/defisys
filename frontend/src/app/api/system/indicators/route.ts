import { NextResponse } from 'next/server';
import { buildBackendUrl } from '@/lib/backendEndpoints';

export async function GET() {
  try {
    const backendUrl = buildBackendUrl('/system/indicators');
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
