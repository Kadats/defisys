import { buildBackendUrl } from '@/lib/backendEndpoints';
import { proxyJsonRequest } from '@/lib/bffProxy';

export async function POST(request: Request) {
  const backendUrl = buildBackendUrl('/sandbox/run');
  const body = await request.json();
  return proxyJsonRequest({
    backendUrl,
    init: {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    },
    fallback: () => ({
      success: false,
      message: 'Proxy Error: Unable to run simulation.',
    }),
    logLabel: 'Error in Sandbox Proxy',
  });
}
