const DEFAULT_BACKEND_API_BASE = 'http://backend:8000/api/v1';

function stripApiV1(path: string): string {
  return path.replace(/\/api\/v1\/?$/, '');
}

export function getBackendHttpBase(): string {
  const configured = process.env.API_BASE_URL || DEFAULT_BACKEND_API_BASE;
  return stripApiV1(configured);
}

export function buildBackendUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getBackendHttpBase()}${normalizedPath}`;
}

export function getBackendWebSocketBase(hostname: string): string {
  const configured = process.env.NEXT_PUBLIC_API_URL;
  if (!configured) {
    return `ws://${hostname}:8000`;
  }

  try {
    const apiUrl = new URL(configured);
    const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${apiUrl.host}`;
  } catch {
    return `ws://${hostname}:8000`;
  }
}
