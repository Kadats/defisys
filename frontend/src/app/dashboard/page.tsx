'use client';

import { Activity, LayoutDashboard, ShieldAlert } from 'lucide-react';
import IndicatorWidget from '@/components/IndicatorWidget';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function DashboardPage() {
  const { isConnected } = useWebSocket('/api/ws/ticker');

  return (
    <div className="text-slate-200 font-sans">
      <header className="flex items-center justify-between mb-10 border-b border-slate-800 pb-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-black flex items-center gap-3 tracking-tighter text-white uppercase">
            <Activity className={`text-emerald-500 ${isConnected ? 'animate-pulse' : 'opacity-20'}`} />
            War Room <span className="text-slate-500">v3.0</span>
          </h1>
          <p className="text-xs font-mono text-slate-500 uppercase tracking-widest">DefiSys Institutional Control Center</p>
        </div>
        
        <div className="flex gap-4">
          <div className="bg-slate-900 px-4 py-2 rounded-lg border border-slate-800 flex items-center gap-3 shadow-2xl">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]'}`} />
            <span className={`text-xs font-mono font-bold uppercase tracking-widest ${isConnected ? 'text-emerald-400' : 'text-rose-400'}`}>
              System {isConnected ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Real-time Indicators Section */}
        <section className="lg:col-span-8 bg-slate-900/40 p-8 rounded-2xl border border-slate-800/50 backdrop-blur-sm shadow-inner">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold flex items-center gap-3 text-white uppercase tracking-tight">
              <LayoutDashboard className="text-sky-400" size={20} />
              Market Intelligence
            </h2>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded">LIVE FEED</span>
          </div>
          
          <IndicatorWidget />
          
          {/* Main Visual Placeholder (e.g. Chart area) */}
          <div className="mt-8 aspect-video rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-center group overflow-hidden relative">
             <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.05)_0%,transparent_70%)]" />
             <div className="flex flex-col items-center gap-4 relative z-10">
                <div className="w-16 h-16 rounded-full border border-slate-800 flex items-center justify-center bg-slate-900 group-hover:scale-110 transition-transform duration-500">
                   <Activity size={32} className="text-slate-600" />
                </div>
                <span className="text-slate-500 font-mono text-xs uppercase tracking-widest animate-pulse">Initializing Neural Engine...</span>
             </div>
          </div>
        </section>

        {/* Risk Management Section */}
        <aside className="lg:col-span-4 flex flex-col gap-6">
          <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold flex items-center gap-3 text-white uppercase tracking-tight">
                <ShieldAlert className="text-rose-500" size={18} />
                Risk Protocol
              </h2>
              <span className="text-[10px] font-mono text-emerald-400 font-bold">SECURE</span>
            </div>
            
            <div className="space-y-6">
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-slate-400 font-mono uppercase tracking-widest">Capital Safety</span>
                  <span className="text-emerald-400 font-bold">94%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 w-[94%] shadow-[0_0_10px_rgba(16,185,129,0.3)]"></div>
                </div>
              </div>
              
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <p className="text-[11px] text-slate-500 font-mono uppercase mb-2">Institutional Status</p>
                <p className="text-xs text-slate-300 leading-relaxed">
                  All liquidity buffers are operational. Aave health factor is within nominal parameters ({'>'}1.5).
                </p>
              </div>
            </div>
          </div>

          {/* Terminal Console */}
          <div className="bg-black/80 p-6 rounded-2xl border border-slate-800 shadow-2xl flex-grow font-mono">
            <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
               <div className="w-2 h-2 rounded-full bg-rose-500/50" />
               <div className="w-2 h-2 rounded-full bg-amber-500/50" />
               <div className="w-2 h-2 rounded-full bg-emerald-500/50" />
               <span className="text-[10px] text-slate-600 ml-2">SYSTEM_CONSOLE v3.0</span>
            </div>
            <div className="text-emerald-500/80 text-[11px] space-y-1">
               <p>$ DefiSys v3.0 booting...</p>
               <p>$ [OK] Multi-RPC failover ready.</p>
               <p>$ [OK] Market synchronizer active.</p>
               <p>$ [OK] XGBoost prediction engine idle.</p>
               <p>$ <span className="animate-pulse">_</span></p>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
