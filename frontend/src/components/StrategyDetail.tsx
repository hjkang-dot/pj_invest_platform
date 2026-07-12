import React from "react";
import { 
  ArrowLeft, 
  BarChart3, 
  Sliders, 
  Layers, 
  Info,
  Search,
  Clock
} from "lucide-react";
import type { Transaction } from "./TransactionEntry";

interface StrategyDetailProps {
  strategyId: string;
  transactions?: Transaction[];
  onSelectStock?: (code: string) => void;
  onBack: () => void;
}

export const StrategyDetail: React.FC<StrategyDetailProps> = ({ 
  strategyId, 
  transactions = [], 
  onSelectStock, 
  onBack 
}) => {
  const [positions, setPositions] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [metrics, setMetrics] = React.useState<any>(null);
  const [chartPath, setChartPath] = React.useState<string>("");
  const [activeTab, setActiveTab] = React.useState<"evaluation" | "backtest">("evaluation");
  const [searchQuery, setSearchQuery] = React.useState<string>("");
  const [runningBacktest, setRunningBacktest] = React.useState<boolean>(false);
  const [simulatedTrades, setSimulatedTrades] = React.useState<any[]>([]);
  const [benchmarkChartPath, setBenchmarkChartPath] = React.useState<string>("");
  const [benchmarkReturn, setBenchmarkReturn] = React.useState<string>("");

  // Mock Detailed Data based on Strategy ID (Used as fallback or default)
  const getStrategyData = (id: string) => {
    switch (id) {
      case "ud_dividend":
        return {
          name: "저평가 고배당 스크리닝 전략",
          type: "CORE",
          target: "국내 주식 (KRX)",
          description: "DART 공시 및 배당 히스토리를 분석하여 재무가 건전하고 배당 성향이 우수한 고배당 우량주를 선별하여 장기 투자합니다.",
          allocation: "40%",
          status: "운용중",
          metrics: {
            cumReturn: "12.4%",
            mdd: "-6.2%",
            sharpe: "1.65",
            winRate: "68%",
            profitFactor: "2.1",
            totalTrades: "142"
          },
          rules: [
            { name: "부채비율 (Debt Ratio)", value: "150% 이하" },
            { name: "유동비율 (Current Ratio)", value: "100% 이상" },
            { name: "배당 성향 (Payout Ratio)", value: "20% ~ 60% 사이" },
            { name: "배당 유지/상승 기간", value: "최근 3년 연속 유지/증가" },
            { name: "PBR & PER 필터", value: "PBR 1.0 이하, PER 10 이하" }
          ],
          positions: [
            { name: "SK텔레콤", code: "017670", entryPrice: "51,200", currentPrice: "52,400", qty: "100", pnl: "+120,000", pnlPct: "+2.3%" },
            { name: "KT&G", code: "033780", entryPrice: "92,500", currentPrice: "94,800", qty: "50", pnl: "+115,000", pnlPct: "+2.4%" },
            { name: "기업은행", code: "024110", entryPrice: "13,800", currentPrice: "14,200", qty: "300", pnl: "+120,050", pnlPct: "+2.8%" }
          ],
          chartPath: "M10 80 Q30 75, 50 68 T90 55 T130 50 T170 38 T210 25 T250 18 T290 8"
        };
      case "op_growth":
        return {
          name: "우량 기회 성장 스크리닝 전략",
          type: "CORE",
          target: "국내 주식 / 미국 테크",
          description: "높은 자기자본이익률(ROE)과 합리적인 가치 평가(PEG) 기준을 결합하여, 실적 개선세가 뚜렷한 우량 성장주를 선별합니다.",
          allocation: "30%",
          status: "운용중",
          metrics: {
            cumReturn: "24.8%",
            mdd: "-8.5%",
            sharpe: "1.95",
            winRate: "62%",
            profitFactor: "2.3",
            totalTrades: "84"
          },
          rules: [
            { name: "매출액 성장률", value: "최근 전년 대비 10% 이상" },
            { name: "자기자본이익률 (ROE)", value: "연 15% 이상 유지" },
            { name: "PEG Ratio", value: "1.5 이하" },
            { name: "부채비율", value: "100% 이하" },
            { name: "영업이익 성장률", value: "전년 대비 15% 이상" }
          ],
          positions: [
            { name: "SK하이닉스", code: "000660", entryPrice: "178,000", currentPrice: "182,500", qty: "30", pnl: "+135,000", pnlPct: "+2.5%" },
            { name: "한미반도체", code: "022270", entryPrice: "142,000", currentPrice: "148,600", qty: "40", pnl: "+264,000", pnlPct: "+4.6%" }
          ],
          chartPath: "M10 80 Q30 78, 50 72 T90 62 T130 52 T170 45 T210 32 T250 15 T290 -5"
        };
      case "sector_growth":
        return {
          name: "섹터 분산 성장 스크리닝 전략",
          type: "CORE",
          target: "국내 주식 (KRX)",
          description: "섹터 중복을 배제하고 섹터 별로 최우량 성장 종목을 1개씩만 선정하여 분산 투자합니다. 부합하는 종목이 부족할 경우 현금 비중을 유지합니다.",
          allocation: "20%",
          status: "운용중",
          metrics: {
            cumReturn: "97.2%",
            mdd: "-11.3%",
            sharpe: "1.79",
            winRate: "57%",
            profitFactor: "2.13",
            totalTrades: "14"
          },
          rules: [
            { name: "섹터 분산 필터", value: "동일 업종/섹터 내 최대 1개 종목 편입" },
            { name: "매출액 성장률", value: "최근 전년 대비 10% 이상" },
            { name: "자기자본이익률 (ROE)", value: "연 15% 이상 유지" },
            { name: "종목당 비중 한도", value: "각 20% 동일 비중 (최대 5종목)" },
            { name: "현금 확보 룰", value: "조건 미달 시 해당 슬롯은 현금 유지" }
          ],
          positions: [] as any[],
          chartPath: ""
        };
      case "deep_value_contra":
        return {
          name: "낙폭과대 역발상 매수 전략",
          type: "SATELLITE",
          target: "금 선물 / 해외 원자재",
          description: "단기 매도세가 집중되어 밸류에이션 매력도가 한계치에 다다른 자산을 동적으로 매수하여 기술적 반등 수익을 추구합니다.",
          allocation: "15%",
          status: "신호감지",
          metrics: {
            cumReturn: "18.5%",
            mdd: "-12.4%",
            sharpe: "1.42",
            winRate: "59%",
            profitFactor: "1.95",
            totalTrades: "61"
          },
          rules: [
            { name: "모니터링 주기", value: "글로벌 원자재 종가 기준" },
            { name: "낙폭 기준 (RSI)", value: "RSI(14) 30 이하 과매도" },
            { name: "이동평균 이격도", value: "200일 이평선 하향 이격 10% 이상" },
            { name: "기회 감지 알림", value: "Deep Value 시그널 즉시 발생" },
            { name: "분할 매수 및 손절", value: "3차 분할 매수, 손절 -5%" }
          ],
          positions: [
            { name: "금 선물 (GC=F)", code: "GOLD_FUT", entryPrice: "$2,320.00", currentPrice: "$2,310.50", qty: "10", pnl: "-$95.00", pnlPct: "-0.41%" }
          ],
          chartPath: "M10 80 Q30 85, 50 82 T90 70 T130 75 T170 58 T210 65 T250 42 T290 20"
        };
      case "vol_climax":
      default:
        return {
          name: "거래량 클라이맥스 돌파 전략",
          type: "SATELLITE",
          target: "가상자산 (BTC, ETH)",
          description: "볼린저 밴드 하단 이탈 후 대량의 반등 거래량이 발생하는 시점에 진입하고, ATR 기준으로 손절/익절을 유동적으로 관리합니다.",
          allocation: "15%",
          status: "시그널 대기",
          metrics: {
            cumReturn: "32.1%",
            mdd: "-18.2%",
            sharpe: "1.82",
            winRate: "55%",
            profitFactor: "2.4",
            totalTrades: "112"
          },
          rules: [
            { name: "볼린저 밴드 설정", value: "30일 기준, 표준편차 2.0배" },
            { name: "거래량 돌파 지수", value: "20일 평균 거래량 대비 3배 이상" },
            { name: "매수 진입 조건", value: "Lower BB 터치 후 양봉 캔들 마감" },
            { name: "동적 손절 (SL)", value: "진입가 기준 1.5 * ATR(14)" },
            { name: "동적 익절 (TP)", value: "진입가 기준 3.0 * ATR(14)" }
          ],
          positions: [] as any[],
          chartPath: "M10 80 Q30 78, 50 85 T90 62 T130 65 T170 40 T210 42 T250 12 T290 -8"
        };
    }
  };

  const data = getStrategyData(strategyId);
  const isQuantStrategy = strategyId === "ud_dividend" || strategyId === "op_growth" || strategyId === "sector_growth";

  const fetchPositionsAndMetrics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/strategies/${strategyId}`);
      if (res.ok) {
        const result = await res.json();
        setPositions(result.positions || []);
        setMetrics(result.metrics || null);
        setChartPath(result.chartPath || "");
        setBenchmarkChartPath(result.benchmarkChartPath || "");
        setBenchmarkReturn(result.benchmarkReturn || "");
        setSimulatedTrades(result.simulatedTrades || []);
      }
    } catch (e) {
      console.error("Failed to fetch strategy positions:", e);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (isQuantStrategy) {
      fetchPositionsAndMetrics();
    } else {
      setPositions(data.positions);
      setMetrics(data.metrics);
      setChartPath(data.chartPath);
      setBenchmarkChartPath("");
      setBenchmarkReturn("");
      setSimulatedTrades([]);
    }
  }, [strategyId]);

  const handleRunBacktest = async () => {
    setRunningBacktest(true);
    try {
      const res = await fetch(`/api/strategies/${strategyId}/backtest`, {
        method: "POST"
      });
      if (res.ok) {
        const result = await res.json();
        setMetrics(result);
        setChartPath(result.chartPath || "");
        setBenchmarkChartPath(result.benchmarkChartPath || "");
        setBenchmarkReturn(result.benchmarkReturn || "");
        setSimulatedTrades(result.simulatedTrades || []);
        alert("백테스트가 성공적으로 완료되었습니다! 데이터베이스의 실제 가격/재무 시계열 기준 결과 및 가상 체결 이력으로 업데이트되었습니다.");
      } else {
        const err = await res.json();
        alert("백테스트 실패: " + err.detail);
      }
    } catch (e) {
      console.error(e);
      alert("서버 연결에 실패했습니다.");
    } finally {
      setRunningBacktest(false);
    }
  };

  // Filter positions by search query
  const filteredPositions = positions.filter(pos => 
    pos.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    pos.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const tradesToDisplay = isQuantStrategy 
    ? simulatedTrades 
    : transactions.filter(tx => tx.strategyId === strategyId);

  return (
    <div className="space-y-6">
      {/* 1. Header */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="p-2 bg-slate-950/80 hover:bg-slate-900 text-slate-400 hover:text-cyan-400 rounded-xl border border-slate-800 transition active:scale-95 cursor-pointer"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                data.type === "CORE" 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
              }`}>
                {data.type} 전략
              </span>
              <span className="text-[10px] text-slate-500 font-medium">대상 자산군: {data.target}</span>
            </div>
            <h1 className="text-lg font-black text-slate-100">{data.name}</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-850">
            할당 비중: <span className="text-cyan-400 font-bold">{data.allocation}</span>
          </span>
          <span className={`text-xs font-semibold px-3 py-1.5 rounded-lg border ${
            data.status === "신호감지" 
              ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30 animate-pulse" 
              : data.status === "운용중"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-amber-500/10 text-amber-400 border-amber-500/30"
          }`}>
            상태: {data.status}
          </span>
        </div>
      </header>

      {/* 2. Glassmorphism Tab Bar */}
      <div className="flex gap-2 p-1.5 bg-slate-900/40 backdrop-blur-md rounded-2xl border border-slate-900 max-w-xs">
        <button
          onClick={() => setActiveTab("evaluation")}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === "evaluation"
              ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/20 shadow-sm shadow-cyan-500/5"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/20 border border-transparent"
          }`}
        >
          <Layers size={14} />
          종목 평가
        </button>
        <button
          onClick={() => setActiveTab("backtest")}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === "backtest"
              ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/20 shadow-sm shadow-cyan-500/5"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/20 border border-transparent"
          }`}
        >
          <BarChart3 size={14} />
          백테스트
        </button>
      </div>

      {/* Description Text (Common info) */}
      <div className="bg-slate-900/10 p-5 rounded-2xl border border-slate-900/50">
        <p className="text-xs text-slate-400 leading-relaxed font-medium">
          <Info size={14} className="inline-block text-cyan-500 mr-1.5 -translate-y-[1px]" />
          {data.description}
        </p>
      </div>

      {/* Tab Contents */}
      {activeTab === "evaluation" ? (
        /* SCREEN 1: STOCK EVALUATION & SCREENING */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Candidates & Recommended Stocks */}
          <div className="lg:col-span-2 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
            {/* Header + Search bar */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-5 pb-4 border-b border-slate-900">
              <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                <Layers size={14} className="text-cyan-400" />
                {isQuantStrategy ? "실시간 추천 스크리닝 종목" : "현재 진입 자산"}
              </h3>
              
              <div className="relative w-full sm:w-60">
                <input
                  type="text"
                  placeholder="종목명 또는 코드 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 bg-slate-950/80 border border-slate-900 rounded-xl text-xs text-slate-300 placeholder-slate-650 focus:outline-none focus:border-cyan-500/50 transition-all font-medium"
                />
                <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-650" />
              </div>
            </div>

            <div className="overflow-x-auto">
              {loading ? (
                <div className="text-center py-12 text-slate-500 text-xs font-semibold">
                  전략 스크리닝 계산기를 가동하고 있습니다...
                </div>
              ) : (
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    {isQuantStrategy ? (
                      <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                        <th className="py-2 px-3 w-12 text-center">순위</th>
                        <th className="py-2 px-3">종목 (코드)</th>
                        <th className="py-2 px-3 text-center">평가점수</th>
                        <th className="py-2 px-3 text-right">현재가</th>
                        <th className="py-2 px-3 text-right">투자 매력 지표</th>
                        <th className="py-2 px-3 text-right">세부 지표</th>
                        <th className="py-2 px-3 text-center w-16">액션</th>
                      </tr>
                    ) : (
                      <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                        <th className="py-2 px-3">종목/자산 (수량)</th>
                        <th className="py-2 px-3 text-right">매입가</th>
                        <th className="py-2 px-3 text-right">현재가</th>
                        <th className="py-2 px-3 text-right">평가손익 (수익률)</th>
                        <th className="py-2 px-3 text-center">액션</th>
                      </tr>
                    )}
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 text-slate-300 font-medium">
                    {filteredPositions.map((pos, idx) => {
                      if (isQuantStrategy) {
                        return (
                          <tr key={idx} className="hover:bg-slate-800/10">
                            <td className="py-2.5 px-3 text-center font-mono text-slate-500 font-bold">{idx + 1}</td>
                            <td className="py-2.5 px-3">
                              {onSelectStock ? (
                                <button
                                  onClick={() => onSelectStock(pos.code)}
                                  className="font-semibold text-slate-100 hover:text-cyan-400 transition cursor-pointer text-left font-sans block"
                                  title="종목 상세 분석 대시보드로 이동"
                                >
                                  {pos.name}
                                </button>
                              ) : (
                                <span className="font-semibold text-slate-100 block">{pos.name}</span>
                              )}
                              <span className="text-[9px] text-slate-500 font-mono">[{pos.code}]</span>
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <span className="inline-block text-[10px] text-cyan-400 font-bold bg-cyan-500/10 px-2.5 py-0.5 rounded-full border border-cyan-500/20 shadow-sm font-mono">
                                {pos.qty}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono text-slate-200">{pos.currentPrice}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-slate-300">{pos.entryPrice}</td>
                            <td className="py-2.5 px-3 text-right font-mono">
                              <div className="text-slate-300">{pos.pnl}</div>
                              <div className="text-[9px] text-slate-500 font-normal">{pos.pnlPct}</div>
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <button 
                                onClick={() => onSelectStock && onSelectStock(pos.code)}
                                className="px-2 py-0.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 text-[9px] font-bold rounded border border-cyan-500/20 cursor-pointer active:scale-95 transition"
                              >
                                분석
                              </button>
                            </td>
                          </tr>
                        );
                      } else {
                        const isProfit = !pos.pnl.startsWith("-");
                        return (
                          <tr key={idx} className="hover:bg-slate-800/10">
                            <td className="py-2.5 px-3">
                              {onSelectStock ? (
                                <button
                                  onClick={() => onSelectStock(pos.code)}
                                  className="font-semibold text-slate-100 hover:text-cyan-400 transition cursor-pointer text-left font-sans"
                                  title="종목 상세 분석 대시보드로 이동"
                                >
                                  {pos.name}
                                </button>
                              ) : (
                                <span className="font-semibold text-slate-100">{pos.name}</span>
                              )}
                              <span className="text-[9px] text-slate-500 font-mono block">[{pos.code}] / 수량: {pos.qty}</span>
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono">{pos.entryPrice}</td>
                            <td className="py-2.5 px-3 text-right font-mono">{pos.currentPrice}</td>
                            <td className={`py-2.5 px-3 text-right font-mono font-semibold ${
                              isProfit ? "text-emerald-400" : "text-rose-400"
                            }`}>
                              {pos.pnl} {pos.pnlPct ? `(${pos.pnlPct})` : ""}
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <button className="px-2 py-0.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-[9px] font-bold rounded border border-rose-500/20 cursor-pointer active:scale-95 transition">
                                청산
                              </button>
                            </td>
                          </tr>
                        );
                      }
                    })}
                    {filteredPositions.length === 0 && (
                      <tr>
                        <td colSpan={isQuantStrategy ? 7 : 5} className="py-12 text-center text-slate-500 font-semibold">
                          {searchQuery 
                            ? "검색 필터에 매치되는 종목이 없습니다."
                            : isQuantStrategy
                              ? "스크리닝에 매치되는 종목이 없습니다."
                              : "현재 진입한 포지션 자산이 없습니다. (시그널 모니터링 대기 중)"}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Strategy Parameters (Rules List) */}
          <div className="lg:col-span-1 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl flex flex-col">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800/60 pb-3">
              <div className="flex items-center gap-2">
                <Sliders size={14} className="text-cyan-400" />
                <h3 className="text-xs font-bold text-slate-200">가동 규칙 설정 파라미터</h3>
              </div>
              <button className="px-2 py-0.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 text-[10px] font-bold rounded border border-cyan-500/20 cursor-pointer">
                값 변경
              </button>
            </div>

            <div className="divide-y divide-slate-800/40">
              {data.rules.map((rule, idx) => (
                <div key={idx} className="py-3 flex justify-between items-center gap-2 text-xs">
                  <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <span className="w-1 h-1 bg-cyan-500 rounded-full"></span>
                    {rule.name}
                  </span>
                  <span className="font-bold text-slate-400 font-mono bg-slate-950/40 px-2 py-0.5 rounded border border-slate-900 text-right">
                    {rule.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>
      ) : (
        /* SCREEN 2: BACKTEST STATISTICS & PLOT & TRANSACTION LOG */
        <div className="space-y-6">
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* SVG Cumulative Return Chart */}
            <div className="lg:col-span-2 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl flex flex-col justify-between">
              
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-3 pb-3 border-b border-slate-900/60">
                <div className="flex items-center gap-2">
                  <BarChart3 size={16} className="text-cyan-400" />
                  <div>
                    <h3 className="text-xs font-bold text-slate-300">백테스트 누적 수익률 흐름</h3>
                    <p className="text-[10px] text-slate-500 font-medium">전략 가동 시뮬레이션 결과 곡선 (벤치마크 대비)</p>
                  </div>
                </div>
                {strategyId in {"ud_dividend":1, "op_growth":1} && (
                  <button
                    onClick={handleRunBacktest}
                    disabled={runningBacktest}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 hover:text-cyan-300 text-xs font-bold rounded-xl border border-cyan-500/20 active:scale-95 transition-all cursor-pointer disabled:opacity-50 disabled:scale-100 disabled:cursor-not-allowed"
                  >
                    <svg className={`w-3.5 h-3.5 ${runningBacktest ? "animate-spin" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17.9" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    {runningBacktest ? "시뮬레이션 연산 중..." : "실데이터 백테스트 실행"}
                  </button>
                )}
              </div>

              <div className="w-full h-44 my-4 relative">
                <svg className="w-full h-full" viewBox="0 0 300 100" preserveAspectRatio="none">
                  {/* Grid Lines */}
                  <line x1="0" y1="20" x2="300" y2="20" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                  <line x1="0" y1="50" x2="300" y2="50" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                  <line x1="0" y1="80" x2="300" y2="80" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                  
                  {/* Benchmark curve (Slate) */}
                  <path 
                    d={benchmarkChartPath || "M10 80 Q60 85, 110 75 T210 65 T300 62"} 
                    fill="none" 
                    stroke="#475569" 
                    strokeWidth="1.5" 
                    strokeDasharray="2" 
                  />
                  
                  {/* Strategy curve */}
                  <path 
                    d={chartPath || data.chartPath} 
                    fill="none" 
                    stroke="url(#neonGradientDetail)" 
                    strokeWidth="2.5" 
                    className="drop-shadow-[0_2px_8px_rgba(6,182,212,0.3)]"
                  />
                  
                  {/* Gradients */}
                  <defs>
                    <linearGradient id="neonGradientDetail" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#06b6d4" />
                      <stop offset="100%" stopColor="#10b981" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute top-2 right-2 flex gap-3 text-[9px] font-bold">
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-0.5 bg-cyan-400 inline-block"></span>
                    <span className="text-cyan-400">전략 수익률</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-0.5 border-t border-dashed border-slate-500 inline-block"></span>
                    <span className="text-slate-500">지수/벤치마크</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
                <span>백테스트 시작</span>
                <span>2025.07</span>
                <span>2025.12</span>
                <span>2026.04</span>
                <span>현재 (2026.07)</span>
              </div>
            </div>

            {/* KPIs Grid */}
            <div className="lg:col-span-1 grid grid-cols-2 gap-4">
              <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-5 rounded-2xl">
                <span className="text-[10px] text-slate-500 font-bold block">누적 수익률</span>
                <span className="text-xl font-black text-emerald-400 mt-1 block font-mono">+{metrics?.cumReturn || data.metrics.cumReturn}</span>
                {(() => {
                  const stratRet = parseFloat(metrics?.cumReturn || data.metrics.cumReturn || "0");
                  const benchRet = parseFloat(benchmarkReturn || "33.8");
                  const isOutperforming = stratRet >= benchRet;
                  return (
                    <span className={`text-[9px] font-bold block ${isOutperforming ? "text-emerald-500" : "text-rose-500"}`}>
                      BM({benchRet > 0 ? "+" : ""}{benchRet.toFixed(1)}%) 대비 {isOutperforming ? "우위" : "열위"}
                    </span>
                  );
                })()}
              </div>

              <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-5 rounded-2xl">
                <span className="text-[10px] text-slate-500 font-bold block">최대 낙폭 (MDD)</span>
                <span className="text-xl font-black text-rose-400 mt-1 block font-mono">{metrics?.mdd || data.metrics.mdd}</span>
                <span className="text-[9px] text-slate-500 font-medium">최고점 대비 하락</span>
              </div>

              <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-5 rounded-2xl">
                <span className="text-[10px] text-slate-500 font-bold block">샤프 지수 (Sharpe)</span>
                <span className="text-xl font-black text-slate-200 mt-1 block font-mono">{metrics?.sharpe || data.metrics.sharpe}</span>
                <span className="text-[9px] text-emerald-500 font-semibold">위험 대비 보상 우수</span>
              </div>

              <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-5 rounded-2xl">
                <span className="text-[10px] text-slate-500 font-bold block">승률 (Win Rate)</span>
                <span className="text-xl font-black text-slate-200 mt-1 block font-mono">{metrics?.winRate || data.metrics.winRate}</span>
                <span className="text-[9px] text-slate-500 font-medium">익절 거래 비율</span>
              </div>

              <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-5 rounded-2xl">
                <span className="text-[10px] text-slate-500 font-bold block">손익비 (PF)</span>
                <span className="text-xl font-black text-slate-200 mt-1 block font-mono">{metrics?.profitFactor || data.metrics.profitFactor}</span>
                <span className="text-[9px] text-slate-500 font-medium">총익절 / 총손절</span>
              </div>

              <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-5 rounded-2xl">
                <span className="text-[10px] text-slate-500 font-bold block">총 거래횟수</span>
                <span className="text-xl font-black text-slate-200 mt-1 block font-mono">{metrics?.totalTrades || data.metrics.totalTrades} 회</span>
                <span className="text-[9px] text-slate-500 font-medium">테스트 누적 거래</span>
              </div>
            </div>
          </div>

          {/* Simulated / Actual Transaction Log */}
          <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
            <h3 className="text-xs font-bold text-slate-200 mb-4 flex items-center gap-2 pb-3 border-b border-slate-900">
              <Clock size={14} className="text-cyan-400" />
              {isQuantStrategy 
                ? `백테스트 시뮬레이션 거래 이력 (${tradesToDisplay.length}건)` 
                : `실제 거래 집행 이력 (${tradesToDisplay.length}건)`}
            </h3>
            
            <div className="overflow-y-auto max-h-[400px]">
              <table className="w-full text-left border-collapse text-[11px]">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold sticky top-0 bg-slate-950/80 backdrop-blur-sm z-10">
                    <th className="py-2 px-3">거래 날짜</th>
                    <th className="py-2 px-3">유형</th>
                    <th className="py-2 px-3">자산명</th>
                    <th className="py-2 px-3 text-right">체결 단가</th>
                    <th className="py-2 px-3 text-right">수량</th>
                    <th className="py-2 px-3 text-right">체결 금액</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 text-slate-300 font-medium">
                  {tradesToDisplay.map((tx, idx) => {
                    const isBuy = tx.type === "BUY";
                    // Handle currency formats. Simulated trades are always KRW, actual trades might be USD.
                    const isUsd = tx.currency === "USD" || tx.symbol === "GOLD_FUT" || tx.symbol.endsWith("USDT");
                    const formattedPrice = isUsd 
                      ? `$${tx.price.toLocaleString(undefined, {minimumFractionDigits: 2})}`
                      : `${tx.price.toLocaleString(undefined, {maximumFractionDigits: 0})}원`;
                    const formattedAmount = isUsd
                      ? `$${(tx.price * tx.qty).toLocaleString(undefined, {minimumFractionDigits: 2})}`
                      : `${(tx.price * tx.qty).toLocaleString(undefined, {maximumFractionDigits: 0})}원`;
                    return (
                      <tr key={tx.id || idx} className="hover:bg-slate-800/10">
                        <td className="py-2.5 px-3 font-mono">{tx.date}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-extrabold ${
                            isBuy 
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          }`}>
                            {isBuy ? "매수" : "매도"}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          {onSelectStock ? (
                            <button
                              onClick={() => onSelectStock(tx.symbol)}
                              className="font-semibold text-slate-100 hover:text-cyan-400 transition cursor-pointer text-left font-sans"
                              title="종목 상세 분석 대시보드로 이동"
                            >
                              {tx.name}
                            </button>
                          ) : (
                            <span className="font-semibold text-slate-100">{tx.name}</span>
                          )}
                          <span className="text-[9px] text-slate-500 font-mono block">[{tx.symbol}]</span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono">{formattedPrice}</td>
                        <td className="py-2.5 px-3 text-right font-mono">{tx.qty.toLocaleString(undefined, {maximumFractionDigits: 2})}</td>
                        <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-200">{formattedAmount}</td>
                      </tr>
                    );
                  })}
                  {tradesToDisplay.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-slate-500 font-semibold">
                        {isQuantStrategy
                          ? "백테스트 시뮬레이션 거래 내역이 아직 없습니다. 상단의 '실데이터 백테스트 실행' 버튼을 눌러 연산을 기동해 주세요."
                          : "이 전략으로 집행된 실제 거래 내역이 아직 없습니다. (자산/거래 입력 메뉴에서 거래를 입력할 수 있습니다)"}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

    </div>
  );
};
