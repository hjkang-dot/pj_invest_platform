import React from "react";
import { Terminal } from "lucide-react";

interface LiveLogsProps {
  logs?: string[];
}

export const LiveLogs: React.FC<LiveLogsProps> = ({ logs = [] }) => {
  const mockLogs = logs.length > 0 ? logs : [
    "[2026-06-22 21:00:00] [SYSTEM] Starting unified daily trading batch executor...",
    "[2026-06-22 21:00:01] [DB] Connecting to invest_platform.db...",
    "[2026-06-22 21:00:01] [COIN] Fetching 1d candles for BTC_USDT...",
    "[2026-06-22 21:00:02] [COIN] BTC_USDT: Close=$65,140, Signal=LONG (Vol Climax Rebound)",
    "[2026-06-22 21:00:02] [COIN] Executing mock BUY order for BTC_USDT (Qty: 0.15, Price: 65140.0)...",
    "[2026-06-22 21:00:02] [COIN] Order filled. Database updated.",
    "[2026-06-22 21:00:02] [STOCK] Running KRX Daily Price Sync Pipeline for 20260622...",
    "[2026-06-22 21:00:03] [STOCK] Sync skipped. Date 20260622 already synced in DB.",
    "[2026-06-22 21:00:03] [STOCK] Fetching DART company financials cache...",
    "[2026-06-22 21:00:03] [STOCK] Evaluating stock strategies on daily prices...",
    "[2026-06-22 21:00:04] [SYSTEM] Telegram report sent successfully.",
    "[2026-06-22 21:00:04] [SYSTEM] Unified trading batch finished successfully."
  ];

  return (
    <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300">
      <div className="flex items-center gap-2 mb-4">
        <Terminal size={20} className="text-cyan-400" />
        <h3 className="text-base font-semibold text-slate-200">배치 시스템 로그 콘솔</h3>
      </div>

      {/* Terminal Display */}
      <div className="bg-black/60 rounded-xl p-4 border border-slate-800/80 font-mono text-[10px] text-emerald-400 overflow-y-auto max-h-56 shadow-inner space-y-1.5 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
        {mockLogs.map((log, idx) => {
          let colorClass = "text-emerald-400";
          if (log.includes("[COIN]")) colorClass = "text-cyan-400";
          if (log.includes("[STOCK]")) colorClass = "text-amber-400";
          if (log.includes("Executing") || log.includes("filled")) colorClass = "text-fuchsia-400 font-bold";
          if (log.includes("[SYSTEM]")) colorClass = "text-purple-400";
          
          return (
            <div key={idx} className={`leading-relaxed break-all ${colorClass}`}>
              {log}
            </div>
          );
        })}
      </div>
    </div>
  );
};
