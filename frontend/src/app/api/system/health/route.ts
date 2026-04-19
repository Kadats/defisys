import { buildBackendUrl } from '@/lib/backendEndpoints';
import { proxyJsonRequest } from '@/lib/bffProxy';

export async function GET() {
  const backendUrl = buildBackendUrl('/system/health');
  return proxyJsonRequest({
    backendUrl,
    init: {
      next: { revalidate: 0 }, // Garantir que não haja cache para o health check
    },
    fallback: () => ({
      primary: { status: 'offline', latency: 0, url: 'N/A' },
      secondary: { status: 'offline', latency: 0, url: 'N/A' },
      decentralized: { status: 'offline', latency: 0, url: 'N/A' },
    }),
    logLabel: 'Error in Health Proxy',
  });
}
