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
import { AccountDetails } from "./components/AccountDetails";
import { RefreshCw, ShieldCheck, LayoutDashboard, Compass, PlusCircle, Search, Globe, Wallet } from "lucide-react";

function App() {
  const [refreshing, setRefreshing] = useState(false);
  const [currentView, setCurrentView] = useState<"DASHBOARD" | "STRATEGY_LIST" | "STRATEGY_DETAIL" | "TRANSACTION_ENTRY" | "STOCK_EXPLORER" | "STOCK_DETAIL" | "MACRO_DASHBOARD" | "ACCOUNT_DETAILS">("DASHBOARD");
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
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-cyan-500 selection:text-slate-900 flex flex-col md:flex-row relative overflow-hidden">
      {/* Background Neon Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-emerald-500/5 rounded-full blur-[120px] pointer-events-none"></div>

      {/* 1. Left Sidebar Navigation */}
      <aside className="w-full md:w-64 lg:w-72 bg-slate-900/20 backdrop-blur-xl border-b md:border-b-0 md:border-r border-slate-900/60 p-6 flex flex-col justify-between shrink-0 z-20 md:min-h-screen">
        <div className="space-y-8">
          {/* Logo Section */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <ShieldCheck size={24} className="text-slate-950 font-bold" />
            </div>
            <div>
              <h1 className="text-sm font-black bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent tracking-wider">
                ASTRON ENGINE
              </h1>
              <p className="text-[10px] text-slate-500 font-medium">통합 투자 대시보드</p>
            </div>
          </div>

          {/* Navigation Menus */}
          <nav className="flex flex-col gap-1.5">
            {/* Dashboard */}
            <button
              onClick={() => {
                setCurrentView("DASHBOARD");
                setSelectedStrategyId(null);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                currentView === "DASHBOARD"
                  ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/20 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/20"
              }`}
            >
              <LayoutDashboard size={16} />
              대시보드
            </button>

            {/* Account Details */}
            <button
              onClick={() => {
                setCurrentView("ACCOUNT_DETAILS");
                setSelectedStrategyId(null);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                currentView === "ACCOUNT_DETAILS"
                  ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/20 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/20"
              }`}
            >
              <Wallet size={16} />
              계좌별 자산 명세
            </button>

            {/* Strategy list & detail */}
            <div className="flex flex-col gap-1">
              <button
                onClick={() => {
                  setCurrentView("STRATEGY_LIST");
                  setSelectedStrategyId(null);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                  currentView === "STRATEGY_LIST" || currentView === "STRATEGY_DETAIL"
                    ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/20 shadow-sm shadow-cyan-500/5"
                    : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/20"
                }`}
              >
                <Compass size={16} />
                전략 분석
              </button>

              {/* Sub-menu for strategies */}
              {(currentView === "STRATEGY_LIST" || currentView === "STRATEGY_DETAIL") && (
                <div className="mt-1 ml-4 pl-3 border-l border-slate-800/80 flex flex-col gap-1">
                  <button
                    onClick={() => handleSelectStrategy("ud_dividend")}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                      selectedStrategyId === "ud_dividend"
                        ? "text-cyan-400 bg-cyan-500/10"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/20"
                    }`}
                  >
                    저평가 고배당
                  </button>
                  <button
                    onClick={() => handleSelectStrategy("op_growth")}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                      selectedStrategyId === "op_growth"
                        ? "text-cyan-400 bg-cyan-500/10"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/20"
                    }`}
                  >
                    우량 기회 성장
                  </button>
                  <button
                    onClick={() => handleSelectStrategy("sector_growth")}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                      selectedStrategyId === "sector_growth"
                        ? "text-cyan-400 bg-cyan-500/10"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/20"
                    }`}
                  >
                    섹터 분산 성장
                  </button>
                  <button
                    onClick={() => handleSelectStrategy("deep_value_contra")}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                      selectedStrategyId === "deep_value_contra"
                        ? "text-cyan-400 bg-cyan-500/10"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/20"
                    }`}
                  >
                    낙폭과대 역발상
                  </button>
                  <button
                    onClick={() => handleSelectStrategy("vol_climax")}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                      selectedStrategyId === "vol_climax"
                        ? "text-cyan-400 bg-cyan-500/10"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/20"
                    }`}
                  >
                    거래량 클라이맥스
                  </button>
                </div>
              )}
            </div>

            {/* Transaction entry */}
            <button
              onClick={() => {
                setCurrentView("TRANSACTION_ENTRY");
                setSelectedStrategyId(null);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                currentView === "TRANSACTION_ENTRY"
                  ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/20 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/20"
              }`}
            >
              <PlusCircle size={16} />
              자산/거래 입력
            </button>

            {/* Stock explorer */}
            <button
              onClick={() => {
                setCurrentView("STOCK_EXPLORER");
                setSelectedStrategyId(null);
                setSelectedStockCode(null);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                currentView === "STOCK_EXPLORER" || currentView === "STOCK_DETAIL"
                  ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/20 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/20"
              }`}
            >
              <Search size={16} />
              종목 탐색
            </button>

            {/* Macro dashboard */}
            <button
              onClick={() => {
                setCurrentView("MACRO_DASHBOARD");
                setSelectedStrategyId(null);
                setSelectedStockCode(null);
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                currentView === "MACRO_DASHBOARD"
                  ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/20 shadow-sm shadow-cyan-500/5"
                  : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/20"
              }`}
            >
              <Globe size={16} />
              거시경제 분석
            </button>
          </nav>
        </div>

        {/* Sidebar Footer Info */}
        <div className="mt-auto pt-6 border-t border-slate-900/80 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-slate-500 font-mono">서버 상태</span>
            <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-bold font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              ONLINE
            </span>
          </div>
          
          <button
            onClick={handleRefresh}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-950/60 hover:bg-slate-900 text-slate-300 hover:text-cyan-400 text-xs font-semibold rounded-xl border border-slate-800/80 active:scale-95 transition-all cursor-pointer"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin text-cyan-400" : ""} />
            새로고침
          </button>
        </div>
      </aside>

      {/* 2. Main Content Frame (Wider Width) */}
      <div className="flex-1 flex flex-col min-h-screen overflow-y-auto">
        <main className="flex-1 p-6 sm:p-8 lg:p-10 space-y-6 w-full max-w-none z-10">
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
                onClickTotalAsset={() => setCurrentView("ACCOUNT_DETAILS")}
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
              transactions={transactions}
              onSelectStock={(code) => {
                setSelectedStockCode(code);
                setCurrentView("STOCK_DETAIL");
              }}
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

          {currentView === "ACCOUNT_DETAILS" && (
            <AccountDetails onBack={() => setCurrentView("DASHBOARD")} />
          )}
        </main>

        {/* Footer */}
        <footer className="text-center py-6 text-[10px] text-slate-600 font-medium border-t border-slate-900/30 mt-auto">
          &copy; {new Date().getFullYear()} pj_invest_platform &bull; All Rights Reserved &bull; Premium Sidebar Dashboard
        </footer>
      </div>
    </div>
  );
}

export default App;

