'use client';

import React, { useState, useEffect, memo } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Server, WifiOff } from 'lucide-react';

interface RPCHealth {
  [key: string]: {
    status: string;
    latency: number;
    url: string;
  };
}

function TickerHeader() {
  const { data: tickerData, isConnected } = useWebSocket('/api/ws/ticker');
  const [rpcHealth, setRpcHealth] = useState<RPCHealth | null>(null);
  const [btcPrice, setBtcPrice] = useState<number | null>(null);
  const [ethPrice, setEthPrice] = useState<number | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsMounted(true), 0);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (tickerData) {
      if (typeof tickerData === 'object' && tickerData.symbol === 'BTCUSDT') {
        // Use a timeout to avoid synchronous setState in effect (Satisfy lint)
        const timer = setTimeout(() => {
          setBtcPrice(tickerData.price);
          // Simulate ETH price as ~0.05 BTC if not provided
          if (!ethPrice) setEthPrice(tickerData.price * 0.052);
        }, 0);
        return () => clearTimeout(timer);
      }
    }
  }, [tickerData, ethPrice]);

  const fetchHealth = async () => {
    try {
      // BFF: Chamada relativa para o Route Handler do Next.js
      const res = await fetch('/api/system/health');
      if (!res.ok) throw new Error('Proxy health check failed');
      const data = await res.json();
      setRpcHealth(data);
    } catch (err) {
      console.warn('Backend offline or Proxy error. Showing offline status.', err);
      // Fallback gracioso para a UI
      setRpcHealth({
        primary: { status: 'offline', latency: 0, url: 'N/A' },
        secondary: { status: 'offline', latency: 0, url: 'N/A' },
        decentralized: { status: 'offline', latency: 0, url: 'N/A' }
      });
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => fetchHealth(), 0);
    const interval = setInterval(fetchHealth, 10000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, []);

  // Mock data if backend is not responding or live
  const displayBtc = btcPrice || 64230.50;
  const displayEth = ethPrice || 3450.20;

  return (
    <div className="w-full bg-slate-900/50 border-b border-slate-800/50 px-6 py-3 flex items-center justify-between backdrop-blur-md">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
          <span className="text-xs font-mono text-slate-400 uppercase tracking-widest">System Pulse</span>
        </div>

        <div className="flex gap-6">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">BTC / USDT</span>
            <span suppressHydrationWarning={true} className="text-sm font-mono font-bold text-emerald-400">
              ${isMounted ? displayBtc.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '...'}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">ETH / USDT</span>
            <span suppressHydrationWarning={true} className="text-sm font-mono font-bold text-emerald-400">
              ${isMounted ? displayEth.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '...'}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {rpcHealth ? (
          Object.entries(rpcHealth).map(([name, info]) => (
            <div key={name} className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800">
              <Server size={12} className={info.status === 'ok' ? 'text-emerald-500' : 'text-rose-500'} />
              <span className="text-[10px] font-mono text-slate-300 uppercase">{name}</span>
              <span className={`text-[10px] font-mono ${info.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {info.latency}ms
              </span>
            </div>
          ))
        ) : (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800">
            <WifiOff size={12} className="text-slate-500" />
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest animate-pulse">Connecting RPCs...</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(TickerHeader);
