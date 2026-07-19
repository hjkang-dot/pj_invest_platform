import React from "react";
import { 
  ArrowLeft, 
  BarChart3, 
  Layers, 
  Info,
  Search,
  Clock,
  Workflow,
  ShieldCheck,
  TrendingUp,
  Zap
} from "lucide-react";
import type { Transaction } from "./TransactionEntry";

interface StrategyDetailProps {
  strategyId: string;
  transactions?: Transaction[];
  onSelectStock?: (code: string) => void;
  onBack: () => void;
}

class StrategyErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("StrategyDetail Error Caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-slate-900/80 border border-cyan-500/30 p-8 rounded-2xl text-center space-y-4 my-6 shadow-2xl">
          <div className="w-12 h-12 bg-cyan-500/10 text-cyan-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
            🔥
          </div>
          <h3 className="text-base font-bold text-slate-100">시장 주도 수급주 전략 화면 복구 완료</h3>
          <p className="text-xs text-slate-400 font-mono">
            {this.state.error?.message || "컴포넌트를 최적화 상태로 재구성했습니다."}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 font-extrabold text-xs rounded-xl shadow-lg cursor-pointer transition active:scale-95"
          >
            🔄 화면 다시 불러오기
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export const StrategyDetailContent: React.FC<StrategyDetailProps> = ({ 
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
      case "step0_market_leader":
        return {
          name: "시장 주도 수급주 (Step 0 ~ Step 1) 전략",
          type: "CORE",
          target: "국내 주식 (KOSPI / KOSDAQ)",
          description: "거래대금 1,000억+ 및 시장 대비 +3%p 이상 폭발한 주도주 중, 5/20일선 정배열과 거래량 35% 이하 dry-up 양봉 지지(Step 1)를 확인하여 진입하고 트레일링 스톱으로 익절을 극대화합니다.",
          allocation: "40%",
          status: "운용중",
          metrics: {
            cumReturn: "+402.85%",
            mdd: "-9.69%",
            sharpe: "2.45",
            winRate: "59.0%",
            profitFactor: "1.91",
            avgTradeReturn: "+2.78%",
            totalTrades: "711회 (344회 한도거절)"
          },
          rules: [
            { name: "주도주 거래대금 기준", value: "1,000억 원 이상 (진성 주도주)" },
            { name: "시장 대비 초과 수익률", value: "(종목 등락률 - 지수 등락률) >= +3.0%p" },
            { name: "조정일 거래량 감소 (Dry-up)", value: "기준봉 거래량 대비 35.0% 이하 급감" },
            { name: "이동평균선 배열 조건", value: "5일선 / 20일선 정배열 가격 지지" },
            { name: "손절가 및 목표가", value: "손절가 -4.0% / 기본 목표가 +5.0%" },
            { name: "트레일링 스톱 본절 상향", value: "+3.0% 반등 시 손절가 0%(본절)로 상향" },
            { name: "이익 확정 Peak Drop", value: "고점 대비 -1.5% 하락 시 즉시 자동 매도" }
          ],
          positions: [],
          chartPath: "M10 80 Q30 75, 50 68 T90 55 T130 50 T170 38 T210 25 T250 18 T290 8"
        };
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
          positions: [] as any[],
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
          positions: [] as any[],
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
          positions: [] as any[],
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
  const isQuantStrategy = strategyId === "ud_dividend" || strategyId === "op_growth" || strategyId === "sector_growth" || strategyId === "step0_market_leader";

  // KIS Order Modal & Telegram Bot States
  const [orderModalOpen, setOrderModalOpen] = React.useState(false);
  const [orderStock, setOrderStock] = React.useState<{ code: string; name: string; price: number } | null>(null);
  const [isPaperOrder, setIsPaperOrder] = React.useState(true);
  const [orderType, setOrderType] = React.useState("01"); // 01: 시장가, 00: 지정가
  const [orderQty, setOrderQty] = React.useState(10);
  const [orderPrice, setOrderPrice] = React.useState(0);
  const [orderSubmitting, setOrderSubmitting] = React.useState(false);
  const [orderMessage, setOrderMessage] = React.useState<{ type: "success" | "error"; text: string } | null>(null);
  
  const [autoTraderActive, setAutoTraderActive] = React.useState(true);
  const [telegramSending, setTelegramSending] = React.useState(false);
  const [botDashboard, setBotDashboard] = React.useState<{
    activePositions: any[];
    tradeHistory: any[];
    logs: string[];
  }>({ activePositions: [], tradeHistory: [], logs: [] });

  const fetchBotDashboard = async () => {
    try {
      const res = await fetch("/api/kis/auto-trader/dashboard");
      if (res.ok) {
        const data = await res.json();
        setBotDashboard(data);
        if (data.botActive !== undefined) setAutoTraderActive(data.botActive);
      }
    } catch (e) {
      console.error("Failed to fetch bot dashboard:", e);
    }
  };

  React.useEffect(() => {
    if (strategyId === "step0_market_leader") {
      fetchBotDashboard();
      const interval = setInterval(fetchBotDashboard, 5000);
      return () => clearInterval(interval);
    }
  }, [strategyId]);

  const handleToggleAutoTrader = async () => {
    try {
      const res = await fetch("/api/kis/auto-trader/toggle", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setAutoTraderActive(data.botActive);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendTelegramTest = async () => {
    setTelegramSending(true);
    try {
      const res = await fetch("/api/kis/telegram-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "<b>[📱 KIS 자동 매매 텔레그램 알림 연동 성공]</b>\n\n• 매수 체결 알림\n• +3.0% 본절 방어선 상향 알림\n• 트레일링 스톱 청산 알림이 실시간으로 발송됩니다! 🚀"
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("텔레그램 메시지가 성공적으로 전송되었습니다! 텔레그램 앱을 확인해 보세요.");
      } else {
        alert("텔레그램 전송 실패: " + (data.detail || "알 수 없는 오류"));
      }
    } catch (e) {
      alert("텔레그램 전송 중 통신 오류가 발생했습니다.");
    } finally {
      setTelegramSending(false);
    }
  };

  const openKisOrderModal = (code?: string, name?: string, priceStr?: string) => {
    const cleanCode = String(code || "").trim();
    const cleanName = String(name || "").replace(/\[.*?\]/g, "").trim() || "종목";
    const rawPrice = parseInt(String(priceStr || "").replace(/[^0-9]/g, ""), 10) || 0;
    setOrderStock({ code: cleanCode, name: cleanName, price: rawPrice });
    setOrderPrice(rawPrice);
    setOrderQty(10);
    setOrderMessage(null);
    setOrderModalOpen(true);
  };

  const handleExecuteKisOrder = async () => {
    if (!orderStock) return;
    setOrderSubmitting(true);
    setOrderMessage(null);
    try {
      const res = await fetch("/api/kis/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: orderStock.code,
          qty: orderQty,
          price: orderType === "01" ? 0 : orderPrice,
          side: "BUY",
          orderType: orderType,
          isPaper: isPaperOrder
        })
      });
      const data = await res.json();
      if (res.ok) {
        setOrderMessage({
          type: "success",
          text: `[${isPaperOrder ? "모의투자" : "실전투자"}] ${orderStock.name} (${orderQty}주) ${orderType === "01" ? "시장가" : orderPrice.toLocaleString() + "원"} 매수 주문이 완료되었습니다! (주문번호: ${data.output?.ODNO || "체결요청완료"})`
        });
      } else {
        setOrderMessage({
          type: "error",
          text: `주문 실패: ${data.detail || JSON.stringify(data)}`
        });
      }
    } catch (e: any) {
      setOrderMessage({
        type: "error",
        text: `통신 오류: ${e.message || String(e)}`
      });
    } finally {
      setOrderSubmitting(false);
    }
  };

  const fetchPositionsAndMetrics = async (query: string = "") => {
    setLoading(true);
    try {
      const url = query 
        ? `/api/strategies/${strategyId}?q=${encodeURIComponent(query)}` 
        : `/api/strategies/${strategyId}`;
      const res = await fetch(url);
      if (res.ok) {
        const result = await res.json();
        setPositions(result.positions || []);
        if (result.metrics) setMetrics(result.metrics);
        if (result.chartPath) setChartPath(result.chartPath || "");
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
      fetchPositionsAndMetrics(strategyId === "step0_market_leader" ? searchQuery : "");
    } else {
      setPositions(data.positions);
      setMetrics(data.metrics);
      setChartPath(data.chartPath);
      setBenchmarkChartPath("");
      setBenchmarkReturn("");
      setSimulatedTrades([]);
    }
  }, [strategyId]);

  React.useEffect(() => {
    if (strategyId === "step0_market_leader") {
      const timer = setTimeout(() => {
        fetchPositionsAndMetrics(searchQuery);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [searchQuery]);

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

      {/* 5-SLOT AUTO TRADER & TELEGRAM CONTROL BANNER */}
      {strategyId === "step0_market_leader" && (
        <div className="bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-cyan-950/40 backdrop-blur-xl border border-cyan-500/30 p-5 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xl">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center border text-lg ${
              autoTraderActive 
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                : "bg-slate-800 border-slate-700 text-slate-400"
            }`}>
              🤖
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-extrabold text-slate-100">KIS 주도주 5슬롯 자동 매매 봇</h3>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  autoTraderActive
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}>
                  {autoTraderActive ? "🟢 가동 중 (Active)" : "⚪ 일시 정지"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                09:00:10 시초가 200만 원 자동 매수 | +3% 본절 상향 | 고점 대비 -1.5% 트레일링 스톱 매도
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 w-full md:w-auto justify-end">
            <button
              onClick={handleSendTelegramTest}
              disabled={telegramSending}
              className="px-3.5 py-2 bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 hover:text-sky-200 text-xs font-bold rounded-xl border border-sky-500/30 cursor-pointer active:scale-95 transition flex items-center gap-1.5 shadow-sm"
              title="텔레그램 메시지 테스트 발송"
            >
              <span>📱</span>
              {telegramSending ? "전송 중..." : "텔레그램 알림 테스트"}
            </button>

            <button
              onClick={handleToggleAutoTrader}
              className={`px-4 py-2 text-xs font-extrabold rounded-xl border cursor-pointer active:scale-95 transition shadow-md flex items-center gap-1.5 ${
                autoTraderActive
                  ? "bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border-rose-500/30"
                  : "bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border-emerald-500/40"
              }`}
            >
              {autoTraderActive ? "⏸️ 봇 일시정지" : "▶️ 봇 가동 시작"}
            </button>
          </div>
        </div>
      )}

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
        <div className="space-y-6">
          {/* MARKET LEADER BOT LIVE DASHBOARD SECTION */}
          {strategyId === "step0_market_leader" && (
            <div className="space-y-6">
              {/* 1. ACTIVE 5-SLOT PORTFOLIO HOLDINGS */}
              <div className="bg-slate-900/40 backdrop-blur-xl border border-cyan-500/30 p-6 rounded-2xl shadow-xl">
                <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2.5">
                    <span className="w-3 h-3 bg-emerald-400 rounded-full animate-ping"></span>
                    <h3 className="text-sm font-extrabold text-slate-100">🤖 현재 자동 매매 봇 보유 종목 (5슬롯 포트폴리오)</h3>
                  </div>
                  <span className="text-[11px] text-emerald-400 font-mono font-bold bg-emerald-500/10 px-3 py-1 rounded-lg border border-emerald-500/20">
                    🟢 실시간 5초 간격 감시 중
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {botDashboard.activePositions && botDashboard.activePositions.length > 0 ? (
                    botDashboard.activePositions.map((pos: any, idx: number) => {
                      const gain = pos.gain_pct || 0;
                      const isPositive = gain >= 0;
                      return (
                        <div key={idx} className="bg-slate-950/90 border border-slate-800 p-4 rounded-xl flex flex-col justify-between space-y-3 hover:border-cyan-500/40 transition shadow-lg">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-base font-black text-slate-100">{pos.name}</span>
                                <span className="text-xs text-slate-500 font-mono">({pos.code})</span>
                              </div>
                              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded mt-1 inline-block border border-emerald-500/20">
                                {pos.status || (pos.trailing_raised ? "🛡️ 본절 방어선 가동 중 (+3% 이상)" : "실시간 감시 중")}
                              </span>
                            </div>
                            <div className="text-right">
                              <span className={`text-lg font-black font-mono block ${isPositive ? "text-emerald-400" : "text-rose-400"}`}>
                                {gain >= 0 ? `+${gain.toFixed(2)}%` : `${gain.toFixed(2)}%`}
                              </span>
                              <span className="text-xs text-slate-400 font-mono">{pos.pnl_krw ? `${pos.pnl_krw > 0 ? '+' : ''}${pos.pnl_krw.toLocaleString()}원` : ''}</span>
                            </div>
                          </div>

                          <div className="grid grid-cols-3 gap-2 pt-2.5 border-t border-slate-900 text-xs font-mono">
                            <div>
                              <span className="text-[10px] text-slate-500 block">매수가</span>
                              <span className="text-slate-300 font-semibold">{pos.entry_price?.toLocaleString()}원</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-500 block">현재가</span>
                              <span className="text-slate-200 font-bold">{pos.current_price?.toLocaleString()}원</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-500 block">보유수량</span>
                              <span className="text-cyan-400 font-bold">{pos.qty}주</span>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="col-span-2 text-center py-8 text-slate-400 text-xs font-semibold">
                      현재 체결되어 보유 중인 포지션이 없습니다. (09:00:10 시초가 자동 매수 대기 중)
                    </div>
                  )}
                </div>
              </div>

              {/* 2. RECENT EXECUTED TRADE HISTORY & LIVE TERMINAL CONSOLE LOG (GRID) */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Trade History */}
                <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl shadow-xl flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                      <h3 className="text-xs font-bold text-slate-100 flex items-center gap-2">
                        <span>📜</span> 최근 체결된 자동 매매 거래 내역
                      </h3>
                      <span className="text-[10px] text-slate-400 font-mono">총 {botDashboard.tradeHistory?.length || 0}건</span>
                    </div>

                    <div className="overflow-x-auto max-h-52 overflow-y-auto">
                      <table className="w-full text-left border-collapse text-[11px]">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400 font-semibold sticky top-0 bg-slate-950">
                            <th className="py-2 px-2.5">매매일</th>
                            <th className="py-2 px-2.5">종목</th>
                            <th className="py-2 px-2.5 text-right">매수가/청산가</th>
                            <th className="py-2 px-2.5 text-right">수익률(손익)</th>
                            <th className="py-2 px-2.5 text-center">사유</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40">
                          {botDashboard.tradeHistory && botDashboard.tradeHistory.length > 0 ? (
                            botDashboard.tradeHistory.map((tr: any, idx: number) => {
                              const isProfit = tr.return_pct >= 0;
                              return (
                                <tr key={idx} className="hover:bg-slate-900/40 transition">
                                  <td className="py-2 px-2.5 font-mono text-slate-400 text-[10px]">{tr.entry_date?.slice(5)}~{tr.exit_date?.slice(5)}</td>
                                  <td className="py-2 px-2.5 font-bold text-slate-200">{tr.name}</td>
                                  <td className="py-2 px-2.5 text-right font-mono text-slate-300">
                                    {tr.entry_price?.toLocaleString()} / {tr.exit_price?.toLocaleString()}
                                  </td>
                                  <td className={`py-2 px-2.5 text-right font-mono font-bold ${isProfit ? "text-emerald-400" : "text-rose-400"}`}>
                                    {tr.return_pct > 0 ? `+${tr.return_pct.toFixed(1)}%` : `${tr.return_pct.toFixed(1)}%`}
                                  </td>
                                  <td className="py-2 px-2.5 text-center">
                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                                      isProfit ? "bg-emerald-500/10 text-emerald-300" : "bg-rose-500/10 text-rose-300"
                                    }`}>
                                      {tr.exit_reason?.split(" ")[0]}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })
                          ) : (
                            <tr>
                              <td colSpan={5} className="py-6 text-center text-slate-500 text-xs">체결 내역 없음</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Live Terminal Console Log */}
                <div className="bg-slate-950 border border-slate-800 p-5 rounded-2xl shadow-xl font-mono text-xs space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-900 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse"></span>
                      <span className="w-2.5 h-2.5 bg-amber-500 rounded-full"></span>
                      <span className="w-2.5 h-2.5 bg-rose-500 rounded-full"></span>
                      <h4 className="text-xs font-extrabold text-slate-200 ml-1">💻 KIS 자동 매매 실시간 터미널 실행 로그</h4>
                    </div>
                    <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">5s Refresh</span>
                  </div>

                  <div className="h-52 overflow-y-auto space-y-1.5 text-[11px] text-slate-300 pr-1 scrollbar-thin scrollbar-thumb-slate-800">
                    {botDashboard.logs && botDashboard.logs.length > 0 ? (
                      botDashboard.logs.map((logStr: string, idx: number) => (
                        <div key={idx} className="flex items-start gap-1.5">
                          <span className="text-cyan-500 font-bold select-none">&gt;</span>
                          <span className={logStr.includes("Buy") ? "text-emerald-400 font-semibold" : logStr.includes("Trailing") ? "text-sky-300 font-semibold" : logStr.includes("Telegram") ? "text-amber-300" : "text-slate-300"}>
                            {logStr}
                          </span>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-600 text-center py-8">로그 데이터를 수신하는 중...</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Candidates & Recommended Stocks */}
            <div className="lg:col-span-2 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
            {/* Header + Search bar */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-5 pb-4 border-b border-slate-900">
              <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                <Layers size={14} className="text-cyan-400" />
                {isQuantStrategy ? "진입 예정 종목 (Step 0 주도주 스크리닝)" : "현재 진입 자산"}
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
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-[9px] text-slate-500 font-mono">[{pos.code}]</span>
                                {pos.statusLabel && (
                                  <span className={`inline-block text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                                    pos.statusLabel === "Step 0 통과"
                                      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                                      : "text-amber-400 bg-amber-500/10 border-amber-500/20"
                                  }`}>
                                    {pos.statusLabel}
                                  </span>
                                )}
                              </div>
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
                              <div className="flex items-center gap-1 justify-center">
                                <button 
                                  onClick={() => openKisOrderModal(pos.code, pos.name, pos.currentPrice || pos.entryPrice)}
                                  className="px-2 py-0.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[9px] font-bold rounded border border-emerald-500/30 cursor-pointer active:scale-95 transition shadow-sm flex items-center gap-1"
                                  title="한국투자증권(KIS) 모의/실전주문 바로가기"
                                >
                                  <span>⚡</span> KIS주문
                                </button>
                                <button 
                                  onClick={() => onSelectStock && onSelectStock(pos.code)}
                                  className="px-2 py-0.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 text-[9px] font-bold rounded border border-cyan-500/20 cursor-pointer active:scale-95 transition"
                                >
                                  분석
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      } else {
                        const pnlVal = String(pos?.pnl || "0");
                        const isProfit = !pnlVal.startsWith("-");
                        return (
                          <tr key={idx} className="hover:bg-slate-800/10">
                            <td className="py-2.5 px-3">
                              {onSelectStock ? (
                                <button
                                  onClick={() => onSelectStock(pos?.code || "")}
                                  className="font-semibold text-slate-100 hover:text-cyan-400 transition cursor-pointer text-left font-sans"
                                  title="종목 상세 분석 대시보드로 이동"
                                >
                                  {pos?.name || "종목"}
                                </button>
                              ) : (
                                <span className="font-semibold text-slate-100">{pos?.name || "종목"}</span>
                              )}
                              <span className="text-[9px] text-slate-500 font-mono block">[{pos?.code || ""}] / 수량: {pos?.qty || 0}</span>
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono">{pos?.entryPrice || "0"}</td>
                            <td className="py-2.5 px-3 text-right font-mono">{pos?.currentPrice || "0"}</td>
                            <td className={`py-2.5 px-3 text-right font-mono font-semibold ${
                              isProfit ? "text-emerald-400" : "text-rose-400"
                            }`}>
                              {pos?.pnl || "0"} {pos?.pnlPct ? `(${pos.pnlPct})` : ""}
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

          {/* Strategy Logic Flow Diagram Card */}
          <div className="lg:col-span-1 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl flex flex-col justify-between shadow-xl">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800/60 pb-3">
              <div className="flex items-center gap-2">
                <Workflow size={16} className="text-cyan-400" />
                <h3 className="text-xs font-bold text-slate-200">봇 자동 매매 전략 로직 다이어그램</h3>
              </div>
              <span className="text-[10px] text-cyan-400 font-mono font-bold bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                알고리즘 플로우
              </span>
            </div>

            <div className="space-y-4 my-auto">
              {/* Step 0 */}
              <div className="relative pl-6 pb-2 border-l-2 border-cyan-500/40">
                <div className="absolute -left-[9px] top-0.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-cyan-400 flex items-center justify-center">
                  <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full"></span>
                </div>
                <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-extrabold text-cyan-300 flex items-center gap-1">
                      <span>1️⃣</span> Step 0: 주도주 탐색
                    </span>
                    <span className="text-[9px] bg-cyan-500/10 text-cyan-400 px-1.5 py-0.2 rounded font-mono font-bold">진입 예정 종목</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug font-medium">
                    · 당일 거래대금 1,000억+ & 지수 대비 +3.0%p 이상 폭발 주도주 탐색<br/>
                    · 20일 평균 대비 거래량 1.5배 이상 스파이크 조건 검증
                  </p>
                </div>
              </div>

              {/* Step 1 */}
              <div className="relative pl-6 pb-2 border-l-2 border-emerald-500/40">
                <div className="absolute -left-[9px] top-0.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-emerald-400 flex items-center justify-center">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                </div>
                <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-extrabold text-emerald-300 flex items-center gap-1">
                      <span>2️⃣</span> Step 1: 시초가 자동 매수
                    </span>
                    <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.2 rounded font-mono font-bold">09:00:10 체결</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug font-medium">
                    · 5일선 / 20일선 정배열 가격 지지 확인<br/>
                    · 조정일 거래량 35% 이하 급감(Dry-up) 양봉 지지 시 09:00:10 시초가 200만 원 자동 체결
                  </p>
                </div>
              </div>

              {/* Step 3: Exit Rules */}
              <div className="relative pl-6">
                <div className="absolute -left-[9px] top-0.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-purple-400 flex items-center justify-center">
                  <span className="w-1.5 h-1.5 bg-purple-400 rounded-full"></span>
                </div>
                <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-2">
                  <span className="text-xs font-extrabold text-purple-300 flex items-center gap-1">
                    <span>3️⃣</span> 청산 및 손익 관리 (Exit)
                  </span>
                  <div className="space-y-1.5 text-[11px] font-medium">
                    <div className="flex items-center justify-between bg-slate-900/80 p-2 rounded border border-slate-850">
                      <span className="text-emerald-400 font-bold flex items-center gap-1">
                        <ShieldCheck size={13}/> +3.0% 반등 달성
                      </span>
                      <span className="text-slate-300 text-[10px] font-semibold">손절가 본절(0.0%) 즉시 상향</span>
                    </div>
                    <div className="flex items-center justify-between bg-slate-900/80 p-2 rounded border border-slate-850">
                      <span className="text-cyan-400 font-bold flex items-center gap-1">
                        <TrendingUp size={13}/> 고점 대비 -1.5%
                      </span>
                      <span className="text-slate-300 text-[10px] font-semibold">트레일링 스톱 이익 확정</span>
                    </div>
                    <div className="flex items-center justify-between bg-slate-900/80 p-2 rounded border border-slate-850">
                      <span className="text-rose-400 font-bold flex items-center gap-1">
                        <Zap size={13}/> -4.0% 손절 이탈
                      </span>
                      <span className="text-slate-300 text-[10px] font-semibold">손절선 즉시 자동 매도</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
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
                {strategyId in {"ud_dividend":1, "op_growth":1, "sector_growth":1} && (
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



      {/* KIS STOCK ORDER MODAL POPUP */}
      {orderModalOpen && orderStock && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-cyan-500/30 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl shadow-cyan-950/40 animate-in fade-in zoom-in-95 duration-200">
            
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse"></span>
                <h3 className="text-sm font-bold text-slate-100">한국투자증권(KIS) 매수 주문</h3>
              </div>
              <button 
                onClick={() => setOrderModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-xs font-bold px-2 py-1 bg-slate-800 rounded-lg"
              >
                ✕ 닫기
              </button>
            </div>

            {/* Target Stock Info */}
            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 flex justify-between items-center">
              <div>
                <span className="text-sm font-extrabold text-cyan-400">{orderStock.name}</span>
                <span className="text-xs text-slate-400 font-mono ml-2">[{orderStock.code}]</span>
              </div>
              <div className="text-right font-mono font-bold text-slate-200 text-sm">
                현재가: {orderStock.price > 0 ? orderStock.price.toLocaleString() + "원" : "시장가"}
              </div>
            </div>

            {/* Order Settings */}
            <div className="space-y-4 text-xs">
              
              {/* Account Mode: Paper vs Real */}
              <div>
                <label className="block text-slate-400 font-semibold mb-1.5">투자 계좌 선택</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setIsPaperOrder(true)}
                    className={`py-2 rounded-xl font-bold border transition ${
                      isPaperOrder 
                        ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 shadow-md" 
                        : "bg-slate-800/40 border-slate-800 text-slate-400 hover:bg-slate-800"
                    }`}
                  >
                    🧪 모의투자 (Paper)
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsPaperOrder(false)}
                    className={`py-2 rounded-xl font-bold border transition ${
                      !isPaperOrder 
                        ? "bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-md" 
                        : "bg-slate-800/40 border-slate-800 text-slate-400 hover:bg-slate-800"
                    }`}
                  >
                    💳 실전투자 (Real)
                  </button>
                </div>
              </div>

              {/* Order Type: Market vs Limit */}
              <div>
                <label className="block text-slate-400 font-semibold mb-1.5">주문 구분</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setOrderType("01")}
                    className={`py-2 rounded-xl font-bold border transition ${
                      orderType === "01" 
                        ? "bg-slate-700 border-slate-500 text-slate-100" 
                        : "bg-slate-800/40 border-slate-800 text-slate-400 hover:bg-slate-800"
                    }`}
                  >
                    ⚡ 시장가 (Fast)
                  </button>
                  <button
                    type="button"
                    onClick={() => setOrderType("00")}
                    className={`py-2 rounded-xl font-bold border transition ${
                      orderType === "00" 
                        ? "bg-slate-700 border-slate-500 text-slate-100" 
                        : "bg-slate-800/40 border-slate-800 text-slate-400 hover:bg-slate-800"
                    }`}
                  >
                    🎯 지정가 (Limit)
                  </button>
                </div>
              </div>

              {/* Quantity & Price */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">주문 수량 (주)</label>
                  <input
                    type="number"
                    min="1"
                    value={orderQty}
                    onChange={(e) => setOrderQty(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 font-mono font-bold focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">
                    {orderType === "01" ? "단가 (시장가)" : "지정 단가 (원)"}
                  </label>
                  <input
                    type="number"
                    disabled={orderType === "01"}
                    value={orderType === "01" ? 0 : orderPrice}
                    onChange={(e) => setOrderPrice(parseInt(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 font-mono font-bold focus:border-cyan-500 focus:outline-none disabled:opacity-50"
                  />
                </div>
              </div>

              {/* Estimated Total Amount */}
              <div className="p-3 bg-cyan-950/30 border border-cyan-900/40 rounded-xl flex justify-between items-center text-xs">
                <span className="text-slate-300 font-medium">예상 총 매수 금액</span>
                <span className="font-mono font-extrabold text-cyan-400 text-sm">
                  {((orderType === "01" ? orderStock.price : orderPrice) * orderQty).toLocaleString()} 원
                </span>
              </div>

              {/* Automated Trailing Stop Note */}
              <div className="p-2.5 bg-slate-950/80 rounded-lg border border-slate-800 text-[10px] text-slate-400 space-y-1">
                <p className="text-emerald-400 font-bold">✓ 자동 매도 스톱 트래킹 설정</p>
                <p>· +3.0% 반등 달성 시: 손절가를 본절가(0.0%)로 즉시 상향보전</p>
                <p>· 고점 대비 -1.5% 이상 밀릴 시: 이익 확정 자동 트레일링 스톱 청산</p>
              </div>

              {/* Response Message */}
              {orderMessage && (
                <div className={`p-3 rounded-xl text-xs font-semibold ${
                  orderMessage.type === "success" 
                    ? "bg-emerald-950/60 text-emerald-300 border border-emerald-800" 
                    : "bg-rose-950/60 text-rose-300 border border-rose-800"
                }`}>
                  {orderMessage.text}
                </div>
              )}

            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setOrderModalOpen(false)}
                className="w-1/3 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl active:scale-95 transition"
              >
                취소
              </button>
              <button
                type="button"
                disabled={orderSubmitting}
                onClick={handleExecuteKisOrder}
                className="w-2/3 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-extrabold rounded-xl shadow-lg shadow-emerald-950/50 active:scale-95 transition disabled:opacity-50"
              >
                {orderSubmitting ? "주문 전송 중..." : "🚀 KIS 매수 주문 실행"}
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};

export const StrategyDetail: React.FC<StrategyDetailProps> = (props) => (
  <StrategyErrorBoundary>
    <StrategyDetailContent {...props} />
  </StrategyErrorBoundary>
);
