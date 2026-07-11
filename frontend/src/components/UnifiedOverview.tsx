import React from "react";
import { Wallet, TrendingUp, ShieldAlert, Award } from "lucide-react";

interface OverviewProps {
  totalAsset: number;
  dailyReturn: number;
  dailyReturnPct: number;
  cumulativeReturnPct: number;
  mdd: number;
  stockWeight: number; // e.g. 45
  coinWeight: number;  // e.g. 35
  cashWeight: number;  // e.g. 20
  onClickTotalAsset?: () => void;
}

export const UnifiedOverview: React.FC<OverviewProps> = ({
  totalAsset = 154200000,
  dailyReturn = 2430000,
  dailyReturnPct = 1.6,
  cumulativeReturnPct = 24.8,
  mdd = -4.2,
  stockWeight = 45,
  coinWeight = 35,
  cashWeight = 20,
  onClickTotalAsset,
}) => {
  // SVG Donut calculation
  const radius = 50;
  const circumference = 2 * Math.PI * radius; // 314.16
  
  const stockOffset = 0;
  const coinOffset = (stockWeight / 100) * circumference;
  const cashOffset = ((stockWeight + coinWeight) / 100) * circumference;

  const stockDash = (stockWeight / 100) * circumference;
  const coinDash = (coinWeight / 100) * circumference;
  const cashDash = (cashWeight / 100) * circumference;

  const formatKRW = (val: number) => {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: "KRW",
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* 1. Indicators Cards Column */}
      <div className="xl:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Card 1: Total Asset */}
        <div 
          onClick={onClickTotalAsset}
          className="relative overflow-hidden bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 hover:bg-slate-900/60 active:scale-[0.99] transition duration-300 group cursor-pointer"
        >
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/10 rounded-full blur-2xl group-hover:bg-cyan-500/20 transition duration-500"></div>
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-xl">
              <Wallet size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">총 평가 자산</p>
              <h3 className="text-2xl font-bold text-slate-100 mt-1">{formatKRW(totalAsset)}</h3>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className={`flex items-center font-semibold ${dailyReturn >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {dailyReturn >= 0 ? "+" : ""}{formatKRW(dailyReturn)} ({dailyReturnPct >= 0 ? "+" : ""}{dailyReturnPct}%)
            </span>
            <span className="text-slate-500">전일 대비</span>
          </div>
        </div>

        {/* Card 2: Cumulative Return */}
        <div className="relative overflow-hidden bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300 group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl group-hover:bg-emerald-500/20 transition duration-500"></div>
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl">
              <TrendingUp size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">누적 수익률</p>
              <h3 className="text-2xl font-bold text-slate-100 mt-1">{cumulativeReturnPct}%</h3>
            </div>
          </div>
          <div className="text-sm text-slate-400 flex gap-2">
            <span className="text-emerald-400 font-medium">연초 대비 최고 성과</span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-300">포트폴리오 누적</span>
          </div>
        </div>

        {/* Card 3: MDD */}
        <div className="relative overflow-hidden bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300 group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-rose-500/10 rounded-full blur-2xl group-hover:bg-rose-500/20 transition duration-500"></div>
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-rose-500/10 text-rose-400 rounded-xl">
              <ShieldAlert size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">최대 낙폭 (MDD)</p>
              <h3 className="text-2xl font-bold text-rose-400 mt-1">{mdd}%</h3>
            </div>
          </div>
          <div className="text-sm text-slate-400">
            <span className="text-slate-500">백테스트 대비 안정성:</span>{" "}
            <span className="text-emerald-400 font-semibold">매우 양호</span>
          </div>
        </div>

        {/* Card 4: Strategy Performance */}
        <div className="relative overflow-hidden bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300 group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/10 rounded-full blur-2xl group-hover:bg-amber-500/20 transition duration-500"></div>
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl">
              <Award size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">전략 가동 개수</p>
              <h3 className="text-2xl font-bold text-slate-100 mt-1">4 / 5 개</h3>
            </div>
          </div>
          <div className="text-sm text-slate-400">
            <span className="text-amber-400 font-medium">코인 2개, 주식 2개</span> 전략 활성 상태
          </div>
        </div>
      </div>

      {/* 2. Asset Allocation Donut Chart Column */}
      <div className="relative overflow-hidden bg-slate-900/40 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700 transition duration-300 flex flex-col items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-300 self-start">자산 포트폴리오 비중</h4>
        
        {/* SVG Donut */}
        <div className="relative w-40 h-40 flex items-center justify-center my-4">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
            {/* Stock circle */}
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="transparent"
              stroke="#10b981" // Emerald
              strokeWidth="10"
              strokeDasharray={`${stockDash} ${circumference}`}
              strokeDashoffset={-stockOffset}
              className="transition-all duration-1000 ease-out"
            />
            {/* Coin circle */}
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="transparent"
              stroke="#06b6d4" // Cyan
              strokeWidth="10"
              strokeDasharray={`${coinDash} ${circumference}`}
              strokeDashoffset={-coinOffset}
              className="transition-all duration-1000 ease-out"
            />
            {/* Cash circle */}
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="transparent"
              stroke="#f59e0b" // Amber
              strokeWidth="10"
              strokeDasharray={`${cashDash} ${circumference}`}
              strokeDashoffset={-cashOffset}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          {/* Inner Text */}
          <div className="absolute text-center">
            <p className="text-xs text-slate-400">보유 자산군</p>
            <p className="text-base font-bold text-slate-200">3개 부문</p>
          </div>
        </div>

        {/* Legend */}
        <div className="w-full flex justify-around text-xs mt-2">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span className="text-slate-400">주식 ({stockWeight}%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500"></span>
            <span className="text-slate-400">코인 ({coinWeight}%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span className="text-slate-400">예수금 ({cashWeight}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
