import React, { useState, useEffect } from "react";
import { RefreshCw, CheckCircle2, AlertTriangle, ArrowRightLeft, Search, Loader2 } from "lucide-react";

interface KisHolding {
  code: string;
  name: string;
  quantity: number;
  sellableQty: number;
  entryPrice: number;
  currentPrice: number;
  valuation: number;
  pnlAmount: number;
  pnlPct: number;
}

interface KisAccountData {
  isPaper: boolean;
  cano: string;
  acntPrdtCd: string;
  deposit: number;
  totalValuation: number;
  netAsset: number;
  totalPnl: number;
  holdings: KisHolding[];
}

export const KisTradingPanel: React.FC = () => {
  // Config Status
  const [accountData, setAccountData] = useState<KisAccountData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form Controls
  const [isPaper, setIsPaper] = useState<boolean>(true);
  const [cano, setCano] = useState<string>("");
  const [realCano, setRealCano] = useState<string>("");
  const [paperCano, setPaperCano] = useState<string>("");
  const [acntPrdtCd, setAcntPrdtCd] = useState<string>("01");

  // Order Inputs
  const [orderSide, setOrderSide] = useState<"BUY" | "SELL">("BUY");
  const [stockCode, setStockCode] = useState<string>("005930");
  const [stockName, setStockName] = useState<string>("삼성전자");
  const [orderType, setOrderType] = useState<"00" | "01">("00"); // 00: 지정가, 01: 시장가
  const [quantity, setQuantity] = useState<number>(10);
  const [price, setPrice] = useState<number>(75000);
  const [submitting, setSubmitting] = useState(false);
  const [orderResult, setOrderResult] = useState<any>(null);

  // Stock Search Modal / Results
  const [searchResults, setSearchResults] = useState<{ code: string; name: string; market: string }[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  // 1. Check Initial Status
  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/kis/status");
      if (res.ok) {
        const json = await res.json();
        const modeIsPaper = json.defaultModeIsPaper ?? true;
        setIsPaper(modeIsPaper);
        setRealCano(json.realCano || "");
        setPaperCano(json.paperCano || "");
        
        const initialCano = modeIsPaper ? (json.paperCano || json.defaultCano) : (json.realCano || json.defaultCano);
        if (initialCano) setCano(initialCano);
        if (json.defaultAcntPrdtCd) setAcntPrdtCd(json.defaultAcntPrdtCd);
      }
    } catch (e) {
      console.error("Failed to fetch KIS status:", e);
    }
  };

  const handleTogglePaperMode = (paperMode: boolean) => {
    setIsPaper(paperMode);
    if (paperMode && paperCano) {
      setCano(paperCano);
    } else if (!paperMode && realCano) {
      setCano(realCano);
    }
  };

  // 2. Fetch Account Balance
  const fetchAccount = async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams();
      query.append("isPaper", isPaper ? "true" : "false");
      if (cano) query.append("cano", cano);
      if (acntPrdtCd) query.append("acntPrdtCd", acntPrdtCd);

      const res = await fetch(`/api/kis/account?${query.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setAccountData(data);
      } else {
        const errJson = await res.json();
        setError(errJson.detail || "계좌 정보를 불러오는데 실패했습니다.");
      }
    } catch (e: any) {
      setError("서버 응답이 없거나 네트워크 통신에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    if (cano && cano.length >= 8) {
      fetchAccount();
    }
  }, [isPaper, cano, acntPrdtCd]);

  // Stock Search Handler
  const handleSearchStock = async (q: string) => {
    setSearchQuery(q);
    if (!q || q.trim().length < 1) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const res = await fetch(`/api/stocks/search?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const list = await res.json();
        setSearchResults(list);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  // Order Submission
  const handleExecuteOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stockCode || quantity <= 0) {
      alert("종목 코드와 수량을 올바르게 입력해주세요.");
      return;
    }
    if (orderType === "00" && price <= 0) {
      alert("지정가 주문 시 주문 가격을 입력해야 합니다.");
      return;
    }

    setSubmitting(true);
    setOrderResult(null);
    try {
      const res = await fetch("/api/kis/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: stockCode,
          qty: quantity,
          price: orderType === "01" ? 0 : price,
          side: orderSide,
          orderType: orderType,
          isPaper: isPaper,
          cano: cano,
          acntPrdtCd: acntPrdtCd
        })
      });

      const json = await res.json();
      if (res.ok) {
        setOrderResult({ success: true, ...json });
        // Refresh account balance after order
        setTimeout(() => fetchAccount(), 1000);
      } else {
        setOrderResult({ success: false, message: json.detail || "주문 실패" });
      }
    } catch (e: any) {
      setOrderResult({ success: false, message: "서버 통신 실패: " + e.message });
    } finally {
      setSubmitting(false);
    }
  };

  const formatKRW = (num: number) => {
    return new Intl.NumberFormat("ko-KR", { style: "currency", currency: "KRW", maximumFractionDigits: 0 }).format(num);
  };

  return (
    <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 rounded-2xl p-6 shadow-2xl space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-emerald-500 flex items-center justify-center shadow-md shadow-amber-500/20">
            <ArrowRightLeft className="text-slate-950 font-bold" size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-extrabold text-slate-100">한국투자증권 (KIS) 실시간 트레이딩</h3>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${isPaper ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"}`}>
                {isPaper ? "모의투자 Mode" : "실전투자 Mode"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium mt-0.5">국내 주식 실시간 잔고 조회 및 지정가/시장가 매수·매도 주문</p>
          </div>
        </div>

        {/* Mode Toggle & Account inputs */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Mode Switch Button */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              type="button"
              onClick={() => handleTogglePaperMode(true)}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${isPaper ? "bg-amber-500 text-slate-950 shadow" : "text-slate-400 hover:text-slate-200"}`}
            >
              모의투자
            </button>
            <button
              type="button"
              onClick={() => handleTogglePaperMode(false)}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${!isPaper ? "bg-emerald-500 text-slate-950 shadow" : "text-slate-400 hover:text-slate-200"}`}
            >
              실전투자
            </button>
          </div>

          {/* Account Number Input */}
          <div className="flex items-center gap-1 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 font-medium">계좌번호:</span>
            <input
              type="text"
              placeholder="8자리 계좌번호"
              value={cano}
              onChange={(e) => setCano(e.target.value)}
              className="w-24 bg-transparent text-slate-200 text-xs font-mono focus:outline-none"
            />
            <span className="text-slate-600 font-mono text-xs">-</span>
            <input
              type="text"
              placeholder="01"
              value={acntPrdtCd}
              onChange={(e) => setAcntPrdtCd(e.target.value)}
              className="w-8 bg-transparent text-slate-200 text-xs font-mono focus:outline-none"
            />
          </div>

          <button
            type="button"
            onClick={fetchAccount}
            disabled={loading}
            className="p-2 bg-slate-950 hover:bg-slate-800 text-slate-300 hover:text-cyan-400 rounded-xl border border-slate-800 transition active:scale-95 cursor-pointer"
            title="잔고 새로고침"
          >
            <RefreshCw size={14} className={loading ? "animate-spin text-cyan-400" : ""} />
          </button>
        </div>
      </div>

      {/* Main Grid: Left Account Info, Right Order Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left: Account Summary & Holdings (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-300 p-4 rounded-xl text-xs flex items-start gap-2.5">
              <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">계좌 조회 안내</p>
                <p className="text-[11px] text-rose-400/90 mt-0.5">{error}</p>
                <p className="text-[10px] text-slate-500 mt-1">.env 파일의 KIS_API_KEY 또는 계좌번호(CANO) 설정을 확인해 주세요.</p>
              </div>
            </div>
          )}

          {/* Balance Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/80">
              <p className="text-[10px] text-slate-500 font-medium">예수금 (Cash)</p>
              <p className="text-sm font-bold font-mono text-amber-400 mt-1">
                {accountData ? formatKRW(accountData.deposit) : "-"}
              </p>
            </div>
            <div className="bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/80">
              <p className="text-[10px] text-slate-500 font-medium">주식 평가금액</p>
              <p className="text-sm font-bold font-mono text-emerald-400 mt-1">
                {accountData ? formatKRW(accountData.totalValuation) : "-"}
              </p>
            </div>
            <div className="bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/80">
              <p className="text-[10px] text-slate-500 font-medium">총 순자산</p>
              <p className="text-sm font-bold font-mono text-slate-200 mt-1">
                {accountData ? formatKRW(accountData.netAsset) : "-"}
              </p>
            </div>
            <div className="bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/80">
              <p className="text-[10px] text-slate-500 font-medium">평가손익 합계</p>
              <p className={`text-sm font-bold font-mono mt-1 ${accountData && accountData.totalPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {accountData ? `${accountData.totalPnl >= 0 ? "+" : ""}${formatKRW(accountData.totalPnl)}` : "-"}
              </p>
            </div>
          </div>

          {/* Active Holdings List */}
          <div className="bg-slate-950/30 border border-slate-900 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold text-slate-300">한국투자증권 보유 주식 목록</h4>
              <span className="text-[10px] text-slate-500 font-mono">
                {accountData ? `${accountData.holdings.length}개 종목` : "조회 전"}
              </span>
            </div>

            {!accountData || accountData.holdings.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-600 border border-dashed border-slate-900 rounded-lg">
                {loading ? "계좌 잔고 및 보유 종목 조회 중..." : "보유 중인 주식이 없거나 계좌를 조회하지 않았습니다."}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-[10px] text-slate-500 font-bold uppercase">
                      <th className="py-2">종목명</th>
                      <th className="py-2 text-right">보유수량</th>
                      <th className="py-2 text-right">평균단가</th>
                      <th className="py-2 text-right">현재가</th>
                      <th className="py-2 text-right">손익률</th>
                      <th className="py-2 text-center">주문</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900/60 text-xs font-mono">
                    {accountData.holdings.map((h, i) => (
                      <tr key={i} className="hover:bg-slate-900/40 transition">
                        <td className="py-2 font-sans font-semibold text-slate-200">
                          {h.name} <span className="text-[10px] text-slate-500 font-mono">{h.code}</span>
                        </td>
                        <td className="py-2 text-right text-slate-300">{h.quantity}주</td>
                        <td className="py-2 text-right text-slate-400">{formatKRW(h.entryPrice)}</td>
                        <td className="py-2 text-right text-slate-200 font-bold">{formatKRW(h.currentPrice)}</td>
                        <td className={`py-2 text-right font-bold ${h.pnlPct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {h.pnlPct >= 0 ? "+" : ""}{h.pnlPct.toFixed(2)}%
                        </td>
                        <td className="py-2 text-center">
                          <button
                            type="button"
                            onClick={() => {
                              setOrderSide("SELL");
                              setStockCode(h.code);
                              setStockName(h.name);
                              setQuantity(h.sellableQty || h.quantity);
                              setPrice(h.currentPrice);
                            }}
                            className="px-2 py-0.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-[10px] font-bold rounded cursor-pointer transition"
                          >
                            매도 선택
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right: Order Form (5 cols) */}
        <div className="lg:col-span-5 bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
            <h4 className="text-xs font-extrabold text-slate-200 flex items-center gap-1.5">
              <span>주식 매수/매도 주문</span>
            </h4>
            <div className="text-[10px] text-slate-500 font-mono">
              {isPaper ? "모의투자 서버" : "실전투자 서버"}
            </div>
          </div>

          <form onSubmit={handleExecuteOrder} className="space-y-4">
            {/* BUY / SELL Switch */}
            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-900 rounded-xl border border-slate-800">
              <button
                type="button"
                onClick={() => setOrderSide("BUY")}
                className={`py-2 text-xs font-black rounded-lg transition cursor-pointer ${orderSide === "BUY" ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20" : "text-slate-400 hover:text-slate-200"}`}
              >
                매수 (BUY)
              </button>
              <button
                type="button"
                onClick={() => setOrderSide("SELL")}
                className={`py-2 text-xs font-black rounded-lg transition cursor-pointer ${orderSide === "SELL" ? "bg-rose-500 text-slate-950 shadow-md shadow-rose-500/20" : "text-slate-400 hover:text-slate-200"}`}
              >
                매도 (SELL)
              </button>
            </div>

            {/* Stock Search Input */}
            <div className="space-y-1 relative">
              <label className="text-[11px] font-semibold text-slate-400">종목 검색 / 코드</label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="종목명 또는 6자리 코드 (예: 삼성전자, 005930)"
                  value={searchQuery || `${stockName} (${stockCode})`}
                  onChange={(e) => handleSearchStock(e.target.value)}
                  onFocus={() => {
                    if (!searchQuery) setSearchQuery(stockName);
                  }}
                  className="w-full bg-slate-900 text-slate-100 text-xs px-3 py-2.5 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-500 font-medium"
                />
                {isSearching ? (
                  <Loader2 size={14} className="absolute right-3 top-3 text-cyan-400 animate-spin pointer-events-none" />
                ) : (
                  <Search size={14} className="absolute right-3 top-3 text-slate-500 pointer-events-none" />
                )}
              </div>

              {/* Search Suggestions Dropdown */}
              {searchResults.length > 0 && (
                <div className="absolute left-0 right-0 top-full mt-1 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-30 max-h-48 overflow-y-auto">
                  {searchResults.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setStockCode(item.code);
                        setStockName(item.name);
                        setSearchResults([]);
                        setSearchQuery("");
                      }}
                      className="w-full text-left px-3 py-2 text-xs hover:bg-slate-800 text-slate-200 flex justify-between items-center transition"
                    >
                      <span className="font-semibold">{item.name}</span>
                      <span className="font-mono text-[10px] text-slate-500">{item.code} ({item.market})</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Order Type Toggle */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-400">주문 유형</label>
              <div className="grid grid-cols-2 gap-2 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setOrderType("00")}
                  className={`py-2 rounded-xl border transition cursor-pointer ${orderType === "00" ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/30" : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"}`}
                >
                  지정가 (Limit)
                </button>
                <button
                  type="button"
                  onClick={() => setOrderType("01")}
                  className={`py-2 rounded-xl border transition cursor-pointer ${orderType === "01" ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/30" : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"}`}
                >
                  시장가 (Market)
                </button>
              </div>
            </div>

            {/* Quantity & Price Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-400">수량 (주)</label>
                <input
                  type="number"
                  min="1"
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 0))}
                  className="w-full bg-slate-900 text-slate-100 text-xs px-3 py-2.5 rounded-xl border border-slate-800 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-400">가격 (원)</label>
                <input
                  type="number"
                  disabled={orderType === "01"}
                  placeholder={orderType === "01" ? "시장가" : "가격 입력"}
                  value={orderType === "01" ? "" : price}
                  onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 disabled:opacity-50 text-slate-100 text-xs px-3 py-2.5 rounded-xl border border-slate-800 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* Total Estimated Amount */}
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800/60 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500 text-[11px]">총 주문 예상 금액:</span>
              <span className="text-slate-100 font-bold text-sm">
                {orderType === "01" ? "체결시 결정 (시장가)" : formatKRW(quantity * price)}
              </span>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className={`w-full py-3 rounded-xl font-black text-xs transition cursor-pointer active:scale-95 shadow-lg ${
                orderSide === "BUY"
                  ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 shadow-emerald-500/20 hover:brightness-110"
                  : "bg-gradient-to-r from-rose-500 to-pink-500 text-slate-950 shadow-rose-500/20 hover:brightness-110"
              }`}
            >
              {submitting ? "주문 전송 중..." : `${stockName} (${stockCode}) ${orderSide === "BUY" ? "매수 주문 전송" : "매도 주문 전송"}`}
            </button>
          </form>

          {/* Order Response Banner */}
          {orderResult && (
            <div className={`p-3.5 rounded-xl border text-xs space-y-1 ${
              orderResult.success ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300" : "bg-rose-500/10 border-rose-500/20 text-rose-300"
            }`}>
              <div className="flex items-center gap-1.5 font-bold">
                {orderResult.success ? <CheckCircle2 size={16} className="text-emerald-400 shrink-0" /> : <AlertTriangle size={16} className="text-rose-400 shrink-0" />}
                <span>{orderResult.success ? "주문 접수 완료" : "주문 실패"}</span>
              </div>
              <p className="text-[11px] font-mono opacity-90">{orderResult.message}</p>
              {orderResult.orderNo && (
                <div className="text-[10px] font-mono text-slate-400 pt-1 border-t border-emerald-500/10">
                  주문번호: <span className="text-slate-200 font-bold">{orderResult.orderNo}</span> | 시각: {orderResult.orderTime}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
