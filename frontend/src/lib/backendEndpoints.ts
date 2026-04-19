const DEFAULT_BACKEND_API_BASE = 'http://backend:8000/api/v1';

function normalizeApiBase(path: string): string {
  const trimmed = path.replace(/\/+$/, '');
  if (/\/api\/v1$/i.test(trimmed)) {
    return trimmed.replace(/\/api\/v1$/i, '/api');
  }
  if (/\/api$/i.test(trimmed)) {
    return trimmed;
  }
  return `${trimmed}/api`;
}

export function getBackendHttpBase(): string {
  const configured = process.env.API_BASE_URL || DEFAULT_BACKEND_API_BASE;
  return normalizeApiBase(configured);
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
