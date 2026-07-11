import { useState, useEffect } from "react";
import { UnifiedOverview } from "./components/UnifiedOverview";
import { ActiveHoldings } from "./components/ActiveHoldings";
import { SignalAlerts } from "./components/SignalAlerts";
import { RecentTrades } from "./components/RecentTrades";
import { LiveLogs } from "./components/LiveLogs";
import { StrategyList } from "./components/StrategyList";
import { StrategyDetail } from "./components/StrategyDetail";
import { TransactionEntry } from "./components/TransactionEntry";
import type { Transaction } from "./components/TransactionEntry";
import { AssetMonitor } from "./components/AssetMonitor";
import { StockExplorer } from "./components/StockExplorer";
import { StockDetail } from "./components/StockDetail";
import { MacroDashboard } from "./components/MacroDashboard";
import { RefreshCw, ShieldCheck, LayoutDashboard, Compass, PlusCircle, Search, Globe } from "lucide-react";

function App() {
  const [refreshing, setRefreshing] = useState(false);
  const [currentView, setCurrentView] = useState<"DASHBOARD" | "STRATEGY_LIST" | "STRATEGY_DETAIL" | "TRANSACTION_ENTRY" | "STOCK_EXPLORER" | "STOCK_DETAIL" | "MACRO_DASHBOARD">("DASHBOARD");
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [selectedStockCode, setSelectedStockCode] = useState<string | null>(null);

  // Dynamic Portfolio States fetched from Backend API
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  // Fetch Dashboard and Transactions
  const fetchPortfolioData = async () => {
    try {
      const dashRes = await fetch("/api/dashboard");
      if (dashRes.ok) {
        const dashData = await dashRes.json();
        setDashboardData(dashData);
      }

      const txRes = await fetch("/api/transactions");
      if (txRes.ok) {
        const txData = await txRes.json();
        setTransactions(txData);
      }
    } catch (e) {
      console.error("Failed to fetch portfolio data:", e);
    }
  };

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchPortfolioData();
    setRefreshing(false);
  };

  const handleSelectStrategy = (id: string) => {
    setSelectedStrategyId(id);
    setCurrentView("STRATEGY_DETAIL");
  };

  // Transaction Actions
  const handleAddTransaction = async (newTx: Omit<Transaction, "id">) => {
    try {
      const res = await fetch("/api/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newTx)
      });
      if (res.ok) {
        await fetchPortfolioData();
      } else {
        const err = await res.json();
        alert("거래 추가 실패: " + err.detail);
      }
    } catch (e) {
      console.error(e);
      alert("서버 연결에 실패했습니다.");
    }
  };

  const handleDeleteTransaction = async (id: string) => {
    try {
      const res = await fetch(`/api/transactions/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        await fetchPortfolioData();
      } else {
        const err = await res.json();
        alert("거래 삭제 실패: " + err.detail);
      }
    } catch (e) {
      console.error(e);
      alert("서버 연결에 실패했습니다.");
    }
  };

  const handleUpdateCash = async (newCash: number) => {
    try {
      const res = await fetch("/api/cash", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cash: newCash })
      });
      if (res.ok) {
        await fetchPortfolioData();
      } else {
        const err = await res.json();
        alert("예수금 수정 실패: " + err.detail);
      }
    } catch (e) {
      console.error(e);
      alert("서버 연결에 실패했습니다.");
    }
  };

  // Derived properties from fetched API data (with defaults if loading)
  const totalAssets = dashboardData ? dashboardData.totalAsset : 0;
  const cashBalance = dashboardData ? dashboardData.cashBalance : 0;
  const stockWeight = dashboardData ? dashboardData.stockWeight : 0;
  const coinWeight = dashboardData ? dashboardData.coinWeight : 0;
  const cashWeight = dashboardData ? dashboardData.cashWeight : 100;
  const holdingsList = dashboardData ? dashboardData.holdings : [];
  const recentTradesFormatted = dashboardData ? dashboardData.recentTrades : [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8 font-sans antialiased selection:bg-cyan-500 selection:text-slate-900 relative overflow-hidden">
      {/* Background Neon Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-emerald-500/5 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="max-w-7xl mx-auto space-y-6 relative z-10">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <ShieldCheck size={24} className="text-slate-950 font-bold" />
            </div>
            <div>
              <h1 className="text-xl font-black bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent tracking-wide">
                ASTRON TRADING ENGINE
              </h1>
              <p className="text-[10px] text-slate-500 font-medium">통합 투자 파이프라인 & 다중 자산 대시보드</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex bg-slate-950/60 p-1 rounded-xl border border-slate-900 self-stretch md:self-auto justify-center">
            <button
              onClick={() => {
                setCurrentView("DASHBOARD");
                setSelectedStrategyId(null);
              }}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                currentView === "DASHBOARD"
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <LayoutDashboard size={14} />
              대시보드
            </button>
            <button
              onClick={() => {
                setCurrentView("STRATEGY_LIST");
                setSelectedStrategyId(null);
              }}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                currentView === "STRATEGY_LIST" || currentView === "STRATEGY_DETAIL"
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <Compass size={14} />
              전략 분석
            </button>
            <button
              onClick={() => {
                setCurrentView("TRANSACTION_ENTRY");
                setSelectedStrategyId(null);
              }}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                currentView === "TRANSACTION_ENTRY"
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <PlusCircle size={14} />
              자산/거래 입력
            </button>
            <button
              onClick={() => {
                setCurrentView("STOCK_EXPLORER");
                setSelectedStrategyId(null);
                setSelectedStockCode(null);
              }}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                currentView === "STOCK_EXPLORER" || currentView === "STOCK_DETAIL"
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <Search size={14} />
              종목 탐색
            </button>
            <button
              onClick={() => {
                setCurrentView("MACRO_DASHBOARD");
                setSelectedStrategyId(null);
                setSelectedStockCode(null);
              }}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                currentView === "MACRO_DASHBOARD"
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <Globe size={14} />
              거시경제 분석
            </button>
          </div>
          
          <div className="flex items-center gap-3 self-stretch md:self-auto justify-between md:justify-start">
            <span className="text-xs text-slate-400 font-mono bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800/80">
              서버 상태: <span className="text-emerald-400 font-bold">ONLINE</span>
            </span>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-slate-950/60 hover:bg-slate-900 text-slate-300 hover:text-cyan-400 text-xs font-semibold rounded-lg border border-slate-800/80 active:scale-95 transition-all cursor-pointer"
            >
              <RefreshCw size={14} className={refreshing ? "animate-spin text-cyan-400" : ""} />
              새로고침
            </button>
          </div>
        </header>

        {/* Dashboard/Strategy View Router */}
        <main className="space-y-6">
          {currentView === "DASHBOARD" && (
            <>
              {/* 글로벌 다중 자산 실시간 모니터링 */}
              <AssetMonitor />

              {/* Section 1: Portfolio Allocation Summary */}
              <UnifiedOverview 
                totalAsset={totalAssets}
                dailyReturn={2430000}
                dailyReturnPct={1.6}
                cumulativeReturnPct={24.8}
                mdd={-4.2}
                stockWeight={stockWeight}
                coinWeight={coinWeight}
                cashWeight={cashWeight}
              />

              {/* Section 2: Strategy 구동 및 시그널 */}
              <SignalAlerts />

              {/* Section 3: 보유 자산 상세 */}
              <ActiveHoldings holdings={holdingsList} />

              {/* Section 4: 하단 거래 이력 & 로그 콘솔 */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <RecentTrades trades={recentTradesFormatted} />
                </div>
                <div className="lg:col-span-1">
                  <LiveLogs />
                </div>
              </div>
            </>
          )}

          {currentView === "STRATEGY_LIST" && (
            <StrategyList onSelectStrategy={handleSelectStrategy} />
          )}

          {currentView === "STRATEGY_DETAIL" && (
            <StrategyDetail 
              strategyId={selectedStrategyId || ""} 
              onBack={() => {
                setCurrentView("STRATEGY_LIST");
                setSelectedStrategyId(null);
              }} 
            />
          )}

          {currentView === "TRANSACTION_ENTRY" && (
            <TransactionEntry 
              cashBalance={cashBalance}
              onUpdateCash={handleUpdateCash}
              transactions={transactions}
              onAddTransaction={handleAddTransaction}
              onDeleteTransaction={handleDeleteTransaction}
            />
          )}

          {currentView === "STOCK_EXPLORER" && (
            <StockExplorer 
              onSelectStock={(code) => {
                setSelectedStockCode(code);
                setCurrentView("STOCK_DETAIL");
              }} 
            />
          )}

          {currentView === "STOCK_DETAIL" && (
            <StockDetail 
              stockCode={selectedStockCode || ""} 
              onBack={() => {
                setCurrentView("STOCK_EXPLORER");
                setSelectedStockCode(null);
              }} 
            />
          )}

          {currentView === "MACRO_DASHBOARD" && (
            <MacroDashboard />
          )}
        </main>

        {/* Footer */}
        <footer className="text-center py-8 text-[10px] text-slate-600 font-medium border-t border-slate-900/50 mt-12">
          &copy; {new Date().getFullYear()} pj_invest_platform &bull; All Rights Reserved &bull; Premium Quantum Dashboard
        </footer>
      </div>
    </div>
  );
}

export default App;

