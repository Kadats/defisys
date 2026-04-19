import { NextResponse } from 'next/server';

type FallbackFactory = () => unknown;

function parseBackendBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text().then((text) => ({
    error: text || 'Backend returned non-JSON response',
    status: response.status,
  }));
}

export async function proxyJsonRequest(args: {
  backendUrl: string;
  init?: RequestInit;
  fallback: FallbackFactory;
  logLabel: string;
}): Promise<NextResponse> {
  const { backendUrl, init, fallback, logLabel } = args;
  try {
    const response = await fetch(backendUrl, init);
    const body = await parseBackendBody(response);

    if (!response.ok) {
      return NextResponse.json(body, { status: response.status });
    }

    return NextResponse.json(body);
  } catch (error) {
    console.error(`${logLabel}:`, error);
    return NextResponse.json(fallback(), { status: 503 });
  }
}
