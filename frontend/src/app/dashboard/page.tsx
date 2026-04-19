'use client';

import { Activity, LayoutDashboard, ShieldAlert, TrendingUp, TrendingDown, Cpu, Zap, Clock } from 'lucide-react';
import IndicatorWidget from '@/components/IndicatorWidget';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useState, useEffect } from 'react';

function StatCard({
  label,
  value,
  sub,
  color,
  icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  color: string;
  icon: React.ElementType;
}) {
  return (
    <div className={`relative bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 overflow-hidden group hover:border-opacity-40 transition-all hover:bg-slate-900/80`}>
      <div className={`absolute top-0 right-0 w-20 h-20 rounded-full blur-3xl opacity-0 group-hover:opacity-10 transition-opacity ${color}`} />
      <div className="flex items-start justify-between mb-3">
        <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">{label}</p>
        <div className={`p-1.5 rounded-md bg-slate-800/80`}>
          <Icon size={11} className={color.replace('bg-', 'text-')} />
        </div>
      </div>
      <p className="text-xl font-black font-mono text-white leading-none">{value}</p>
      {sub && <p className="text-[10px] font-mono text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { isConnected } = useWebSocket('/api/ws/ticker');
  const [time, setTime] = useState('');
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const update = () => setTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="text-slate-200 font-sans max-w-screen-2xl mx-auto">
      {/* Page header */}
      <header className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`}>
              {isConnected && <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping opacity-50" />}
            </div>
            <h1 className="text-2xl font-black tracking-tighter text-white uppercase flex items-center gap-2.5">
              <Activity size={22} className="text-cyan-400" />
              War Room
              <span className="text-xs font-mono text-slate-600 font-normal normal-case tracking-normal">v3.0</span>
            </h1>
          </div>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest pl-4">
            DefiSys Institutional Control Center
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-800/80">
            <Clock size={12} className="text-slate-500" />
            <span suppressHydrationWarning className="text-xs font-mono text-slate-300">{isMounted ? time : '--:--:--'}</span>
          </div>
          <div className={`px-3 py-2 rounded-lg border text-xs font-mono font-bold uppercase tracking-widest flex items-center gap-2 ${
            isConnected
              ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400'
              : 'bg-rose-500/5 border-rose-500/20 text-rose-400'
          }`}>
            <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            {isConnected ? 'System Online' : 'System Offline'}
          </div>
        </div>
      </header>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard label="Capital Safety" value="94%" sub="Aave Health > 1.5" color="bg-emerald-500" icon={ShieldAlert} />
        <StatCard label="Active Strategy" value="XGBoost" sub="AI Confidence 0.65" color="bg-violet-500" icon={Cpu} />
        <StatCard label="24h P&L" value="+2.4%" sub="Normalized to USDT" color="bg-cyan-500" icon={TrendingUp} />
        <StatCard label="Max Drawdown" value="-3.1%" sub="Rolling 30d" color="bg-amber-500" icon={TrendingDown} />
      </div>

      {/* Main grid */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Market Intelligence */}
        <section className="lg:col-span-8 space-y-4">
          <div className="bg-slate-900/40 p-5 rounded-2xl border border-slate-800/60 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold flex items-center gap-2.5 text-white uppercase tracking-tight">
                <LayoutDashboard className="text-cyan-400" size={16} />
                Market Intelligence
              </h2>
              <span className="text-[9px] font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 px-2 py-1 rounded-md flex items-center gap-1.5 uppercase tracking-widest font-bold">
                <div className="w-1 h-1 rounded-full bg-cyan-500 animate-pulse" />
                Live Feed
              </span>
            </div>

            <IndicatorWidget />

            {/* Chart placeholder */}
            <div className="mt-4 aspect-video rounded-xl border border-slate-800/80 bg-slate-950/60 flex items-center justify-center group overflow-hidden relative">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(6,182,212,0.06)_0%,transparent_70%)]" />

              {/* Decorative chart lines */}
              <svg className="absolute inset-0 w-full h-full opacity-10" viewBox="0 0 400 200" preserveAspectRatio="none">
                <polyline
                  points="0,160 40,140 80,150 120,100 160,80 200,90 240,60 280,70 320,40 360,55 400,30"
                  fill="none"
                  stroke="#06b6d4"
                  strokeWidth="1.5"
                />
                <polyline
                  points="0,180 40,170 80,175 120,150 160,140 200,145 240,120 280,130 320,100 360,115 400,90"
                  fill="none"
                  stroke="#8b5cf6"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
              </svg>

              <div className="flex flex-col items-center gap-3 relative z-10">
                <div className="w-12 h-12 rounded-full border border-slate-800 flex items-center justify-center bg-slate-900/80 group-hover:scale-105 transition-transform duration-500 group-hover:border-cyan-500/30">
                  <Activity size={22} className="text-slate-600 group-hover:text-cyan-500/60 transition-colors" />
                </div>
                <div className="text-center">
                  <span className="text-slate-500 font-mono text-[10px] uppercase tracking-widest animate-pulse block">
                    Initializing Neural Engine...
                  </span>
                  <span className="text-slate-700 font-mono text-[9px] mt-1 block">Chart data stream pending backend connection</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Right panel */}
        <aside className="lg:col-span-4 flex flex-col gap-4">
          {/* Risk Protocol */}
          <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/60 shadow-xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold flex items-center gap-2.5 text-white uppercase tracking-tight">
                <ShieldAlert className="text-rose-500" size={16} />
                Risk Protocol
              </h2>
              <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-md font-bold uppercase tracking-widest">
                SECURE
              </span>
            </div>

            <div className="space-y-4">
              {/* Capital Safety Bar */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Capital Safety</span>
                  <span className="text-xs font-bold font-mono text-emerald-400">94%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full shadow-[0_0_8px_rgba(16,185,129,0.4)] transition-all duration-1000"
                    style={{ width: '94%', background: 'linear-gradient(90deg, #10b981, #34d399)' }}
                  />
                </div>
              </div>

              {/* Aave Health Factor */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Aave Health Factor</span>
                  <span className="text-xs font-bold font-mono text-cyan-400">2.14</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full shadow-[0_0_8px_rgba(6,182,212,0.4)] transition-all duration-1000"
                    style={{ width: '71%', background: 'linear-gradient(90deg, #06b6d4, #38bdf8)' }}
                  />
                </div>
              </div>

              {/* Liquidity Buffer */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Liquidity Buffer</span>
                  <span className="text-xs font-bold font-mono text-violet-400">87%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full shadow-[0_0_8px_rgba(139,92,246,0.4)] transition-all duration-1000"
                    style={{ width: '87%', background: 'linear-gradient(90deg, #8b5cf6, #a78bfa)' }}
                  />
                </div>
              </div>

              <div className="mt-2 p-3 rounded-xl bg-slate-950/60 border border-slate-800/60">
                <p className="text-[9px] text-slate-500 font-mono uppercase tracking-widest mb-1.5 flex items-center gap-1">
                  <Zap size={9} className="text-emerald-500" />
                  Institutional Status
                </p>
                <p className="text-[10px] text-slate-300 leading-relaxed font-mono">
                  All liquidity buffers operational. Aave health factor within nominal parameters ({'>'}1.5).
                </p>
              </div>
            </div>
          </div>

          {/* System Console */}
          <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800/60 shadow-2xl flex-grow font-mono">
            <div className="flex items-center gap-1.5 mb-3 pb-2.5 border-b border-slate-800/60">
              <div className="w-2 h-2 rounded-full bg-rose-500/60" />
              <div className="w-2 h-2 rounded-full bg-amber-500/60" />
              <div className="w-2 h-2 rounded-full bg-emerald-500/60" />
              <span className="text-[9px] text-slate-600 ml-1.5 uppercase tracking-widest">SYSTEM_CONSOLE v3.0</span>
            </div>
            <div className="space-y-1.5 text-[10px] leading-relaxed">
              <p className="text-slate-500"><span className="text-slate-700">$</span> <span className="text-emerald-400/70">DefiSys v3.0 initializing...</span></p>
              <p className="text-slate-500"><span className="text-slate-700">$</span> <span className="text-emerald-400">[OK]</span> Multi-RPC failover ready.</p>
              <p className="text-slate-500"><span className="text-slate-700">$</span> <span className="text-emerald-400">[OK]</span> Market synchronizer active.</p>
              <p className="text-slate-500"><span className="text-slate-700">$</span> <span className="text-emerald-400">[OK]</span> XGBoost prediction engine idle.</p>
              <p className="text-slate-500"><span className="text-slate-700">$</span> <span className="text-cyan-400">[INFO]</span> Awaiting backend handshake...</p>
              <p className="text-emerald-500/80"><span className="text-slate-700">$</span> <span className="animate-pulse inline-block">▊</span></p>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
