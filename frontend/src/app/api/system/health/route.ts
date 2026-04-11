import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // BFF Proxy: Chamada interna entre containers Docker (backend:8000)
    // Tenta usar a env var, removendo o sufixo /v1 se presente para endpoints de sistema
    const baseUrl = (process.env.API_BASE_URL || 'http://backend:8000/api/v1').replace('/v1', '');
    const backendUrl = `${baseUrl}/system/health`;
    
    const response = await fetch(backendUrl, {
      next: { revalidate: 0 }, // Garantir que não haja cache para o health check
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in Health Proxy:', error);
    
    // Fallback amigável caso o backend esteja offline
    return NextResponse.json({
      primary: { status: 'offline', latency: 0, url: 'N/A' },
      secondary: { status: 'offline', latency: 0, url: 'N/A' },
      decentralized: { status: 'offline', latency: 0, url: 'N/A' }
    }, { status: 503 });
  }
}
