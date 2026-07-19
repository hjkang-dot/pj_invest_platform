import React from "react";
import { History, ArrowUpRight, ArrowDownRight } from "lucide-react";

interface TradeItem {
  id: string;
  time: string;
  strategy: string;
  asset: string;
  type: "BUY" | "SELL";
  price: number;
  quantity: number;
  pnl?: number;
  pnlPct?: number;
  isLive: boolean;
}

interface RecentTradesProps {
  trades?: TradeItem[];
}

export const RecentTrades: React.FC<RecentTradesProps> = ({ trades }) => {
  const displayTrades = trades || [];

  const formatPrice = (val: number, asset: string) => {
    if (asset.includes("_")) {
      return `$${val.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;
    }
    return `${val.toLocaleString("ko-KR")} 원`;
  };

  const formatPnL = (pnl?: number | null, pct?: number | null, asset: string = "") => {
    if (pnl == null) return <span className="text-slate-500">-</span>;
    const isPositive = pnl >= 0;
    const sign = isPositive ? "+" : "";
    const color = isPositive ? "text-emerald-400" : "text-rose-400";
    
    if (asset.includes("_")) {
      return <span className={`font-semibold ${color}`}>{sign}${pnl.toLocaleString("en-US")} ({sign}{pct}%)</span>;
    }
    return <span className={`font-semibold ${color}`}>{sign}{pnl.toLocaleString("ko-KR")} 원 ({sign}{pct}%)</span>;
  };

  return (
    <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300">
      <div className="flex items-center gap-2 mb-6">
        <History size={20} className="text-cyan-400" />
        <h3 className="text-base font-semibold text-slate-200">최근 5회 거래 이력</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 font-semibold">
              <th className="py-2.5 px-3">체결 시각</th>
              <th className="py-2.5 px-3">자산 종목</th>
              <th className="py-2.5 px-3">적용 전략</th>
              <th className="py-2.5 px-3">거래 구분</th>
              <th className="py-2.5 px-3">체결 단가</th>
              <th className="py-2.5 px-3 text-right">수량</th>
              <th className="py-2.5 px-3 text-right">실현 손익</th>
              <th className="py-2.5 px-3 text-center">방식</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 text-slate-300 font-medium">
            {displayTrades.length > 0 ? (
              displayTrades.map(trade => (
                <tr key={trade.id} className="hover:bg-slate-800/5 transition">
                  <td className="py-3 px-3 text-slate-500 font-mono">{trade.time}</td>
                  <td className="py-3 px-3 font-semibold text-slate-200">{trade.asset}</td>
                  <td className="py-3 px-3 text-slate-400">{trade.strategy}</td>
                  <td className="py-3 px-3">
                    <span className={`inline-flex items-center gap-0.5 font-bold ${
                      trade.type === "BUY" ? "text-emerald-400" : "text-rose-400"
                    }`}>
                      {trade.type === "BUY" ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                      {trade.type === "BUY" ? "매수" : "매도"}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono">{formatPrice(trade.price, trade.asset)}</td>
                  <td className="py-3 px-3 text-right font-mono">{trade.quantity.toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
                  <td className="py-3 px-3 text-right font-mono">{formatPnL(trade.pnl, trade.pnlPct, trade.asset)}</td>
                  <td className="py-3 px-3 text-center">
                    <span className={`inline-flex px-1.5 py-0.2 rounded text-[9px] font-bold ${
                      trade.isLive 
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                        : "bg-slate-700/20 text-slate-400 border border-slate-700/30"
                    }`}>
                      {trade.isLive ? "실거래" : "모의투자"}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500 text-xs font-semibold">
                  최근 체결된 거래 내역이 없습니다.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
