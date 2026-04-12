import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketOptions {
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxRetries?: number;
}

export function useWebSocket(url: string, options: WebSocketOptions = {}) {
  const [data, setData] = useState<unknown>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const connectRef = useRef<() => void>(() => {});
  const maxRetries = options.maxRetries || 5;
  const reconnectInterval = options.reconnectInterval || 3000;

  const connect = useCallback(() => {
    try {
      // Usa NEXT_PUBLIC_API_URL, fazendo fallback para localhost no desenvolvimento local
      let wsBase = `ws://${window.location.hostname}:8000`;
      if (process.env.NEXT_PUBLIC_API_URL) {
        try {
          const apiUrl = new URL(process.env.NEXT_PUBLIC_API_URL);
          wsBase = `ws://${apiUrl.host}`;
        } catch (e) {
          console.warn("Invalid NEXT_PUBLIC_API_URL provided, falling back to local hostname");
        }
      }
      const socketUrl = `${wsBase}${url}`;

      console.log(`[useWebSocket] Attempting connection to: ${socketUrl}`);
      ws.current = new WebSocket(socketUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        options.onConnect?.();
        console.log(`[useWebSocket] Connected to ${socketUrl}`);
      };

      ws.current.onmessage = (event) => {
        try {
          // Try parsing JSON first
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
          options.onMessage?.(parsedData);
        } catch {
          // If not JSON, use raw data as fallback
          setData(event.data);
          options.onMessage?.(event.data);
        }
      };

      ws.current.onclose = (event) => {
        setIsConnected(false);
        options.onDisconnect?.();
        
        if (reconnectAttempts.current < maxRetries && !event.wasClean) {
          reconnectAttempts.current += 1;
          const delay = reconnectInterval * Math.min(reconnectAttempts.current, 5); // Exponential-ish backoff
          console.log(`[useWebSocket] Disconnected (Code: ${event.code}). Retrying in ${delay}ms (${reconnectAttempts.current}/${maxRetries})...`);
          setTimeout(() => connectRef.current(), delay);
        }
      };

      ws.current.onerror = (event) => {
        setError(event);
        console.error(`[useWebSocket] Connection failed to: ${socketUrl}`, event);
      };
    } catch (err) {
      console.error('[useWebSocket] Connection Exception:', err);
    }
  }, [url, options, maxRetries, reconnectInterval]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((message: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }, []);

  return { data, isConnected, error, sendMessage };
}
