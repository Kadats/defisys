import { buildBackendUrl } from '@/lib/backendEndpoints';
import { proxyJsonRequest } from '@/lib/bffProxy';

export async function GET() {
  const backendUrl = buildBackendUrl('/system/logs');
  return proxyJsonRequest({
    backendUrl,
    init: { next: { revalidate: 0 } },
    fallback: () => [
      "ERROR: Console Proxy unable to reach backend."
    ],
    logLabel: 'Error in Logs Proxy',
  });
}
