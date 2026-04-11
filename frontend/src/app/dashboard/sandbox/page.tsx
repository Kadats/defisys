'use client';

import React, { useState } from 'react';
import { 
  FlaskConical, 
  Play, 
  Settings2, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2
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
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });
      if (!response.ok) throw new Error('Sandbox Proxy failed');
      const data = await response.json();
      if (data.success) {
        setResult(data);
      }
    } catch (error) {
      console.warn('Simulation failed via Proxy.', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-slate-200 font-sans">
      <header className="flex items-center justify-between mb-10 border-b border-slate-800 pb-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-black flex items-center gap-3 tracking-tighter text-white uppercase">
            <FlaskConical className="text-sky-400" />
            Sandbox Lab <span className="text-slate-500">BETA</span>
          </h1>
          <p className="text-xs font-mono text-slate-500 uppercase tracking-widest">Historical Backtesting & Strategy Lab</p>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Parameters Form Panel */}
        <aside className="lg:col-span-3">
          <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800 shadow-xl sticky top-24">
            <div className="flex items-center gap-2 mb-6">
              <Settings2 size={18} className="text-sky-400" />
              <h2 className="text-lg font-bold text-white uppercase tracking-tight">Configuration</h2>
            </div>

            <div className="space-y-6">
              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-2 tracking-widest">Confidence Threshold ({params.ai_confidence})</label>
                <input 
                  type="range" 
                  min="0.5" 
                  max="0.95" 
                  step="0.05"
                  value={params.ai_confidence}
                  onChange={(e) => setParams({...params, ai_confidence: parseFloat(e.target.value)})}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-2 tracking-widest">Initial Capital ($)</label>
                <input 
                  type="number" 
                  value={params.initial_capital}
                  onChange={(e) => setParams({...params, initial_capital: parseInt(e.target.value)})}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-sm font-mono text-white focus:outline-none focus:border-sky-500/50"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-2 tracking-widest">Train Window (Days)</label>
                <input 
                  type="number" 
                  value={params.train_window}
                  onChange={(e) => setParams({...params, train_window: parseInt(e.target.value)})}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-sm font-mono text-white focus:outline-none focus:border-sky-500/50"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-2 tracking-widest">Test Window (Days)</label>
                <input 
                  type="number" 
                  value={params.test_window}
                  onChange={(e) => setParams({...params, test_window: parseInt(e.target.value)})}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-sm font-mono text-white focus:outline-none focus:border-sky-500/50"
                />
              </div>

              <button 
                onClick={handleRunSimulation}
                disabled={loading}
                className="w-full bg-sky-500 hover:bg-sky-600 disabled:bg-slate-800 disabled:text-slate-500 text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-sky-500/20 uppercase text-xs tracking-widest"
              >
                {loading ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <Play size={18} fill="currentColor" />
                )}
                Run Simulation
              </button>
            </div>
          </div>
        </aside>

        {/* Results Panel */}
        <section className="lg:col-span-9 space-y-8">
          <div className="bg-slate-900/40 p-8 rounded-2xl border border-slate-800/50 backdrop-blur-sm shadow-inner min-h-[500px] flex flex-col">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-xl font-bold flex items-center gap-3 text-white uppercase tracking-tight">
                <TrendingUp className="text-emerald-500" size={20} />
                Simulation Output
              </h2>
              {result && (
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 flex items-center gap-1">
                  <CheckCircle2 size={10} /> COMPLETE
                </span>
              )}
            </div>

            <div className="flex-grow flex flex-col">
              {!result && !loading && (
                <div className="flex-grow flex flex-col items-center justify-center text-slate-500 gap-4 opacity-50">
                  <div className="p-6 rounded-full bg-slate-800/50 border border-slate-700">
                    <FlaskConical size={48} />
                  </div>
                  <p className="font-mono text-xs uppercase tracking-widest">Configure parameters and initiate test</p>
                </div>
              )}

              {loading && (
                <div className="flex-grow flex flex-col items-center justify-center gap-6">
                  <div className="relative">
                    <div className="w-24 h-24 rounded-full border-t-2 border-sky-500 animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Loader2 className="animate-spin text-sky-400" size={32} />
                    </div>
                  </div>
                  <div className="flex flex-col items-center gap-2">
                    <p className="font-mono text-xs text-sky-400 uppercase tracking-widest animate-pulse">Running Neural Backtest...</p>
                    <p className="text-[10px] text-slate-500 font-mono italic">Isolating test database environment...</p>
                  </div>
                </div>
              )}

              {result && (
                <div className="space-y-8 animate-in fade-in duration-700">
                  {/* Equity Chart */}
                  <div className="h-[350px] w-full bg-slate-950/50 rounded-xl border border-slate-800 p-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={result.equity_curve}>
                        <defs>
                          <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis 
                          dataKey="date" 
                          stroke="#475569" 
                          fontSize={10} 
                          tickLine={false} 
                          axisLine={false}
                          tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, { day: '2-digit', month: 'short' })}
                        />
                        <YAxis 
                          stroke="#475569" 
                          fontSize={10} 
                          tickLine={false} 
                          axisLine={false}
                          tickFormatter={(val) => `$${val}`}
                        />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '8px' }}
                          itemStyle={{ color: '#0ea5e9', fontSize: '12px', fontWeight: 'bold' }}
                          labelStyle={{ color: '#94a3b8', fontSize: '10px', marginBottom: '4px' }}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="equity" 
                          stroke="#0ea5e9" 
                          strokeWidth={2}
                          fillOpacity={1} 
                          fill="url(#colorEquity)" 
                          animationDuration={1500}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Metrics Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-slate-950 border border-slate-800 p-6 rounded-xl relative overflow-hidden group">
                      <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                        <TrendingUp size={48} />
                      </div>
                      <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-1">Total ROI</p>
                      <p className={`text-2xl font-black ${result.metrics.roi_total >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {result.metrics.roi_total >= 0 ? '+' : ''}{result.metrics.roi_total}%
                      </p>
                    </div>

                    <div className="bg-slate-950 border border-slate-800 p-6 rounded-xl relative overflow-hidden group">
                      <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                        <AlertTriangle size={48} />
                      </div>
                      <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-1">Max Drawdown</p>
                      <p className="text-2xl font-black text-rose-500">
                        -{result.metrics.max_drawdown}%
                      </p>
                    </div>

                    <div className="bg-slate-950 border border-slate-800 p-6 rounded-xl relative overflow-hidden group">
                      <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                        <CheckCircle2 size={48} />
                      </div>
                      <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-1">Win Rate</p>
                      <p className="text-2xl font-black text-white">
                        {result.metrics.win_rate}%
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Institutional Note */}
          <div className="flex items-start gap-4 p-6 bg-sky-500/5 border border-sky-500/10 rounded-2xl">
            <div className="bg-sky-500/10 p-2 rounded-lg text-sky-400">
              <AlertTriangle size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-tight mb-1">Sandbox Environment Protocol</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                This simulation uses isolated historical data. Predictions and executions in this module do not affect live market positions. Always validate results across multiple time windows before deploying to the execution layer.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
