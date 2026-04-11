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
  Terminal as TerminalIcon 
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
    
    // Simple coloring based on log level
    let coloredMsg = message;
    if (message.includes('ERROR')) {
      coloredMsg = `\x1b[31m${message}\x1b[0m`; // Rose/Red
    } else if (message.includes('WARNING') || message.includes('WARN')) {
      coloredMsg = `\x1b[33m${message}\x1b[0m`; // Yellow
    } else if (message.includes('SUCCESS') || message.includes('OK') || message.includes('CONNECTED')) {
      coloredMsg = `\x1b[32m${message}\x1b[0m`; // Emerald/Green
    } else if (message.includes('INFO')) {
      coloredMsg = `\x1b[37m${message}\x1b[0m`; // White
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
        background: '#020617', // slate-950
        foreground: '#94a3b8', // slate-400
        cursor: '#10b981',     // emerald-500
        black: '#020617',
        red: '#f43f5e',        // rose-500
        green: '#10b981',      // emerald-500
        yellow: '#f59e0b',     // amber-500
        blue: '#3b82f6',
        magenta: '#d946ef',
        cyan: '#06b6d4',
        white: '#f1f5f9',
      },
      fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
      fontSize: 12,
      lineHeight: 1.2,
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

    // Load initial logs (Audit 3.3 Tail)
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

    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
      xtermRef.current = null;
    };
  }, [writeLogToTerminal]);

  // Buffer processing loop
  useEffect(() => {
    const processBuffer = () => {
      if (logBuffer.current.length > 0 && xtermRef.current) {
        // Process a batch of logs to prevent UI stutter during high volume
        const batchSize = 100;
        const batch = logBuffer.current.splice(0, batchSize);
        batch.forEach(msg => writeLogToTerminal(msg));
      }
      animationFrameId.current = requestAnimationFrame(processBuffer);
    };

    animationFrameId.current = requestAnimationFrame(processBuffer);
    
    return () => {
      if (animationFrameId.current) cancelAnimationFrame(animationFrameId.current);
    };
  }, [writeLogToTerminal]);

  // Update terminal options when isPaused changes
  useEffect(() => {
    if (xtermRef.current) {
      // @ts-expect-error - xterm 5 does not have scrollOnData in public options type but it works in some versions or via private.
    }
  }, [isPaused]);

  const clearTerminal = () => {
    xtermRef.current?.clear();
  };

  return (
    <div className="text-slate-200 font-sans">
      <header className="flex items-center justify-between mb-10 border-b border-slate-800 pb-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-black flex items-center gap-3 tracking-tighter text-white uppercase">
            <Activity className="text-sky-400" />
            System Pulse <span className="text-slate-500">LIVE</span>
          </h1>
          <p className="text-xs font-mono text-slate-500 uppercase tracking-widest">Real-time Observation & Audit Console</p>
        </div>

        <div className="flex gap-4">
          <button 
            onClick={() => setIsPaused(!isPaused)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border font-mono text-xs uppercase transition-all ${
              isPaused 
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-500' 
              : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            {isPaused ? <Play size={14} /> : <Pause size={14} />}
            {isPaused ? 'Resume Scroll' : 'Pause Scroll'}
          </button>
          
          <button 
            onClick={clearTerminal}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-white font-mono text-xs uppercase transition-all"
          >
            <Trash2 size={14} />
            Clear
          </button>
        </div>
      </header>

      <main className="flex flex-col h-[calc(100vh-280px)]">
        <div className="flex-grow bg-slate-900/40 rounded-2xl border border-slate-800/50 backdrop-blur-sm shadow-inner p-4 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between mb-4 px-2">
            <div className="flex items-center gap-2">
               <TerminalIcon size={16} className="text-slate-500" />
               <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">CONSOLE_BUFFER_POOL</span>
            </div>
            <div className={`flex items-center gap-2 px-2 py-1 rounded bg-black/40 border border-slate-800/50`}>
               <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500 animate-pulse'}`} />
               <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                 WS_{isConnected ? 'CONNECTED' : 'DISCONNECTED'}
               </span>
            </div>
          </div>
          
          <div 
            ref={terminalRef} 
            className="flex-grow rounded-xl overflow-hidden border border-slate-800 bg-[#020617] p-2"
          />
          
          <div className="mt-4 flex justify-between items-center px-2">
            <p className="text-[10px] text-slate-600 font-mono italic">
              $ tail -n 50 backend/logs/defisys.log
            </p>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="text-[10px] text-slate-600 font-mono uppercase">Info</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                <span className="text-[10px] text-slate-600 font-mono uppercase">Warn</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                <span className="text-[10px] text-slate-600 font-mono uppercase">Error</span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono ml-4 uppercase">Scroll: {isPaused ? 'Locked' : 'Live'}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
