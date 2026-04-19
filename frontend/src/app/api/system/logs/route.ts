import { NextResponse } from 'next/server';
import { buildBackendUrl } from '@/lib/backendEndpoints';

export async function GET() {
  try {
    const backendUrl = buildBackendUrl('/system/logs');
    const response = await fetch(backendUrl, { next: { revalidate: 0 } });

    if (!response.ok) {
      throw new Error(`Backend logs responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in Logs Proxy:', error);
    return NextResponse.json([
      "ERROR: Console Proxy unable to reach backend."
    ], { status: 503 });
  }
}
