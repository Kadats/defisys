'use client';

import React, { useState, useEffect } from 'react';
import { Gauge, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface IndicatorData {
  rsi: number;
  fear_and_greed: number;
  market_regime: string;
}

export default function IndicatorWidget() {
  const [data, setData] = useState<IndicatorData | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsMounted(true), 0);
    return () => clearTimeout(timer);
  }, []);

  const fetchIndicators = async () => {
    try {
      const res = await fetch('/api/system/indicators');
      if (!res.ok) throw new Error('Proxy failed to fetch indicators');
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.warn('Backend indicators offline or proxy error.', err);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => fetchIndicators(), 0);
    const interval = setInterval(fetchIndicators, 30000); // Poll every 30s
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, []);

  const displayRsi = data?.rsi || 48.5;
  const displayFng = data?.fear_and_greed || 42;
  const displayRegime = data?.market_regime || 'sideways';

  const getRsiColor = (rsi: number) => {
    if (rsi >= 70) return 'text-rose-500';
    if (rsi <= 30) return 'text-emerald-500';
    return 'text-sky-400';
  };

  const getFngColor = (fng: number) => {
    if (fng >= 70) return 'text-emerald-500';
    if (fng <= 30) return 'text-rose-500';
    return 'text-amber-400';
  };

  const getRegimeIcon = (regime: string) => {
    switch (regime) {
      case 'bearish': return <TrendingDown className="text-rose-500" />;
      case 'bull_top': return <TrendingUp className="text-rose-400" />;
      case 'sideways': return <Minus className="text-sky-400" />;
      default: return <Minus className="text-slate-500" />;
    }
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Relative Strength</span>
          <Gauge size={14} className="text-slate-600" />
        </div>
        <div className="flex items-baseline gap-2">
          <span suppressHydrationWarning={true} className={`text-2xl font-mono font-bold ${getRsiColor(displayRsi)}`}>
            {isMounted ? displayRsi.toFixed(1) : '...'}
          </span>
          <span className="text-xs text-slate-600 font-mono">RSI</span>
        </div>
        <div className="mt-3 h-1 w-full bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-1000 ${displayRsi >= 70 ? 'bg-rose-500' : displayRsi <= 30 ? 'bg-emerald-500' : 'bg-sky-500'}`}
            style={{ width: `${isMounted ? displayRsi : 0}%` }}
          />
        </div>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Market Sentiment</span>
          <div className="flex gap-1">
             <div className="w-1 h-1 rounded-full bg-emerald-500" />
             <div className="w-1 h-1 rounded-full bg-amber-500" />
             <div className="w-1 h-1 rounded-full bg-rose-500" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span suppressHydrationWarning={true} className={`text-2xl font-mono font-bold ${getFngColor(displayFng)}`}>
            {isMounted ? displayFng : '...'}
          </span>
          <span className="text-xs text-slate-600 font-mono">F&G</span>
        </div>
        <div className="mt-2 text-[10px] font-mono text-slate-400 flex items-center gap-1">
           Regime: <span className="uppercase font-bold text-slate-200">{isMounted ? displayRegime : '...'}</span>
           {isMounted && getRegimeIcon(displayRegime)}
        </div>
      </div>
    </div>
  );
}
