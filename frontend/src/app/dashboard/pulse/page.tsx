'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import {
  Activity,
  Trash2,
  Pause,
  Play,
  Terminal as TerminalIcon,
  Radio
} from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function SystemPulsePage() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const logBuffer = useRef<string[]>([]);
  const animationFrameId = useRef<number | null>(null);

  const writeLogToTerminal = useCallback((message: string) => {
    if (!xtermRef.current) return;
    let coloredMsg = message;
    if (message.includes('ERROR')) {
      coloredMsg = `\x1b[31m${message}\x1b[0m`;
    } else if (message.includes('WARNING') || message.includes('WARN')) {
      coloredMsg = `\x1b[33m${message}\x1b[0m`;
    } else if (message.includes('SUCCESS') || message.includes('OK') || message.includes('CONNECTED')) {
      coloredMsg = `\x1b[32m${message}\x1b[0m`;
    } else if (message.includes('INFO')) {
      coloredMsg = `\x1b[37m${message}\x1b[0m`;
    }
    xtermRef.current.writeln(coloredMsg);
  }, []);

  const { isConnected } = useWebSocket('/api/ws/pulse', {
    onMessage: (msg) => {
      if (typeof msg === 'string') {
        logBuffer.current.push(msg);
      }
    }
  });

  useEffect(() => {
    if (!terminalRef.current || xtermRef.current) return;

    const term = new XTerm({
      theme: {
        background: '#020617',
        foreground: '#94a3b8',
        cursor: '#06b6d4',
        black: '#020617',
        red: '#f43f5e',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#d946ef',
        cyan: '#06b6d4',
        white: '#f1f5f9',
      },
      fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, "Courier New", monospace',
      fontSize: 12,
      lineHeight: 1.4,
      scrollback: 5000,
      cursorBlink: true,
      disableStdin: true,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    const fetchLogs = async () => {
      try {
        const response = await fetch('/api/system/logs');
        if (!response.ok) throw new Error('Proxy logs fetch failed');
        const logs = await response.json();
        if (Array.isArray(logs)) {
          logs.forEach((log: string) => writeLogToTerminal(log));
        }
      } catch (e) {
        console.warn('Backend logs offline or Proxy error.', e);
        writeLogToTerminal('ERROR: Could not fetch initial logs from backend persistency via Proxy.');
      }
    };
    fetchLogs();

    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
      xtermRef.current = null;
    };
  }, [writeLogToTerminal]);

  useEffect(() => {
    const processBuffer = () => {
      if (logBuffer.current.length > 0 && xtermRef.current) {
        const batch = logBuffer.current.splice(0, 100);
        batch.forEach(msg => writeLogToTerminal(msg));
      }
      animationFrameId.current = requestAnimationFrame(processBuffer);
    };
    animationFrameId.current = requestAnimationFrame(processBuffer);
    return () => {
      if (animationFrameId.current) cancelAnimationFrame(animationFrameId.current);
    };
  }, [writeLogToTerminal]);

  useEffect(() => {
    if (xtermRef.current) {
      // @ts-expect-error - xterm 5 does not have scrollOnData in public options type but it works in some versions or via private.
    }
  }, [isPaused]);

  const clearTerminal = () => xtermRef.current?.clear();

  return (
    <div className="text-slate-200 font-sans max-w-screen-2xl mx-auto">
      <header className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <h1 className="text-2xl font-black tracking-tighter text-white uppercase flex items-center gap-2.5">
              <Activity size={22} className="text-emerald-400" />
              System Pulse
              <span className="text-xs font-mono text-emerald-600 font-normal normal-case tracking-normal bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                <Radio size={9} className={isConnected ? 'text-emerald-400 animate-pulse' : 'text-slate-600'} />
                LIVE
              </span>
            </h1>
          </div>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest pl-4">
            Real-time Observation & Audit Console
          </p>
        </div>

        <div className="flex gap-2.5">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg border font-mono text-[10px] uppercase tracking-widest transition-all ${
              isPaused
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/15'
                : 'bg-slate-900/80 border-slate-800/80 text-slate-400 hover:text-white hover:border-slate-700'
            }`}
          >
            {isPaused ? <Play size={13} /> : <Pause size={13} />}
            {isPaused ? 'Resume' : 'Pause'}
          </button>

          <button
            onClick={clearTerminal}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-800/80 bg-slate-900/80 text-slate-400 hover:text-white hover:border-slate-700 font-mono text-[10px] uppercase tracking-widest transition-all"
          >
            <Trash2 size={13} />
            Clear
          </button>
        </div>
      </header>

      <main className="flex flex-col h-[calc(100vh-220px)]">
        <div className="flex-grow bg-slate-900/40 rounded-2xl border border-slate-800/60 backdrop-blur-sm shadow-inner p-4 flex flex-col overflow-hidden">
          {/* Terminal toolbar */}
          <div className="flex items-center justify-between mb-3 px-1">
            <div className="flex items-center gap-2">
              <TerminalIcon size={13} className="text-slate-600" />
              <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">CONSOLE_BUFFER_POOL</span>
            </div>
            <div className="flex items-center gap-3">
              {/* Log level legend */}
              <div className="hidden sm:flex items-center gap-3">
                {[
                  { color: 'bg-emerald-500', label: 'Info' },
                  { color: 'bg-amber-500', label: 'Warn' },
                  { color: 'bg-rose-500', label: 'Error' },
                ].map(({ color, label }) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${color}`} />
                    <span className="text-[9px] text-slate-600 font-mono uppercase">{label}</span>
                  </div>
                ))}
              </div>

              <div className="w-px h-3 bg-slate-800" />

              <div className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[9px] font-mono uppercase tracking-widest ${
                isConnected
                  ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400'
                  : 'bg-rose-500/5 border-rose-500/20 text-rose-400'
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
                WS_{isConnected ? 'CONNECTED' : 'DISCONNECTED'}
              </div>
            </div>
          </div>

          <div
            ref={terminalRef}
            className="flex-grow rounded-xl overflow-hidden border border-slate-800/60 bg-[#020617]"
          />

          <div className="mt-3 flex justify-between items-center px-1">
            <p className="text-[9px] text-slate-700 font-mono italic">
              $ tail -f backend/logs/defisys.log
            </p>
            <span className="text-[9px] text-slate-600 font-mono uppercase tracking-widest">
              Scroll: {isPaused ? 'Locked' : 'Live'}
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
