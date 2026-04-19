'use client';

import React, { useState, useEffect, memo } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Server, WifiOff, TrendingUp, TrendingDown } from 'lucide-react';

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
  const [btcChange] = useState(2.4);
  const [ethChange] = useState(-0.8);

  useEffect(() => {
    const timer = setTimeout(() => setIsMounted(true), 0);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (tickerData) {
      if (typeof tickerData === 'object' && (tickerData as { symbol?: string }).symbol === 'BTCUSDT') {
        const timer = setTimeout(() => {
          setBtcPrice((tickerData as { price: number }).price);
          if (!ethPrice) setEthPrice((tickerData as { price: number }).price * 0.052);
        }, 0);
        return () => clearTimeout(timer);
      }
    }
  }, [tickerData, ethPrice]);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/system/health');
      if (!res.ok) throw new Error('Proxy health check failed');
      const data = await res.json();
      setRpcHealth(data);
    } catch (err) {
      console.warn('Backend offline or Proxy error. Showing offline status.', err);
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

  const displayBtc = btcPrice || 64230.50;
  const displayEth = ethPrice || 3450.20;

  return (
    <header className="w-full bg-slate-950/80 border-b border-slate-800/60 px-5 py-2.5 flex items-center justify-between backdrop-blur-md z-10 shrink-0">
      {/* Left: connection + prices */}
      <div className="flex items-center gap-6">
        {/* Live feed indicator */}
        <div className="flex items-center gap-2">
          <div className="relative flex">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            {isConnected && (
              <div className="absolute inset-0 w-2 h-2 rounded-full bg-emerald-500 animate-ping opacity-40" />
            )}
          </div>
          <span className={`text-[10px] font-mono uppercase tracking-widest font-bold ${isConnected ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isConnected ? 'Live' : 'Offline'}
          </span>
        </div>

        <div className="w-px h-4 bg-slate-800" />

        {/* BTC */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <span className="text-[9px] text-slate-600 font-mono font-bold uppercase tracking-widest">BTC/USDT</span>
            <div className="flex items-center gap-1.5">
              <span suppressHydrationWarning className="text-xs font-mono font-bold text-white">
                ${isMounted ? displayBtc.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '...'}
              </span>
              <span className={`flex items-center text-[9px] font-mono font-bold ${btcChange >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {btcChange >= 0 ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
                {btcChange >= 0 ? '+' : ''}{btcChange}%
              </span>
            </div>
          </div>

          <div className="flex flex-col">
            <span className="text-[9px] text-slate-600 font-mono font-bold uppercase tracking-widest">ETH/USDT</span>
            <div className="flex items-center gap-1.5">
              <span suppressHydrationWarning className="text-xs font-mono font-bold text-white">
                ${isMounted ? displayEth.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '...'}
              </span>
              <span className={`flex items-center text-[9px] font-mono font-bold ${ethChange >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {ethChange >= 0 ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
                {ethChange >= 0 ? '+' : ''}{ethChange}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Right: RPC nodes */}
      <div className="flex items-center gap-2">
        <span className="text-[9px] text-slate-600 font-mono uppercase tracking-widest mr-1 hidden sm:block">RPC Nodes</span>
        {rpcHealth ? (
          Object.entries(rpcHealth).map(([name, info]) => {
            const ok = info.status === 'ok';
            return (
              <div
                key={name}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[10px] font-mono transition-all ${
                  ok
                    ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400'
                    : 'bg-rose-500/5 border-rose-500/20 text-rose-400'
                }`}
              >
                <Server size={10} className={ok ? 'text-emerald-500' : 'text-rose-500'} />
                <span className="uppercase text-slate-300 hidden md:inline">{name}</span>
                <span className={`font-bold ${ok ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {ok ? `${info.latency}ms` : 'DOWN'}
                </span>
              </div>
            );
          })
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-800 bg-slate-900/50 text-[10px]">
            <WifiOff size={10} className="text-slate-500" />
            <span className="text-slate-500 font-mono uppercase tracking-widest animate-pulse">Connecting...</span>
          </div>
        )}
      </div>
    </header>
  );
}

export default memo(TickerHeader);
