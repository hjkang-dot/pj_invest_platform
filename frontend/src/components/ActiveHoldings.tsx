import React, { useState } from "react";
import { ArrowUpRight, ArrowDownRight, Layers } from "lucide-react";

interface HoldingItem {
  id: string;
  code: string;
  name: string;
  type: "STOCK" | "COIN";
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  valuation: number;
  pnl: number;
  pnlPct: number;
  posType?: "LONG" | "SHORT"; // for coin
  score?: number; // for stock
}

interface ActiveHoldingsProps {
  holdings?: HoldingItem[];
}

export const ActiveHoldings: React.FC<ActiveHoldingsProps> = ({ holdings }) => {
  const [activeTab, setActiveTab] = useState<"ALL" | "STOCK" | "COIN">("ALL");

  // Mock holdings data if none provided
  const items = holdings !== undefined ? holdings : [
    { id: "1", code: "005930", name: "삼성전자", type: "STOCK", quantity: 150, entryPrice: 72000, currentPrice: 75200, valuation: 11280000, pnl: 480000, pnlPct: 4.4, score: 72 },
    { id: "2", code: "000660", name: "SK하이닉스", type: "STOCK", quantity: 60, entryPrice: 178000, currentPrice: 182500, valuation: 10950000, pnl: 270000, pnlPct: 2.5, score: 68 },
    { id: "3", code: "BTC_USDT", name: "Bitcoin", type: "COIN", quantity: 0.85, entryPrice: 63280, currentPrice: 65140, valuation: 55369, pnl: 1581, pnlPct: 2.9, posType: "LONG" },
    { id: "4", code: "ETH_USDT", name: "Ethereum", type: "COIN", quantity: 4.2, entryPrice: 3450, currentPrice: 3380, valuation: 14196, pnl: -294, pnlPct: -2.0, posType: "SHORT" },
    { id: "5", code: "035720", name: "카카오", type: "STOCK", quantity: 100, entryPrice: 48500, currentPrice: 47200, valuation: 4720000, pnl: -130000, pnlPct: -2.7, score: 58 },
  ] as HoldingItem[];

  const filteredItems = items.filter(item => {
    if (activeTab === "ALL") return true;
    return item.type === activeTab;
  });

  const formatPrice = (val: number, type: "STOCK" | "COIN") => {
    if (type === "COIN") {
      return `$${val.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;
    }
    return `${val.toLocaleString("ko-KR")} 원`;
  };

  const formatValuation = (val: number, type: "STOCK" | "COIN") => {
    if (type === "COIN") {
      // rough convert to KRW for valuation overview, or show USD
      return `${(val * 1350).toLocaleString("ko-KR")} 원 (~$${val.toLocaleString("en-US", { maximumFractionDigits: 0 })})`;
    }
    return `${val.toLocaleString("ko-KR")} 원`;
  };

  const formatPnL = (pnl: number, pct: number, type: "STOCK" | "COIN") => {
    const isPositive = pnl >= 0;
    const sign = isPositive ? "+" : "";
    const color = isPositive ? "text-emerald-400" : "text-rose-400";
    const Icon = isPositive ? ArrowUpRight : ArrowDownRight;

    if (type === "COIN") {
      return (
        <div className={`flex items-center gap-1 font-semibold ${color}`}>
          <Icon size={16} />
          <span>{sign}${pnl.toLocaleString("en-US", { maximumFractionDigits: 1 })} ({sign}{pct}%)</span>
        </div>
      );
    }
    return (
      <div className={`flex items-center gap-1 font-semibold ${color}`}>
        <Icon size={16} />
        <span>{sign}{pnl.toLocaleString("ko-KR")} 원 ({sign}{pct}%)</span>
      </div>
    );
  };

  return (
    <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Layers size={20} className="text-cyan-400" />
          <h3 className="text-base font-semibold text-slate-200">보유 자산 및 포지션 상세</h3>
        </div>

        {/* Tab Controls */}
        <div className="flex bg-slate-950/60 p-1 rounded-lg border border-slate-850">
          {(["ALL", "STOCK", "COIN"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-200 ${
                activeTab === tab
                  ? "bg-cyan-500/20 text-cyan-400 shadow-sm border border-cyan-500/30"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              {tab === "ALL" ? "전체 자산" : tab === "STOCK" ? "국내 주식" : "가상 자산(코인)"}
            </button>
          ))}
        </div>
      </div>

      {/* Holdings Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 font-semibold">
              <th className="py-3 px-4">종목명 / 자산</th>
              <th className="py-3 px-4">포지션 정보</th>
              <th className="py-3 px-4">평균 매입가</th>
              <th className="py-3 px-4">현재가</th>
              <th className="py-3 px-4 text-right">보유 수량</th>
              <th className="py-3 px-4 text-right">평가 금액</th>
              <th className="py-3 px-4 text-right">평가 손익 (수익률)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 text-slate-300 font-medium">
            {filteredItems.map(item => (
              <tr key={item.id} className="hover:bg-slate-800/10 transition">
                <td className="py-4 px-4">
                  <div>
                    <span className="font-semibold text-slate-100">{item.name}</span>
                    <span className="text-slate-500 ml-2">[{item.code}]</span>
                  </div>
                </td>
                <td className="py-4 px-4">
                  {item.type === "COIN" ? (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.posType === "LONG" 
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    }`}>
                      {item.posType}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      스코어 {item.score}점
                    </span>
                  )}
                </td>
                <td className="py-4 px-4">{formatPrice(item.entryPrice, item.type)}</td>
                <td className="py-4 px-4">{formatPrice(item.currentPrice, item.type)}</td>
                <td className="py-4 px-4 text-right font-mono">{item.quantity.toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
                <td className="py-4 px-4 text-right font-mono">{formatValuation(item.valuation, item.type)}</td>
                <td className="py-4 px-4 text-right">{formatPnL(item.pnl, item.pnlPct, item.type)}</td>
              </tr>
            ))}
            {filteredItems.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  해당 자산군에 보유 중인 포지션이 없습니다.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
