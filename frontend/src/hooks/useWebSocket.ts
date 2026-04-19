import { useState, useEffect, useCallback, useRef } from 'react';
import { getBackendWebSocketBase } from '@/lib/backendEndpoints';

interface WebSocketOptions {
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxRetries?: number;
}

const DEFAULT_MAX_RETRIES = 5;
const DEFAULT_RECONNECT_INTERVAL = 3000;

export function useWebSocket(url: string, options?: WebSocketOptions) {
  const [data, setData] = useState<unknown>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);
  const connectRef = useRef<() => void>(() => {});
  const onMessageRef = useRef<WebSocketOptions['onMessage']>(undefined);
  const onConnectRef = useRef<WebSocketOptions['onConnect']>(undefined);
  const onDisconnectRef = useRef<WebSocketOptions['onDisconnect']>(undefined);

  const maxRetries = options?.maxRetries ?? DEFAULT_MAX_RETRIES;
  const reconnectInterval = options?.reconnectInterval ?? DEFAULT_RECONNECT_INTERVAL;

  useEffect(() => {
    onMessageRef.current = options?.onMessage;
    onConnectRef.current = options?.onConnect;
    onDisconnectRef.current = options?.onDisconnect;
  }, [options?.onMessage, options?.onConnect, options?.onDisconnect]);

  const connect = useCallback(() => {
    if (!shouldReconnect.current) return;
    if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const wsBase = getBackendWebSocketBase(window.location.hostname);
      const socketUrl = `${wsBase}${url}`;

      console.log(`[useWebSocket] Attempting connection to: ${socketUrl}`);
      ws.current = new WebSocket(socketUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        onConnectRef.current?.();
        console.log(`[useWebSocket] Connected to ${socketUrl}`);
      };

      ws.current.onmessage = (event) => {
        try {
          // Try parsing JSON first
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
          onMessageRef.current?.(parsedData);
        } catch {
          // If not JSON, use raw data as fallback
          setData(event.data);
          onMessageRef.current?.(event.data);
        }
      };

      ws.current.onclose = (event) => {
        ws.current = null;
        setIsConnected(false);
        onDisconnectRef.current?.();

        if (
          shouldReconnect.current &&
          reconnectAttempts.current < maxRetries &&
          !event.wasClean
        ) {
          reconnectAttempts.current += 1;
          const delay = reconnectInterval * Math.min(reconnectAttempts.current, 5); // Exponential-ish backoff
          console.log(`[useWebSocket] Disconnected (Code: ${event.code}). Retrying in ${delay}ms (${reconnectAttempts.current}/${maxRetries})...`);
          reconnectTimer.current = setTimeout(() => connectRef.current(), delay);
        }
      };

      ws.current.onerror = (event) => {
        setError(event);
        console.error(`[useWebSocket] Connection failed to: ${socketUrl}`, event);
      };
    } catch (err) {
      console.error('[useWebSocket] Connection Exception:', err);
    }
  }, [url, maxRetries, reconnectInterval]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    shouldReconnect.current = true;
    connect();

    return () => {
      shouldReconnect.current = false;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      ws.current?.close();
      ws.current = null;
    };
  }, [connect]);

  const sendMessage = useCallback((message: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }, []);

  return { data, isConnected, error, sendMessage };
}
