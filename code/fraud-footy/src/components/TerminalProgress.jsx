import React, { useEffect, useRef } from 'react';

/**
 * Retro Terminal Progress & Log Feed Component.
 * Displays ASCII progress bar (0% - 100%) and scrolling terminal logs.
 */
export default function TerminalProgress({ percent = 0, currentMessage = '', logs = [], onCancel }) {
  const terminalEndRef = useRef(null);

  // Auto-scroll to bottom of terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Generate retro ASCII progress bar [██████░░░░]
  const renderAsciiBar = (pct) => {
    const totalBlocks = 28;
    const filledBlocks = Math.round((pct / 100) * totalBlocks);
    const emptyBlocks = Math.max(0, totalBlocks - filledBlocks);
    const filled = '█'.repeat(Math.min(totalBlocks, filledBlocks));
    const empty = '░'.repeat(emptyBlocks);
    return `[${filled}${empty}] ${pct}%`;
  };

  return (
    <div className="w-full max-w-3xl mx-auto bg-[#07090e] border-2 border-[#24ff00]/60 p-4 font-mono shadow-[0_0_25px_rgba(36,255,0,0.2)] rounded-sm">
      {/* Terminal Title Bar */}
      <div className="flex items-center justify-between border-b border-[#24ff00]/30 pb-2 mb-3 text-xs text-[#24ff00]">
        <div className="flex items-center gap-2 font-pixel text-[10px]">
          <span className="inline-block w-2.5 h-2.5 bg-[#24ff00] animate-ping" />
          <span>FRAUD-NET RECON // ACTIVE ENGINE</span>
        </div>
        {onCancel && (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-red-400 border border-gray-700 px-2 py-0.5 text-[10px] uppercase font-mono"
          >
            [ABORT]
          </button>
        )}
      </div>

      {/* Progress Bar & Current Status */}
      <div className="mb-4 bg-black/80 border border-[#24ff00]/40 p-3">
        <div className="flex justify-between items-center text-xs text-[#39ff14] mb-1 font-mono">
          <span className="truncate max-w-[80%] font-bold">{currentMessage || 'Connecting to telemetric feed...'}</span>
          <span className="font-pixel text-[11px]">{percent}%</span>
        </div>
        <pre className="text-yellow-400 text-xs sm:text-sm font-bold tracking-wider overflow-x-hidden select-none">
          {renderAsciiBar(percent)}
        </pre>
      </div>

      {/* Scrolling Terminal Log Stream */}
      <div className="h-44 sm:h-52 overflow-y-auto bg-black p-3 border border-gray-800 text-[11px] sm:text-xs font-mono space-y-1 text-green-400/90 select-text">
        {logs.length === 0 ? (
          <div className="text-gray-500 italic">Initializing telemetry stream...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-gray-500 select-none">&gt;&gt;</span>
              <span className="leading-tight">{log}</span>
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
      </div>

      <div className="mt-2 text-[10px] text-gray-500 flex items-center justify-between font-mono">
        <span>SOFASCORE PROTOCOL V1.9 // BAYESIAN SHRINKAGE ENGINE</span>
        <span className="animate-pulse text-green-400">● STREAMING ACTIVE</span>
      </div>
    </div>
  );
}
