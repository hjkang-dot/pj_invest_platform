import React from "react";
import { 
  AlertCircle, 
  ChevronRight, 
  Shield,
  Coins
} from "lucide-react";

export interface StrategyItem {
  id: string;
  name: string;
  type: "CORE" | "SATELLITE";
  targetAsset: string;
  allocation: number;
  backtestReturn: number;
  mdd: number;
  status: "ACTIVE" | "WAITING" | "SIGNAL";
  description: string;
  signalMessage?: string;
}

interface StrategyListProps {
  onSelectStrategy: (id: string) => void;
}

export const StrategyList: React.FC<StrategyListProps> = ({ onSelectStrategy }) => {
  // Mock Strategies Data
  const strategies: StrategyItem[] = [
    {
      id: "ud_dividend",
      name: "저평가 고배당 스크리닝 전략",
      type: "CORE",
      targetAsset: "국내 주식 (KRX)",
      allocation: 40,
      backtestReturn: 12.4,
      mdd: 6.2,
      status: "ACTIVE",
      description: "DART 공시 및 배당 히스토리를 분석하여 재무가 건전하고 배당 성향이 우수한 고배당 우량주를 선별하여 장기 투자합니다."
    },
    {
      id: "op_growth",
      name: "우량 기회 성장 스크리닝 전략",
      type: "CORE",
      targetAsset: "국내 주식 / 미국 테크",
      allocation: 30,
      backtestReturn: 24.8,
      mdd: 8.5,
      status: "ACTIVE",
      description: "높은 자기자본이익률(ROE)과 합리적인 가치 평가(PEG) 기준을 결합하여, 실적 개선세가 뚜렷한 우량 성장주를 선별합니다."
    },
    {
      id: "deep_value_contra",
      name: "낙폭과대 역발상 매수 전략",
      type: "SATELLITE",
      targetAsset: "금 선물 / 해외 원자재",
      allocation: 15,
      backtestReturn: 18.5,
      mdd: 12.4,
      status: "SIGNAL",
      description: "단기 매도세가 집중되어 밸류에이션 매력도가 한계치에 다다른 자산을 동적으로 매수하여 기술적 반등 수익을 추구합니다.",
      signalMessage: "금(Gold) 가격 낙폭 과대 매수 신호 활성화"
    },
    {
      id: "vol_climax",
      name: "거래량 클라이맥스 돌파 전략",
      type: "SATELLITE",
      targetAsset: "가상자산 (BTC, ETH)",
      allocation: 15,
      backtestReturn: 32.1,
      mdd: 18.2,
      status: "WAITING",
      description: "볼린저 밴드 하단 이탈 후 대량의 반등 거래량이 발생하는 시점에 진입하고, ATR 기준으로 손절/익절을 유동적으로 관리합니다."
    }
  ];

  const getStatusBadge = (status: StrategyItem["status"]) => {
    switch (status) {
      case "ACTIVE":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            운용중
          </span>
        );
      case "SIGNAL":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
            신호감지
          </span>
        );
      case "WAITING":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            시그널 대기
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-8">
      {/* Strategies Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Core Strategies (70% Allocation) */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-900 pb-3">
            <div className="flex items-center gap-2">
              <Shield size={20} className="text-emerald-400" />
              <h2 className="text-base font-bold text-slate-200">Core 전략 (안정형 우상향 &bull; 70% 비중)</h2>
            </div>
            <span className="text-xs text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              안정형 자산배분
            </span>
          </div>

          <div className="space-y-4">
            {strategies
              .filter(s => s.type === "CORE")
              .map(strategy => (
                <div 
                  key={strategy.id}
                  className="group relative overflow-hidden bg-slate-900/30 backdrop-blur-xl border border-slate-900 hover:border-slate-800 p-6 rounded-2xl transition-all duration-300 flex flex-col justify-between hover:shadow-xl hover:shadow-emerald-500/5 cursor-pointer"
                  onClick={() => onSelectStrategy(strategy.id)}
                >
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-[10px] text-slate-400 font-semibold bg-slate-950/60 px-2 py-0.5 rounded border border-slate-850">
                          {strategy.targetAsset}
                        </span>
                        <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/10">
                          비중 {strategy.allocation}%
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-200 group-hover:text-cyan-400 transition">
                        {strategy.name}
                      </h3>
                    </div>
                    {getStatusBadge(strategy.status)}
                  </div>

                  <p className="text-xs text-slate-400 font-medium leading-relaxed my-4">
                    {strategy.description}
                  </p>

                  <div className="flex items-center justify-between border-t border-slate-900/80 pt-4 mt-auto">
                    <div className="flex gap-6">
                      <div>
                        <span className="text-[10px] text-slate-500 font-medium block">백테스트 수익률</span>
                        <span className="text-sm font-bold text-emerald-400 font-mono">+{strategy.backtestReturn}%</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 font-medium block">최대 낙폭 (MDD)</span>
                        <span className="text-sm font-bold text-rose-400 font-mono">-{strategy.mdd}%</span>
                      </div>
                    </div>
                    <span className="flex items-center gap-0.5 text-xs text-slate-500 font-bold group-hover:text-cyan-400 transition">
                      분석 및 현재 보유 상세 <ChevronRight size={14} />
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </section>

        {/* Satellite Strategies (30% Allocation) */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-900 pb-3">
            <div className="flex items-center gap-2">
              <Coins size={20} className="text-cyan-400" />
              <h2 className="text-base font-bold text-slate-200">Satellite 전략 (전술적 기회 집중 &bull; 30% 비중)</h2>
            </div>
            <span className="text-xs text-cyan-400 font-bold bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              고수익 기회 포착
            </span>
          </div>

          <div className="space-y-4">
            {strategies
              .filter(s => s.type === "SATELLITE")
              .map(strategy => (
                <div 
                  key={strategy.id}
                  className={`group relative overflow-hidden bg-slate-900/30 backdrop-blur-xl border p-6 rounded-2xl transition-all duration-300 flex flex-col justify-between hover:shadow-xl cursor-pointer ${
                    strategy.status === "SIGNAL"
                      ? "border-cyan-500/30 hover:border-cyan-500/60 hover:shadow-cyan-500/5 bg-cyan-950/5"
                      : "border-slate-900 hover:border-slate-800 hover:shadow-cyan-500/5"
                  }`}
                  onClick={() => onSelectStrategy(strategy.id)}
                >
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-[10px] text-slate-400 font-semibold bg-slate-950/60 px-2 py-0.5 rounded border border-slate-850">
                          {strategy.targetAsset}
                        </span>
                        <span className="text-[10px] text-cyan-400 font-bold bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/10">
                          비중 {strategy.allocation}%
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-200 group-hover:text-cyan-400 transition">
                        {strategy.name}
                      </h3>
                    </div>
                    {getStatusBadge(strategy.status)}
                  </div>

                  <p className="text-xs text-slate-400 font-medium leading-relaxed my-4">
                    {strategy.description}
                  </p>

                  {/* Signal Alert Banner inside the strategy card if signal active */}
                  {strategy.status === "SIGNAL" && strategy.signalMessage && (
                    <div className="mb-4 p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-xl flex items-center gap-2">
                      <AlertCircle size={14} className="text-cyan-400 animate-pulse" />
                      <span className="text-[10px] text-cyan-300 font-bold">{strategy.signalMessage}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between border-t border-slate-900/80 pt-4 mt-auto">
                    <div className="flex gap-6">
                      <div>
                        <span className="text-[10px] text-slate-500 font-medium block">백테스트 수익률</span>
                        <span className="text-sm font-bold text-cyan-400 font-mono">+{strategy.backtestReturn}%</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 font-medium block">최대 낙폭 (MDD)</span>
                        <span className="text-sm font-bold text-rose-400 font-mono">-{strategy.mdd}%</span>
                      </div>
                    </div>
                    <span className="flex items-center gap-0.5 text-xs text-slate-500 font-bold group-hover:text-cyan-400 transition">
                      분석 및 현재 보유 상세 <ChevronRight size={14} />
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </section>
      </div>
    </div>
  );
};
