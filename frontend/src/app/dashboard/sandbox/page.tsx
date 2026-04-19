'use client';

import React, { useState } from 'react';
import { 
  FlaskConical, 
  Play, 
  Settings2, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2,
  BarChart2
} from 'lucide-react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

interface SimulationResult {
  metrics: {
    roi_total: number;
    max_drawdown: number;
    win_rate: number;
  };
  equity_curve: Array<{ date: string; equity: number }>;
}

function MetricCard({
  label,
  value,
  color,
  icon: Icon,
  prefix = '',
}: {
  label: string;
  value: string | number;
  color: string;
  icon: React.ElementType;
  prefix?: string;
}) {
  return (
    <div className={`bg-slate-900/80 border rounded-xl p-5 relative overflow-hidden group transition-all ${color}`}>
      <div className="absolute top-3 right-3 opacity-10 group-hover:opacity-20 transition-opacity">
        <Icon size={40} />
      </div>
      <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-2">{label}</p>
      <p className={`text-3xl font-black font-mono`}>{prefix}{value}</p>
    </div>
  );
}

export default function SandboxLabPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [params, setParams] = useState({
    ai_confidence: 0.65,
    initial_capital: 1000,
    train_window: 180,
    test_window: 30
  });

  const handleRunSimulation = async () => {
    setLoading(true);
    setResult(null);
    try {
      const response = await fetch('/api/sandbox/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!response.ok) throw new Error('Sandbox Proxy failed');
      const data = await response.json();
      if (data.success) setResult(data);
    } catch (error) {
      console.warn('Simulation failed via Proxy.', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-slate-200 font-sans max-w-screen-2xl mx-auto">
      <header className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <h1 className="text-2xl font-black tracking-tighter text-white uppercase flex items-center gap-2.5">
              <FlaskConical size={22} className="text-violet-400" />
              Sandbox Lab
              <span className="text-xs font-mono text-violet-600 font-normal normal-case tracking-normal bg-violet-500/10 px-1.5 py-0.5 rounded border border-violet-500/20">BETA</span>
            </h1>
          </div>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest pl-4">
            Historical Backtesting & Strategy Lab
          </p>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Parameters Panel */}
        <aside className="lg:col-span-3">
          <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/60 shadow-xl sticky top-6">
            <div className="flex items-center gap-2 mb-5 pb-3 border-b border-slate-800/60">
              <Settings2 size={15} className="text-violet-400" />
              <h2 className="text-xs font-bold text-white uppercase tracking-wider">Configuration</h2>
            </div>

            <div className="space-y-5">
              <div>
                <label className="flex justify-between items-center mb-2">
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Confidence Threshold</span>
                  <span className="text-[10px] font-mono text-violet-400 font-bold">{params.ai_confidence}</span>
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="0.95"
                  step="0.05"
                  value={params.ai_confidence}
                  onChange={(e) => setParams({ ...params, ai_confidence: parseFloat(e.target.value) })}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-violet-500"
                />
                <div className="flex justify-between mt-1">
                  <span className="text-[8px] text-slate-700 font-mono">0.50</span>
                  <span className="text-[8px] text-slate-700 font-mono">0.95</span>
                </div>
              </div>

              <div>
                <label className="block text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-2">Initial Capital ($)</label>
                <input
                  type="number"
                  value={params.initial_capital}
                  onChange={(e) => setParams({ ...params, initial_capital: parseInt(e.target.value) })}
                  className="w-full bg-slate-950/80 border border-slate-800/80 rounded-lg px-3 py-2 text-sm font-mono text-white focus:outline-none focus:border-violet-500/50 focus:bg-slate-950 transition-all"
                />
              </div>

              <div>
                <label className="block text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-2">Train Window (Days)</label>
                <input
                  type="number"
                  value={params.train_window}
                  onChange={(e) => setParams({ ...params, train_window: parseInt(e.target.value) })}
                  className="w-full bg-slate-950/80 border border-slate-800/80 rounded-lg px-3 py-2 text-sm font-mono text-white focus:outline-none focus:border-violet-500/50 focus:bg-slate-950 transition-all"
                />
              </div>

              <div>
                <label className="block text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-2">Test Window (Days)</label>
                <input
                  type="number"
                  value={params.test_window}
                  onChange={(e) => setParams({ ...params, test_window: parseInt(e.target.value) })}
                  className="w-full bg-slate-950/80 border border-slate-800/80 rounded-lg px-3 py-2 text-sm font-mono text-white focus:outline-none focus:border-violet-500/50 focus:bg-slate-950 transition-all"
                />
              </div>

              <button
                onClick={handleRunSimulation}
                disabled={loading}
                className="w-full bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-violet-500/20 uppercase text-[10px] tracking-widest"
              >
                {loading ? (
                  <><Loader2 className="animate-spin" size={16} /> Running...</>
                ) : (
                  <><Play size={14} fill="currentColor" /> Run Simulation</>
                )}
              </button>
            </div>
          </div>
        </aside>

        {/* Results Panel */}
        <section className="lg:col-span-9 space-y-5">
          <div className="bg-slate-900/40 p-5 rounded-2xl border border-slate-800/60 backdrop-blur-sm min-h-[500px] flex flex-col">
            <div className="flex items-center justify-between mb-5 pb-3 border-b border-slate-800/60">
              <h2 className="text-sm font-bold flex items-center gap-2.5 text-white uppercase tracking-tight">
                <BarChart2 className="text-violet-400" size={16} />
                Simulation Output
              </h2>
              {result && (
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-md flex items-center gap-1.5 uppercase tracking-widest font-bold">
                  <CheckCircle2 size={10} /> Complete
                </span>
              )}
            </div>

            <div className="flex-grow flex flex-col">
              {!result && !loading && (
                <div className="flex-grow flex flex-col items-center justify-center text-slate-500 gap-4">
                  <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/60">
                    <FlaskConical size={40} className="text-slate-700" />
                  </div>
                  <div className="text-center">
                    <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">Configure parameters and initiate test</p>
                    <p className="text-[9px] text-slate-700 font-mono mt-1">Results will appear here after simulation completes</p>
                  </div>
                </div>
              )}

              {loading && (
                <div className="flex-grow flex flex-col items-center justify-center gap-6">
                  <div className="relative">
                    <div className="w-20 h-20 rounded-full border-t-2 border-violet-500 animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Loader2 className="animate-spin text-violet-400" size={28} />
                    </div>
                  </div>
                  <div className="text-center space-y-1">
                    <p className="font-mono text-[10px] text-violet-400 uppercase tracking-widest animate-pulse">Running Neural Backtest...</p>
                    <p className="text-[9px] text-slate-600 font-mono">Isolating test database environment...</p>
                  </div>
                </div>
              )}

              {result && (
                <div className="space-y-5 animate-fade-in-up">
                  {/* Metrics row */}
                  <div className="grid grid-cols-3 gap-4">
                    <MetricCard
                      label="Total ROI"
                      value={`${result.metrics.roi_total}%`}
                      color={result.metrics.roi_total >= 0 ? 'border-emerald-500/20 text-emerald-400' : 'border-rose-500/20 text-rose-400'}
                      icon={TrendingUp}
                      prefix={result.metrics.roi_total >= 0 ? '+' : ''}
                    />
                    <MetricCard
                      label="Max Drawdown"
                      value={`${result.metrics.max_drawdown}%`}
                      color="border-rose-500/20 text-rose-400"
                      icon={AlertTriangle}
                      prefix="-"
                    />
                    <MetricCard
                      label="Win Rate"
                      value={`${result.metrics.win_rate}%`}
                      color="border-cyan-500/20 text-cyan-400"
                      icon={CheckCircle2}
                    />
                  </div>

                  {/* Equity Chart */}
                  <div className="h-[320px] w-full bg-slate-950/60 rounded-xl border border-slate-800/60 p-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={result.equity_curve}>
                        <defs>
                          <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis
                          dataKey="date"
                          stroke="#334155"
                          fontSize={9}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, { day: '2-digit', month: 'short' })}
                        />
                        <YAxis
                          stroke="#334155"
                          fontSize={9}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(val) => `$${val}`}
                        />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '11px' }}
                          itemStyle={{ color: '#8b5cf6', fontWeight: 'bold' }}
                          labelStyle={{ color: '#64748b', marginBottom: '4px', fontSize: '9px' }}
                        />
                        <Area
                          type="monotone"
                          dataKey="equity"
                          stroke="#8b5cf6"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#colorEquity)"
                          animationDuration={1500}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Protocol note */}
          <div className="flex items-start gap-4 p-5 bg-violet-500/5 border border-violet-500/10 rounded-2xl">
            <div className="bg-violet-500/10 p-2 rounded-lg text-violet-400 flex-shrink-0">
              <AlertTriangle size={16} />
            </div>
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-tight mb-1">Sandbox Environment Protocol</h3>
              <p className="text-[10px] text-slate-400 leading-relaxed font-mono">
                This simulation uses isolated historical data. Predictions and executions in this module do not affect live market positions. Always validate results across multiple time windows before deploying to the execution layer.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
