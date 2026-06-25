import React from "react";
import { 
  Activity, 
  Sparkles, 
  ArrowUpRight, 
  TrendingDown 
} from "lucide-react";

export const AssetMonitor: React.FC = () => {
  // Mock Multi-Asset Monitor Data
  const assetsData = [
    { name: "국내 주식 (KRX)", price: "2,650.20", change: "+0.45%", isUp: true, status: "안정적 상승세", signal: "NORMAL" },
    { name: "가상자산 (Aden)", price: "$65,140.00", change: "-0.80%", isUp: false, status: "단기 횡보세", signal: "NORMAL" },
    { name: "해외선물 (Nasdaq)", price: "19,850.50", change: "+1.20%", isUp: true, status: "강한 매수세", signal: "NORMAL" },
    { name: "금 (Gold Spot)", price: "$2,310.50", change: "-6.40%", isUp: false, status: "단기 낙폭 과대", signal: "OPPORTUNITY", signalMsg: "매수 기회 포착" },
    { name: "원/달러 환율", price: "1,385.40", change: "+0.15%", isUp: true, status: "고점 박스권", signal: "NORMAL" }
  ];

  return (
    <section className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
      <div className="flex items-center gap-2 mb-6">
        <Activity size={18} className="text-cyan-400" />
        <h2 className="text-base font-bold text-slate-200">글로벌 다중 자산 실시간 모니터링</h2>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {assetsData.map((asset, idx) => (
          <div 
            key={idx}
            className={`p-4 rounded-xl border transition-all duration-300 ${
              asset.signal === "OPPORTUNITY" 
                ? "bg-cyan-950/20 border-cyan-500/50 shadow-md shadow-cyan-500/5 animate-pulse" 
                : "bg-slate-950/40 border-slate-900 hover:border-slate-800"
            }`}
          >
            <div className="flex justify-between items-start">
              <span className="text-[11px] text-slate-400 font-semibold">{asset.name}</span>
              {asset.signal === "OPPORTUNITY" && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-black bg-cyan-400 text-slate-950 uppercase tracking-wide">
                  <Sparkles size={8} /> OPPORTUNITY
                </span>
              )}
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-lg font-black text-slate-100 font-mono">{asset.price}</span>
              <span className={`text-[10px] font-bold font-mono flex items-center ${asset.isUp ? "text-emerald-400" : "text-rose-400"}`}>
                {asset.isUp ? <ArrowUpRight size={10} /> : <TrendingDown size={10} />}
                {asset.change}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${
                asset.signal === "OPPORTUNITY" ? "bg-cyan-400" : asset.isUp ? "bg-emerald-500" : "bg-rose-500"
              }`}></span>
              <span className={`text-[10px] font-semibold ${
                asset.signal === "OPPORTUNITY" ? "text-cyan-400" : "text-slate-500"
                }`}>
                {asset.signal === "OPPORTUNITY" ? asset.signalMsg : asset.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
