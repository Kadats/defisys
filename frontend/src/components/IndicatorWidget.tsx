'use client';

import React, { useState, useEffect } from 'react';
import { Gauge, TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';

interface IndicatorData {
  rsi: number;
  fear_and_greed: number;
  market_regime: string;
}

function ArcGauge({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min(value / max, 1);
  const r = 28;
  const circ = 2 * Math.PI * r;
  const arcLen = circ * 0.75;
  const filled = arcLen * pct;
  const offset = circ * 0.125;

  return (
    <svg width="72" height="72" viewBox="0 0 72 72" className="rotate-[135deg]">
      <circle
        cx="36" cy="36" r={r}
        fill="none"
        stroke="#1e293b"
        strokeWidth="6"
        strokeDasharray={`${arcLen} ${circ - arcLen}`}
        strokeDashoffset={-offset}
        strokeLinecap="round"
      />
      <circle
        cx="36" cy="36" r={r}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeDasharray={`${filled} ${circ - filled}`}
        strokeDashoffset={-offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(0.4, 0, 0.2, 1)', filter: `drop-shadow(0 0 6px ${color}60)` }}
      />
    </svg>
  );
}

const REGIME_MAP: Record<string, { label: string; icon: typeof Minus; color: string }> = {
  bearish: { label: 'Bearish', icon: TrendingDown, color: 'text-rose-400' },
  bull_top: { label: 'Bull Top', icon: TrendingUp, color: 'text-amber-400' },
  sideways: { label: 'Sideways', icon: Minus, color: 'text-sky-400' },
  bullish: { label: 'Bullish', icon: TrendingUp, color: 'text-emerald-400' },
};

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
    const interval = setInterval(fetchIndicators, 30000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, []);

  const displayRsi = data?.rsi ?? 48.5;
  const displayFng = data?.fear_and_greed ?? 42;
  const displayRegime = data?.market_regime ?? 'sideways';

  const getRsiColor = (rsi: number) => {
    if (rsi >= 70) return '#f43f5e';
    if (rsi <= 30) return '#10b981';
    return '#06b6d4';
  };

  const getFngColor = (fng: number) => {
    if (fng >= 70) return '#10b981';
    if (fng <= 30) return '#f43f5e';
    return '#f59e0b';
  };

  const getFngLabel = (fng: number) => {
    if (fng >= 75) return 'Extreme Greed';
    if (fng >= 55) return 'Greed';
    if (fng >= 45) return 'Neutral';
    if (fng >= 25) return 'Fear';
    return 'Extreme Fear';
  };

  const getRsiLabel = (rsi: number) => {
    if (rsi >= 70) return 'Overbought';
    if (rsi <= 30) return 'Oversold';
    return 'Neutral';
  };

  const regime = REGIME_MAP[displayRegime] ?? REGIME_MAP.sideways;
  const RegimeIcon = regime.icon;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {/* RSI Card */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 flex items-center gap-4 hover:border-cyan-500/20 transition-colors group">
        <div className="relative flex-shrink-0">
          <ArcGauge value={isMounted ? displayRsi : 0} color={getRsiColor(displayRsi)} />
          <div className="absolute inset-0 flex items-center justify-center">
            <Gauge size={14} className="text-slate-500 group-hover:text-slate-400 transition-colors" />
          </div>
        </div>
        <div className="min-w-0">
          <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">RSI (14)</p>
          <p suppressHydrationWarning className="text-2xl font-black font-mono leading-none" style={{ color: getRsiColor(displayRsi) }}>
            {isMounted ? displayRsi.toFixed(1) : '--'}
          </p>
          <p className="text-[9px] font-mono text-slate-500 mt-1 uppercase tracking-wide">
            {isMounted ? getRsiLabel(displayRsi) : '...'}
          </p>
          <div className="mt-2 h-0.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-1000"
              style={{ width: `${isMounted ? displayRsi : 0}%`, backgroundColor: getRsiColor(displayRsi) }}
            />
          </div>
        </div>
      </div>

      {/* Fear & Greed Card */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 flex items-center gap-4 hover:border-amber-500/20 transition-colors group">
        <div className="relative flex-shrink-0">
          <ArcGauge value={isMounted ? displayFng : 0} color={getFngColor(displayFng)} />
          <div className="absolute inset-0 flex items-center justify-center">
            <Activity size={14} className="text-slate-500 group-hover:text-slate-400 transition-colors" />
          </div>
        </div>
        <div className="min-w-0">
          <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">Fear & Greed</p>
          <p suppressHydrationWarning className="text-2xl font-black font-mono leading-none" style={{ color: getFngColor(displayFng) }}>
            {isMounted ? displayFng : '--'}
          </p>
          <p className="text-[9px] font-mono text-slate-500 mt-1 uppercase tracking-wide">
            {isMounted ? getFngLabel(displayFng) : '...'}
          </p>
          <div className="mt-2 h-0.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-1000"
              style={{ width: `${isMounted ? displayFng : 0}%`, backgroundColor: getFngColor(displayFng) }}
            />
          </div>
        </div>
      </div>

      {/* Market Regime Card */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 flex items-center gap-4 hover:border-violet-500/20 transition-colors group">
        <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full border border-slate-800 bg-slate-950/60 group-hover:border-slate-700 transition-colors">
          <RegimeIcon size={28} className={regime.color} />
        </div>
        <div className="min-w-0">
          <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">Market Regime</p>
          <p suppressHydrationWarning className={`text-lg font-black uppercase tracking-tight leading-none ${regime.color}`}>
            {isMounted ? regime.label : '--'}
          </p>
          <p className="text-[9px] font-mono text-slate-500 mt-1 uppercase tracking-wide">AI Classification</p>
          <div className="flex gap-1 mt-2">
            {['bearish', 'sideways', 'bull_top', 'bullish'].map((r) => (
              <div
                key={r}
                className={`flex-1 h-0.5 rounded-full transition-all ${displayRegime === r ? 'opacity-100' : 'opacity-20'}`}
                style={{ backgroundColor: REGIME_MAP[r]?.color.replace('text-', '').replace('-400', '') === 'rose' ? '#f43f5e' : REGIME_MAP[r]?.color.replace('text-', '').replace('-400', '') === 'amber' ? '#f59e0b' : REGIME_MAP[r]?.color.replace('text-', '').replace('-400', '') === 'sky' ? '#38bdf8' : '#34d399' }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
