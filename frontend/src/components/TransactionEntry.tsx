import React, { useState, useEffect, useRef } from "react";
import { 
  PlusCircle, 
  Trash2, 
  DollarSign, 
  FileText
} from "lucide-react";

export interface Transaction {
  id: string;
  date: string;
  assetClass: "STOCK" | "COIN" | "FUTURES" | "GOLD";
  strategyId: string; // 'ud_dividend' | 'op_growth' | 'deep_value_contra' | 'vol_climax' | 'NONE'
  type: "BUY" | "SELL";
  symbol: string;
  name: string;
  price: number;
  qty: number;
  fee: number;
  memo: string;
  currency: "KRW" | "USD";
}

interface TransactionEntryProps {
  cashBalance: number;
  onUpdateCash: (newCash: number) => void;
  transactions: Transaction[];
  onAddTransaction: (tx: Omit<Transaction, "id">) => void;
  onDeleteTransaction: (id: string) => void;
}

interface StockSuggestion {
  code: string;
  name: string;
  market: string;
}

export const TransactionEntry: React.FC<TransactionEntryProps> = ({
  cashBalance,
  onUpdateCash,
  transactions,
  onAddTransaction,
  onDeleteTransaction
}) => {
  // Cash edit state
  const [editingCash, setEditingCash] = useState(false);
  const [cashInput, setCashInput] = useState(cashBalance.toString());

  // Form states
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [assetClass, setAssetClass] = useState<Transaction["assetClass"]>("STOCK");
  const [strategyId, setStrategyId] = useState("NONE");
  const [type, setType] = useState<Transaction["type"]>("BUY");
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [qty, setQty] = useState("");
  const [fee, setFee] = useState("0");
  const [memo, setMemo] = useState("");
  const [currency, setCurrency] = useState<Transaction["currency"]>("KRW");

  // Autocomplete states
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Automatically adjust currency based on assetClass selection
  useEffect(() => {
    if (assetClass === "FUTURES" || assetClass === "COIN") {
      setCurrency("USD");
    } else {
      setCurrency("KRW");
    }
  }, [assetClass]);

  // Autocomplete fetch with debounce
  useEffect(() => {
    if (!symbol.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      try {
        const res = await fetch(`/api/stocks/search?q=${encodeURIComponent(symbol)}&market=${assetClass}`);
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data);
          setShowSuggestions(data.length > 0);
        }
      } catch (e) {
        console.error("Failed to fetch search suggestions", e);
      }
    }, 250); // 250ms debounce

    return () => clearTimeout(delayDebounceFn);
  }, [symbol, assetClass]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleCashSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(cashInput.replace(/,/g, ""));
    if (!isNaN(val) && val >= 0) {
      onUpdateCash(val);
      setEditingCash(false);
    }
  };

  const handleTxSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !name || !price || !qty) {
      alert("종목명, 티커, 단가, 수량은 필수 입력 항목입니다.");
      return;
    }

    const pVal = parseFloat(price);
    const qVal = parseFloat(qty);
    const fVal = parseFloat(fee) || 0;

    if (isNaN(pVal) || pVal <= 0 || isNaN(qVal) || qVal <= 0) {
      alert("단가와 수량은 0보다 큰 수치여야 합니다.");
      return;
    }

    onAddTransaction({
      date,
      assetClass,
      strategyId,
      type,
      symbol: symbol.toUpperCase(),
      name,
      price: pVal,
      qty: qVal,
      fee: fVal,
      memo,
      currency
    });

    // Reset inputs except date
    setSymbol("");
    setName("");
    setPrice("");
    setQty("");
    setFee("0");
    setMemo("");
  };

  const selectSuggestion = (item: StockSuggestion) => {
    setSymbol(item.code);
    setName(item.name);
    
    // Auto adjust asset class based on stock market info
    if (item.market === "FUTURES") {
      setAssetClass("FUTURES");
    } else if (item.market === "COIN") {
      setAssetClass("COIN");
    } else {
      setAssetClass("STOCK");
    }
    
    setShowSuggestions(false);
  };

  const formatKRW = (val: number) => {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: "KRW",
      maximumFractionDigits: 0
    }).format(val);
  };

  const formatUSD = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(val);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      {/* Column 1 & 2: Cash & Transaction Form */}
      <div className="lg:col-span-2 space-y-6">
        
        {/* Cash Balance Setting */}
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-cyan-500/10 text-cyan-400 rounded-xl">
                <DollarSign size={20} />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">현재 가용 현금 (예수금)</span>
                {editingCash ? (
                  <form onSubmit={handleCashSubmit} className="flex items-center gap-2 mt-1">
                    <input 
                      type="text" 
                      value={cashInput}
                      onChange={(e) => setCashInput(e.target.value)}
                      className="bg-slate-950/80 border border-slate-800 text-slate-100 px-3 py-1 text-sm font-black font-mono rounded-lg focus:outline-none focus:border-cyan-500/50"
                      autoFocus
                    />
                    <button type="submit" className="px-3 py-1 bg-cyan-500 hover:bg-cyan-600 text-slate-950 text-xs font-black rounded-lg transition cursor-pointer">저장</button>
                    <button type="button" onClick={() => setEditingCash(false)} className="px-3 py-1 bg-slate-850 hover:bg-slate-800 text-slate-400 text-xs font-bold rounded-lg transition cursor-pointer">취소</button>
                  </form>
                ) : (
                  <h3 className="text-xl font-black text-slate-100 mt-0.5 font-mono">{formatKRW(cashBalance)}</h3>
                )}
              </div>
            </div>
            
            {!editingCash && (
              <button 
                onClick={() => {
                  setCashInput(cashBalance.toString());
                  setEditingCash(true);
                }} 
                className="px-3 py-1.5 bg-slate-950/60 hover:bg-slate-900 text-slate-400 hover:text-cyan-400 text-xs font-bold rounded-lg border border-slate-800/80 transition cursor-pointer"
              >
                예수금 수정
              </button>
            )}
          </div>
        </div>

        {/* Transaction Entry Form */}
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
          <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-3">
            <PlusCircle size={18} className="text-cyan-400" />
            <h2 className="text-sm font-bold text-slate-200">새로운 매매 거래 기록 추가</h2>
          </div>

          <form onSubmit={handleTxSubmit} className="space-y-4">
            
            {/* Form Row 1 */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="text-[10px] text-slate-400 font-bold block mb-1">거래 일자</label>
                <div className="relative">
                  <input 
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50 font-mono"
                    required
                  />
                </div>
              </div>
              
              <div>
                <label className="text-[10px] text-slate-400 font-bold block mb-1">자산군 분류</label>
                <select
                  value={assetClass}
                  onChange={(e) => setAssetClass(e.target.value as Transaction["assetClass"])}
                  className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50"
                >
                  <option value="STOCK">주식 (Domestic/Global)</option>
                  <option value="COIN">가상자산 (Coin)</option>
                  <option value="FUTURES">해외선물 (Futures)</option>
                  <option value="GOLD">금 / 원자재 (Commodity)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 font-bold block mb-1">매매 유형</label>
                <div className="grid grid-cols-2 gap-1.5 p-0.5 bg-slate-950/80 rounded-lg border border-slate-850">
                  <button
                    type="button"
                    onClick={() => setType("BUY")}
                    className={`py-1 rounded text-xs font-bold transition cursor-pointer ${
                      type === "BUY" 
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/10" 
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    매수 (BUY)
                  </button>
                  <button
                    type="button"
                    onClick={() => setType("SELL")}
                    className={`py-1 rounded text-xs font-bold transition cursor-pointer ${
                      type === "SELL" 
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/10" 
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    매도 (SELL)
                  </button>
                </div>
              </div>
            </div>

            {/* Form Row 2 */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="text-[10px] text-slate-400 font-bold block mb-1">관련 투자 전략</label>
                <select
                  value={strategyId}
                  onChange={(e) => setStrategyId(e.target.value)}
                  className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50"
                >
                  <option value="NONE">직접 매매 (전략 없음)</option>
                  <option value="ud_dividend">저평가 고배당 스크리닝</option>
                  <option value="op_growth">우량 기회 성장 스크리닝</option>
                  <option value="deep_value_contra">낙폭과대 역발상 매수</option>
                  <option value="vol_climax">거래량 클라이맥스 돌파</option>
                </select>
              </div>

              {/* Symbol Input with Autocomplete Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <label className="text-[10px] text-slate-400 font-bold block mb-1">종목코드 / 티커</label>
                <input 
                  type="text"
                  placeholder="예: 005930 또는 BTC_USDT"
                  value={symbol}
                  onChange={(e) => {
                    setSymbol(e.target.value);
                    setShowSuggestions(true);
                  }}
                  onFocus={() => {
                    if (symbol.trim()) setShowSuggestions(true);
                  }}
                  className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50 font-mono"
                  required
                />
                
                {/* Autocomplete Dropbox */}
                {showSuggestions && suggestions.length > 0 && (
                  <div className="absolute left-0 right-0 bg-slate-950/95 backdrop-blur-md border border-slate-800 rounded-xl shadow-2xl mt-1 max-h-56 overflow-y-auto z-50 overflow-x-hidden">
                    {suggestions.map((item) => (
                      <button
                        key={item.code}
                        type="button"
                        onClick={() => selectSuggestion(item)}
                        className="w-full px-4 py-2.5 hover:bg-slate-900 transition text-left cursor-pointer flex justify-between items-center border-b border-slate-900/50 last:border-b-0"
                      >
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-slate-200">{item.name}</span>
                          <span className="text-[10px] text-slate-500 font-mono mt-0.5">{item.code}</span>
                        </div>
                        <span className={`text-[8px] font-black px-1.5 py-0.5 rounded uppercase ${
                          item.market === "STOCK" 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/10"
                            : item.market === "COIN"
                            ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/10"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/10"
                        }`}>
                          {item.market}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="text-[10px] text-slate-400 font-bold block mb-1">종목명 / 자산명</label>
                <input 
                  type="text"
                  placeholder="예: 삼성전자 또는 비트코인"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50"
                  required
                />
              </div>
            </div>

            {/* Form Row 3 */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[10px] text-slate-400 font-bold">거래 단가 (Price)</label>
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      onClick={() => setCurrency("KRW")}
                      className={`px-1.5 py-0.5 rounded text-[8px] font-black border transition cursor-pointer ${
                        currency === "KRW"
                          ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/25"
                          : "border-slate-800/80 text-slate-500 hover:text-slate-400"
                      }`}
                    >
                      KRW (₩)
                    </button>
                    <button
                      type="button"
                      onClick={() => setCurrency("USD")}
                      className={`px-1.5 py-0.5 rounded text-[8px] font-black border transition cursor-pointer ${
                        currency === "USD"
                          ? "bg-amber-500/20 text-amber-400 border-amber-500/25"
                          : "border-slate-800/80 text-slate-500 hover:text-slate-400"
                      }`}
                    >
                      USD ($)
                    </button>
                  </div>
                </div>
                <input 
                  type="number"
                  step="any"
                  placeholder={currency === "USD" ? "예: 100.00" : "예: 72000"}
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50 font-mono"
                  required
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-400 font-bold block mb-1.5">거래 수량 (Qty)</label>
                <input 
                  type="number"
                  step="any"
                  placeholder="예: 150"
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50 font-mono"
                  required
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-400 font-bold block mb-1.5">수수료 (Optional)</label>
                <input 
                  type="number"
                  step="any"
                  placeholder="예: 100"
                  value={fee}
                  onChange={(e) => setFee(e.target.value)}
                  className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50 font-mono"
                />
              </div>
            </div>

            {/* Memo Field */}
            <div>
              <label className="text-[10px] text-slate-400 font-bold block mb-1">메모 / 진입 사유</label>
              <textarea 
                placeholder="거래 관련 기록 사항을 남기세요."
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                className="w-full bg-slate-950/60 border border-slate-800 text-slate-300 px-3 py-2 text-xs font-semibold rounded-lg focus:outline-none focus:border-cyan-500/50 h-16 resize-none"
              />
            </div>

            {/* Submit Button */}
            <button 
              type="submit"
              className="w-full py-2.5 bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-600 hover:to-emerald-600 text-slate-950 text-xs font-black rounded-lg transition active:scale-[0.99] cursor-pointer"
            >
              거래 내역 추가하기
            </button>

          </form>
        </div>

      </div>

      {/* Column 3: Recent Logged Transactions */}
      <div className="lg:col-span-1">
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl h-full flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
              <FileText size={18} className="text-cyan-400" />
              <h2 className="text-sm font-bold text-slate-200">최근 입력한 거래 기록</h2>
            </div>
            
            <div className="space-y-3 overflow-y-auto max-h-[360px] pr-1">
              {transactions.map((tx) => {
                const isBuy = tx.type === "BUY";
                return (
                  <div key={tx.id} className="p-3 bg-slate-950/40 border border-slate-900 rounded-xl flex items-center justify-between text-xs transition hover:border-slate-800 group">
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className={`px-1.5 py-0.2 rounded text-[8px] font-black ${
                          isBuy 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}>
                          {isBuy ? "매수" : "매도"}
                        </span>
                        <span className="font-bold text-slate-200">{tx.name}</span>
                        <span className="text-[9px] text-slate-500 font-mono">[{tx.symbol}]</span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        수량: {tx.qty} | 단가: {tx.currency === "USD" ? formatUSD(tx.price) : formatKRW(tx.price)}
                      </div>
                      <div className="text-[8px] text-slate-500 font-mono mt-0.5">
                        {tx.date} {tx.memo && `| ${tx.memo}`}
                      </div>
                    </div>

                    <button 
                      onClick={() => onDeleteTransaction(tx.id)}
                      className="p-1.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-400 rounded-lg opacity-80 group-hover:opacity-100 transition active:scale-95 cursor-pointer"
                      title="거래 삭제"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                );
              })}
              
              {transactions.length === 0 && (
                <div className="py-12 text-center text-slate-500 font-semibold text-xs">
                  최근에 입력한 거래 내역이 없습니다.
                </div>
              )}
            </div>
          </div>
          
          <div className="text-[9px] text-slate-500 mt-6 border-t border-slate-900/50 pt-3">
            ※ 잘못 입력한 내역은 휴지통 아이콘을 누르면 삭제되며, 해당 거래로 수동 변경되었던 자산 잔고와 포지션이 자동으로 롤백됩니다.
          </div>
        </div>
      </div>

    </div>
  );
};
