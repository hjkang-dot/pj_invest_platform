import React from "react";
import { Bell, Activity } from "lucide-react";

interface SignalItem {
  id: string;
  time: string;
  asset: string;
  strategy: string;
  signalType: "LONG" | "SHORT" | "EXIT";
  price: string;
  reason: string;
}

interface StrategyStatus {
  name: string;
  type: "COIN" | "STOCK";
  status: "ACTIVE" | "SLEEP" | "ERROR";
  lastRun: string;
}

interface SignalAlertsProps {
  signals?: SignalItem[];
  strategies?: StrategyStatus[];
}

export const SignalAlerts: React.FC<SignalAlertsProps> = ({
  signals = [],
  strategies = [],
}) => {
  const displayStrategies = strategies;
  const displaySignals = signals;

  const getStatusColor = (status: "ACTIVE" | "SLEEP" | "ERROR") => {
    switch (status) {
      case "ACTIVE":
        return "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
      case "SLEEP":
        return "bg-amber-500/20 text-amber-400 border border-amber-500/30";
      case "ERROR":
        return "bg-rose-500/20 text-rose-400 border border-rose-500/30";
    }
  };

  const getSignalBadgeColor = (type: "LONG" | "SHORT" | "EXIT") => {
    switch (type) {
      case "LONG":
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      case "SHORT":
        return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      case "EXIT":
        return "bg-slate-700/30 text-slate-300 border border-slate-700/50";
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* 1. Strategy Operation Status */}
      <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300">
        <div className="flex items-center gap-2 mb-6">
          <Activity size={20} className="text-cyan-400" />
          <h3 className="text-base font-semibold text-slate-200">배치 및 분석 엔진 구동 현황</h3>
        </div>

        <div className="space-y-4">
          {displayStrategies.map((strat) => (
            <div key={strat.name} className="flex justify-between items-center p-3 bg-slate-950/40 border border-slate-850/50 rounded-xl hover:border-slate-800 transition">
              <div>
                <p className="text-xs font-bold text-slate-200">{strat.name}</p>
                <p className="text-[10px] text-slate-500 mt-0.5">최근 수행 시각: {strat.lastRun}</p>
              </div>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${getStatusColor(strat.status)}`}>
                {strat.status === "ACTIVE" ? "ACTIVE" : strat.status === "SLEEP" ? "STANDBY" : "ERROR"}
              </span>
            </div>
          ))}
          {displayStrategies.length === 0 && (
            <div className="text-slate-500 text-center py-4 text-xs font-medium">
              등록된 분석 엔진 구동 정보가 없습니다.
            </div>
          )}
        </div>
      </div>

      {/* 2. Today's Signal Alerts */}
      <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300">
        <div className="flex items-center gap-2 mb-6">
          <Bell size={20} className="text-cyan-400 animate-pulse" />
          <h3 className="text-base font-semibold text-slate-200">오늘 발생한 매매 시그널</h3>
        </div>

        {/* Timeline */}
        <div className="relative pl-6 border-l border-slate-800 space-y-6">
          {displaySignals.map((sig) => (
            <div key={sig.id} className="relative">
              {/* Timeline Bullet */}
              <span className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-slate-900 border-2 border-cyan-400"></span>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 font-mono">{sig.time}</span>
                  <span className="text-xs font-bold text-slate-200">{sig.asset}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${getSignalBadgeColor(sig.signalType)}`}>
                    {sig.signalType}
                  </span>
                </div>
                <span className="text-xs font-semibold text-slate-300 sm:text-right">{sig.price}</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                [{sig.strategy}] {sig.reason}
              </p>
            </div>
          ))}
          {displaySignals.length === 0 && (
            <div className="text-slate-500 text-center py-8 text-xs relative -left-6 font-medium">
              오늘 발생한 매매 신호가 없습니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
