'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  FlaskConical,
  Terminal,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Shield,
  Zap,
} from 'lucide-react';

const NAV_ITEMS = [
  {
    label: 'War Room',
    href: '/dashboard',
    icon: Activity,
    accent: 'cyan',
    description: 'Market Intelligence',
  },
  {
    label: 'Sandbox Lab',
    href: '/dashboard/sandbox',
    icon: FlaskConical,
    accent: 'violet',
    description: 'Strategy Backtesting',
  },
  {
    label: 'System Pulse',
    href: '/dashboard/pulse',
    icon: Terminal,
    accent: 'emerald',
    description: 'Audit Console',
  },
];

const ACCENT_CLASSES: Record<string, { active: string; hover: string; icon: string; dot: string; border: string }> = {
  cyan: {
    active: 'bg-cyan-500/10 text-cyan-300',
    hover: 'hover:bg-cyan-500/5 hover:text-cyan-400',
    icon: 'text-cyan-400',
    dot: 'bg-cyan-500',
    border: 'border-cyan-500/40',
  },
  violet: {
    active: 'bg-violet-500/10 text-violet-300',
    hover: 'hover:bg-violet-500/5 hover:text-violet-400',
    icon: 'text-violet-400',
    dot: 'bg-violet-500',
    border: 'border-violet-500/40',
  },
  emerald: {
    active: 'bg-emerald-500/10 text-emerald-300',
    hover: 'hover:bg-emerald-500/5 hover:text-emerald-400',
    icon: 'text-emerald-400',
    dot: 'bg-emerald-500',
    border: 'border-emerald-500/40',
  },
};

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={`relative flex flex-col shrink-0 border-r border-slate-800/60 bg-slate-950 transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-56'
      }`}
      style={{ minHeight: '100vh' }}
    >
      {/* Background grid */}
      <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />

      {/* Logo */}
      <div className={`relative flex items-center gap-3 px-4 py-5 border-b border-slate-800/60 ${collapsed ? 'justify-center' : ''}`}>
        <div className="relative flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Cpu size={16} className="text-white" />
          </div>
          <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-slate-950 animate-pulse-dot" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="text-xs font-black text-white uppercase tracking-widest leading-none">DefiSys</p>
            <p className="text-[9px] text-slate-500 font-mono uppercase tracking-widest mt-0.5">v3.0 Control</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="relative flex-1 flex flex-col gap-1 px-2 py-4">
        {!collapsed && (
          <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest px-2 mb-2">Modules</p>
        )}

        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          const acc = ACCENT_CLASSES[item.accent];

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative group flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-medium ${
                active
                  ? `${acc.active} ${acc.border} border`
                  : `text-slate-400 ${acc.hover} border border-transparent`
              } ${collapsed ? 'justify-center' : ''}`}
              title={collapsed ? item.label : undefined}
            >
              {active && (
                <div className={`absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 ${acc.dot} rounded-r shadow-lg`} />
              )}
              <Icon
                size={17}
                className={`flex-shrink-0 transition-colors ${active ? acc.icon : 'text-slate-500 group-hover:text-slate-300'}`}
              />
              {!collapsed && (
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold uppercase tracking-wide leading-none">{item.label}</p>
                  <p className={`text-[9px] font-mono mt-0.5 leading-none ${active ? 'opacity-70' : 'text-slate-600'}`}>
                    {item.description}
                  </p>
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom system info */}
      {!collapsed && (
        <div className="relative px-3 py-4 border-t border-slate-800/60">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-slate-900/50">
              <Shield size={11} className="text-emerald-500 flex-shrink-0" />
              <span className="text-[9px] font-mono text-slate-400 uppercase tracking-widest">Protocol Secure</span>
            </div>
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-slate-900/50">
              <Zap size={11} className="text-amber-400 flex-shrink-0" />
              <span className="text-[9px] font-mono text-slate-400 uppercase tracking-widest">XGBoost Active</span>
            </div>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="relative flex items-center justify-center py-3 border-t border-slate-800/60 text-slate-600 hover:text-slate-300 transition-colors w-full"
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  );
}
