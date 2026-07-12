import React, { useState, useEffect } from "react";
import { ArrowLeft, Wallet, TrendingUp, ShieldAlert, Award } from "lucide-react";

interface StockHolding {
  code: string;
  name: string;
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  valuation: number;
  pnlPct: number;
}

interface CoinPosition {
  contract: string;
  size: number;
  posType: "LONG" | "SHORT";
  entryPrice: number;
  markPrice: number;
  value: number;
  unrealisedPnl: number;
  pnlPct: number;
}

interface FuturesHolding {
  code: string;
  name: string;
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  valuation: number;
  pnlPct: number;
}

interface AccountData {
  metrics: {
    cumulativeReturnPct: number;
    mdd: number;
    dailyReturn: number;
    dailyReturnPct: number;
    stockWeight: number;
    coinWeight: number;
    futuresWeight: number;
    totalAsset: number;
  };
  stockAccount: {
    cash: number;
    valuation: number;
    total: number;
    holdings: StockHolding[];
  };
  coinAccount: {
    usdRate: number;
    cashUsd: number;
    valuationUsd: number;
    totalUsd: number;
    totalKrw: number;
    unrealisedPnlUsd: number;
    positions: CoinPosition[];
  };
  futuresAccount: {
    cashUsd: number;
    valuationUsd: number;
    totalUsd: number;
    totalKrw: number;
    unrealisedPnlUsd: number;
    holdings: FuturesHolding[];
  };
}

interface AccountDetailsProps {
  onBack: () => void;
}

export const AccountDetails: React.FC<AccountDetailsProps> = ({ onBack }) => {
  const [data, setData] = useState<AccountData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Inline editing states
  const [editingStockCash, setEditingStockCash] = useState(false);
  const [stockCashVal, setStockCashVal] = useState("");

  const [editingFuturesCash, setEditingFuturesCash] = useState(false);
  const [futuresCashVal, setFuturesCashVal] = useState("");

  const [saving, setSaving] = useState(false);

  const fetchAccountData = async () => {
    try {
      const res = await fetch("/api/accounts");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        setError("계좌 데이터를 불러오지 못했습니다.");
      }
    } catch (e) {
      console.error(e);
      setError("서버와의 연결이 원활하지 않습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccountData();
  }, []);

  const saveCash = async (accountType: "STOCK" | "FUTURES", amount: number) => {
    setSaving(true);
    try {
      const res = await fetch("/api/accounts/cash", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountType, amount }),
      });
      if (res.ok) {
        await fetchAccountData();
      } else {
        alert("예수금 수정에 실패했습니다.");
      }
    } catch (e) {
      console.error(e);
      alert("서버 연결에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const formatKRW = (val: number) => {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: "KRW",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const formatUSD = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(val);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-12 h-12 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin"></div>
        <p className="text-sm text-slate-400 font-medium">실시간 계좌 정보 조회 중...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-8 text-center max-w-md mx-auto my-12">
        <p className="text-rose-400 font-semibold mb-4">{error || "에러가 발생했습니다."}</p>
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-xl mx-auto transition cursor-pointer"
        >
          <ArrowLeft size={14} />
          대시보드로 돌아가기
        </button>
      </div>
    );
  }

  const { stockAccount, coinAccount, futuresAccount, metrics } = data;

  return (
    <div className="space-y-6">
      {/* Top Controller */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900/40 hover:bg-slate-900/80 text-slate-300 hover:text-cyan-400 text-xs font-bold rounded-xl border border-slate-800 transition active:scale-95 cursor-pointer"
        >
          <ArrowLeft size={14} />
          대시보드
        </button>
        <h2 className="text-lg font-black text-slate-100 bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
          계좌별 자산 명세서 (Account Portfolio)
        </h2>
        <div className="text-right text-[10px] text-slate-500 font-mono">
          기준 환율: $1 = {formatKRW(coinAccount.usdRate)}
        </div>
      </div>

      {/* Performance Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Card 1: Total Asset */}
        <div className="relative overflow-hidden bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-5 shadow-lg">
          <div className="absolute top-0 right-0 w-16 h-16 bg-cyan-500/5 rounded-full blur-xl"></div>
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-cyan-500/10 text-cyan-400 rounded-xl">
              <Wallet size={18} />
            </div>
            <div>
              <p className="text-[10px] font-medium text-slate-500">실시간 총 평가 자산</p>
              <h3 className="text-lg font-extrabold text-slate-100 mt-0.5">{formatKRW(metrics.totalAsset)}</h3>
            </div>
          </div>
        </div>

        {/* Card 4: Current Return */}
        <div className="relative overflow-hidden bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-5 shadow-lg">
          <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-full blur-xl"></div>
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl">
              <Award size={18} />
            </div>
            <div>
              <p className="text-[10px] font-medium text-slate-500">포트폴리오 현재 수익</p>
              <h3 className={`text-lg font-extrabold mt-0.5 ${metrics.dailyReturn >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {metrics.dailyReturn >= 0 ? "+" : ""}{formatKRW(metrics.dailyReturn)} ({metrics.dailyReturnPct >= 0 ? "+" : ""}{metrics.dailyReturnPct}%)
              </h3>
            </div>
          </div>
        </div>

        {/* Card 2: Cumulative Return */}
        <div className="relative overflow-hidden bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-5 shadow-lg">
          <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-500/5 rounded-full blur-xl"></div>
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl">
              <TrendingUp size={18} />
            </div>
            <div>
              <p className="text-[10px] font-medium text-slate-500">누적 수익률</p>
              <h3 className="text-lg font-extrabold text-slate-100 mt-0.5">{metrics.cumulativeReturnPct}%</h3>
            </div>
          </div>
        </div>

        {/* Card 3: MDD */}
        <div className="relative overflow-hidden bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-5 shadow-lg">
          <div className="absolute top-0 right-0 w-16 h-16 bg-rose-500/5 rounded-full blur-xl"></div>
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-rose-500/10 text-rose-400 rounded-xl">
              <ShieldAlert size={18} />
            </div>
            <div>
              <p className="text-[10px] font-medium text-slate-500">최대 낙폭 (MDD)</p>
              <h3 className="text-lg font-extrabold text-rose-400 mt-0.5">{metrics.mdd}%</h3>
            </div>
          </div>
        </div>


      </div>

      {/* Asset Allocation Weight Bar */}
      <div className="bg-slate-900/20 border border-slate-900 rounded-2xl p-5 shadow-md space-y-3">
        <div className="flex items-center justify-between text-xs font-bold text-slate-400">
          <span>계좌별 자산 비중 분배</span>
          <span className="font-mono text-[10px] text-slate-500">가중치 (주식계좌 vs 코인계좌 vs 선물계좌)</span>
        </div>

        {/* Progress Bar Container */}
        <div className="w-full h-3 bg-slate-950 rounded-full flex overflow-hidden border border-slate-900/80 shadow-inner">
          {metrics.stockWeight > 0 && (
            <div
              style={{ width: `${metrics.stockWeight}%` }}
              className="bg-emerald-500 h-full transition-all duration-1000 ease-out"
              title={`주식계좌: ${metrics.stockWeight}%`}
            />
          )}
          {metrics.coinWeight > 0 && (
            <div
              style={{ width: `${metrics.coinWeight}%` }}
              className="bg-cyan-500 h-full transition-all duration-1000 ease-out"
              title={`코인계좌: ${metrics.coinWeight}%`}
            />
          )}
          {metrics.futuresWeight > 0 && (
            <div
              style={{ width: `${metrics.futuresWeight}%` }}
              className="bg-amber-500 h-full transition-all duration-1000 ease-out"
              title={`해외선물계좌: ${metrics.futuresWeight}%`}
            />
          )}
        </div>

        {/* Legend Row */}
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-[10px] font-bold text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>주식계좌 ({metrics.stockWeight}%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
            <span>코인계좌 ({metrics.coinWeight}%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            <span>해외선물계좌 ({metrics.futuresWeight}%)</span>
          </div>
        </div>
      </div>

      {/* Grid Accounts Detail (3-Column Layout for Full-width) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* 1. STOCK & CASH ACCOUNT */}
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl">
                  <Wallet size={20} />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-slate-200">주식 및 예수금 계좌</h3>
                  <p className="text-[10px] text-slate-500 font-medium">개인 입력 원장 및 증권 연동용</p>
                </div>
              </div>
              <span className="text-xs font-bold px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/10 rounded-lg">
                현물 원화계좌
              </span>
            </div>

            {/* Account Summary Row */}
            <div className="grid grid-cols-3 gap-4 bg-slate-950/40 p-4 rounded-xl border border-slate-900/80 mb-6 font-mono">
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">총 계좌 평가액</p>
                <p className="text-sm font-bold text-slate-200">{formatKRW(stockAccount.total)}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">예수금 (Cash)</p>
                {editingStockCash ? (
                  <div className="flex items-center gap-1 mt-1">
                    <input
                      type="number"
                      value={stockCashVal}
                      onChange={(e) => setStockCashVal(e.target.value)}
                      className="w-20 px-1 py-0.5 bg-slate-950 text-slate-100 text-[10px] border border-slate-800 rounded font-mono focus:outline-none"
                      disabled={saving}
                      autoFocus
                    />
                    <button
                      onClick={() => {
                        const amount = parseFloat(stockCashVal);
                        if (!isNaN(amount) && amount >= 0) {
                          saveCash("STOCK", amount);
                        }
                        setEditingStockCash(false);
                      }}
                      className="px-1 py-0.5 bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-[9px] font-bold rounded cursor-pointer"
                    >
                      저장
                    </button>
                    <button
                      onClick={() => setEditingStockCash(false)}
                      className="px-1 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-[9px] font-bold rounded cursor-pointer"
                    >
                      취소
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 mt-1">
                    <p className="text-sm font-bold text-amber-400">{formatKRW(stockAccount.cash)}</p>
                    <button
                      onClick={() => {
                        setStockCashVal(stockAccount.cash.toString());
                        setEditingStockCash(true);
                      }}
                      className="text-[9px] text-slate-500 hover:text-slate-300 underline cursor-pointer"
                    >
                      수정
                    </button>
                  </div>
                )}
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">주식 평가금</p>
                <p className="text-sm font-bold text-emerald-400">{formatKRW(stockAccount.valuation)}</p>
              </div>
            </div>

            {/* Holdings Table */}
            <div className="overflow-x-auto">
              <h4 className="text-xs font-bold text-slate-400 mb-3">보유 현물 주식 상세</h4>
              {stockAccount.holdings.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-600 bg-slate-950/20 rounded-lg border border-dashed border-slate-900">
                  보유한 주식이 없습니다. 자산/거래 입력을 통해 등록해 주세요.
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-900/80 text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                      <th className="py-2.5">종목명</th>
                      <th className="py-2.5 text-right">보유량</th>
                      <th className="py-2.5 text-right">평가금액</th>
                      <th className="py-2.5 text-right">수익률</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900/40 text-xs font-mono">
                    {stockAccount.holdings.map((h, i) => (
                      <tr key={i} className="hover:bg-slate-900/20 transition-all">
                        <td className="py-2.5 font-sans font-semibold text-slate-300">
                          {h.name} <span className="text-[10px] text-slate-500">{h.code}</span>
                        </td>
                        <td className="py-2.5 text-right text-slate-300">{h.quantity}주</td>
                        <td className="py-2.5 text-right font-bold text-slate-200">
                          {formatKRW(h.valuation)}
                        </td>
                        <td className={`py-2.5 text-right font-bold ${h.pnlPct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {h.pnlPct >= 0 ? "+" : ""}{h.pnlPct.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* 2. ADEN COIN FUTURES ACCOUNT */}
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-cyan-500/10 text-cyan-400 rounded-xl">
                  <TrendingUp size={20} />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-slate-200">Aden 선물 거래 계좌</h3>
                  <p className="text-[10px] text-slate-500 font-medium">Aden Exchange API 실시간 연동</p>
                </div>
              </div>
              <span className="text-xs font-bold px-2.5 py-1 bg-cyan-500/10 text-cyan-400 border border-cyan-500/10 rounded-lg">
                코인 달러계좌
              </span>
            </div>

            {/* Account Summary Row */}
            <div className="grid grid-cols-3 gap-4 bg-slate-950/40 p-4 rounded-xl border border-slate-900/80 mb-6 font-mono">
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">총 계좌 가치</p>
                <p className="text-sm font-bold text-slate-200">{formatUSD(coinAccount.totalUsd)}</p>
                <p className="text-[9px] text-slate-500 mt-0.5">({formatKRW(coinAccount.totalKrw)})</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">가용 증거금</p>
                <p className="text-sm font-bold text-amber-400">{formatUSD(coinAccount.cashUsd)}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">미실현 손익</p>
                <p className={`text-sm font-bold ${coinAccount.unrealisedPnlUsd >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {coinAccount.unrealisedPnlUsd >= 0 ? "+" : ""}{formatUSD(coinAccount.unrealisedPnlUsd)}
                </p>
              </div>
            </div>

            {/* Positions Table */}
            <div className="overflow-x-auto">
              <h4 className="text-xs font-bold text-slate-400 mb-3">실시간 선물 보유 포지션</h4>
              {coinAccount.positions.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-600 bg-slate-950/20 rounded-lg border border-dashed border-slate-900">
                  현재 보유 중인 선물 포지션이 없습니다.
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-900/80 text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                      <th className="py-2.5">계약명</th>
                      <th className="py-2.5">구분</th>
                      <th className="py-2.5 text-right">포지션</th>
                      <th className="py-2.5 text-right">수익률</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900/40 text-xs font-mono">
                    {coinAccount.positions.map((pos, i) => (
                      <tr key={i} className="hover:bg-slate-900/20 transition-all">
                        <td className="py-2.5 font-sans font-semibold text-slate-300">
                          {pos.contract}
                        </td>
                        <td className="py-2.5">
                          <span className={`px-1 py-0.5 rounded text-[9px] font-bold ${pos.posType === "LONG" ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
                            }`}>
                            {pos.posType}
                          </span>
                        </td>
                        <td className="py-2.5 text-right text-slate-300">{pos.size}</td>
                        <td className={`py-2.5 text-right font-bold ${pos.pnlPct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {pos.pnlPct >= 0 ? "+" : ""}{pos.pnlPct.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* 3. GLOBAL FUTURES ACCOUNT (NEW!) */}
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl">
                  <Award size={20} />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-slate-200">해외선물 거래 계좌</h3>
                  <p className="text-[10px] text-slate-500 font-medium">개인 입력 선물 원장 관리용</p>
                </div>
              </div>
              <span className="text-xs font-bold px-2.5 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/10 rounded-lg">
                해외 선물 USD계좌
              </span>
            </div>

            {/* Account Summary Row */}
            <div className="grid grid-cols-3 gap-4 bg-slate-950/40 p-4 rounded-xl border border-slate-900/80 mb-6 font-mono">
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">총 계좌 가치</p>
                <p className="text-sm font-bold text-slate-200">{formatUSD(futuresAccount.totalUsd)}</p>
                <p className="text-[9px] text-slate-500 mt-0.5">({formatKRW(futuresAccount.totalKrw)})</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">선물 예수금</p>
                {editingFuturesCash ? (
                  <div className="flex items-center gap-1 mt-1">
                    <input
                      type="number"
                      value={futuresCashVal}
                      onChange={(e) => setFuturesCashVal(e.target.value)}
                      className="w-20 px-1 py-0.5 bg-slate-950 text-slate-100 text-[10px] border border-slate-800 rounded font-mono focus:outline-none"
                      disabled={saving}
                      autoFocus
                    />
                    <button
                      onClick={() => {
                        const amount = parseFloat(futuresCashVal);
                        if (!isNaN(amount) && amount >= 0) {
                          saveCash("FUTURES", amount);
                        }
                        setEditingFuturesCash(false);
                      }}
                      className="px-1 py-0.5 bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-[9px] font-bold rounded cursor-pointer"
                    >
                      저장
                    </button>
                    <button
                      onClick={() => setEditingFuturesCash(false)}
                      className="px-1 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-[9px] font-bold rounded cursor-pointer"
                    >
                      취소
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 mt-1">
                    <p className="text-sm font-bold text-amber-400">{formatUSD(futuresAccount.cashUsd)}</p>
                    <button
                      onClick={() => {
                        setFuturesCashVal(futuresAccount.cashUsd.toString());
                        setEditingFuturesCash(true);
                      }}
                      className="text-[9px] text-slate-500 hover:text-slate-300 underline cursor-pointer"
                    >
                      수정
                    </button>
                  </div>
                )}
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-medium mb-1">선물 평가금</p>
                <p className="text-sm font-bold text-emerald-400">{formatUSD(futuresAccount.valuationUsd)}</p>
              </div>
            </div>

            {/* Holdings Table */}
            <div className="overflow-x-auto">
              <h4 className="text-xs font-bold text-slate-400 mb-3">보유 선물 상품 상세</h4>
              {futuresAccount.holdings.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-600 bg-slate-950/20 rounded-lg border border-dashed border-slate-900">
                  보유 중인 선물 계약이 없습니다. 자산/거래 입력을 통해 등록해 주세요.
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-900/80 text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                      <th className="py-2.5">상품명</th>
                      <th className="py-2.5 text-right">보유량</th>
                      <th className="py-2.5 text-right">평가금액</th>
                      <th className="py-2.5 text-right">수익률</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900/40 text-xs font-mono">
                    {futuresAccount.holdings.map((h, i) => (
                      <tr key={i} className="hover:bg-slate-900/20 transition-all">
                        <td className="py-2.5 font-sans font-semibold text-slate-300">
                          {h.name} <span className="text-[10px] text-slate-500">{h.code}</span>
                        </td>
                        <td className="py-2.5 text-right text-slate-300">{h.quantity}계약</td>
                        <td className="py-2.5 text-right font-bold text-slate-200">
                          {formatUSD(h.valuation)}
                        </td>
                        <td className={`py-2.5 text-right font-bold ${h.pnlPct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {h.pnlPct >= 0 ? "+" : ""}{h.pnlPct.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
