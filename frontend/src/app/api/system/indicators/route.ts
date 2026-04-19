import { buildBackendUrl } from '@/lib/backendEndpoints';
import { proxyJsonRequest } from '@/lib/bffProxy';

export async function GET() {
  const backendUrl = buildBackendUrl('/system/indicators');
  return proxyJsonRequest({
    backendUrl,
    init: { next: { revalidate: 0 } },
    fallback: () => ({
      rsi: 50,
      fear_and_greed: 50,
      market_regime: 'offline',
    }),
    logLabel: 'Error in Indicators Proxy',
  });
}
