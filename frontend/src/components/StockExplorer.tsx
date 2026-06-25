import React, { useState, useEffect } from "react";
import { Search, Globe, ChevronRight, RefreshCw, BarChart2 } from "lucide-react";

interface StockSummary {
  code: string;
  name: string;
  market: string;
  sector: string;
  closePrice: number;
  marketCap: number;
}

interface StockExplorerProps {
  onSelectStock: (code: string) => void;
}

export const StockExplorer: React.FC<StockExplorerProps> = ({ onSelectStock }) => {
  const [stocks, setStocks] = useState<StockSummary[]>([]);
  const [search, setSearch] = useState("");
  const [market, setMarket] = useState<"ALL" | "KOSPI" | "KOSDAQ" | "COIN" | "FUTURES">("ALL");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const checkSyncStatus = async () => {
    try {
      const res = await fetch("/api/stocks/sync/status");
      if (res.ok) {
        const data = await res.json();
        setSyncing(data.isSyncing);
        return data.isSyncing;
      }
    } catch (e) {
      console.error("Failed to check sync status:", e);
    }
    return false;
  };

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      const res = await fetch("/api/stocks/sync", { method: "POST" });
      if (!res.ok) {
        const err = await res.json();
        alert("동기화 실패: " + err.detail);
        setSyncing(false);
      }
    } catch (e) {
      console.error("Failed to start sync:", e);
      alert("서버 연결에 실패했습니다.");
      setSyncing(false);
    }
  };

  // Poll for sync status if syncing
  useEffect(() => {
    let intervalId: any;
    if (syncing) {
      intervalId = setInterval(async () => {
        const isStillSyncing = await checkSyncStatus();
        if (!isStillSyncing) {
          clearInterval(intervalId);
          // Sync completed, reload stocks list
          setOffset(0);
          setHasMore(true);
          fetchStocks(0, true);
        }
      }, 2000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [syncing]);

  // Initial sync status check on mount
  useEffect(() => {
    checkSyncStatus();
  }, []);

  const limit = 50;

  const fetchStocks = async (currentOffset: number, isNewSearch = false) => {
    setLoading(true);
    try {
      const marketParam = market === "ALL" ? "" : market;
      const res = await fetch(
        `/api/stocks?search=${encodeURIComponent(search)}&market=${marketParam}&limit=${limit}&offset=${currentOffset}`
      );
      if (res.ok) {
        const data = await res.json();
        if (data.length < limit) {
          setHasMore(false);
        } else {
          setHasMore(true);
        }

        if (isNewSearch) {
          setStocks(data);
        } else {
          setStocks(prev => [...prev, ...data]);
        }
      }
    } catch (e) {
      console.error("Failed to fetch stocks:", e);
    } finally {
      setLoading(false);
    }
  };

  // Triggered on search input or market filter change
  useEffect(() => {
    setOffset(0);
    setHasMore(true);
    fetchStocks(0, true);
  }, [search, market]);

  const handleLoadMore = () => {
    const nextOffset = offset + limit;
    setOffset(nextOffset);
    fetchStocks(nextOffset, false);
  };

  const isUsdAsset = (marketVal: string, codeVal: string) => {
    return marketVal === "COIN" || marketVal === "FUTURES" || codeVal.includes("_USDT");
  };

  const formatPrice = (price: number, marketVal?: string, codeVal?: string) => {
    const isUsd = marketVal && codeVal ? isUsdAsset(marketVal, codeVal) : false;
    if (isUsd) {
      const decimals = price < 1 ? 4 : 2;
      return `$${price.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
    }
    return `${price.toLocaleString()} 원`;
  };

  const formatMarketCap = (cap: number, marketVal?: string, codeVal?: string) => {
    if (cap === 0) return "-";
    const isUsd = marketVal && codeVal ? isUsdAsset(marketVal, codeVal) : false;
    if (isUsd) {
      const billion = 1000000000;
      const million = 1000000;
      if (cap >= billion) {
        return `$${(cap / billion).toFixed(2)}B`;
      } else if (cap >= million) {
        return `$${(cap / million).toFixed(2)}M`;
      }
      return `$${cap.toLocaleString()}`;
    }
    const trillion = 1000000000000;
    const billion = 100000000;
    
    if (cap >= trillion) {
      const trilVal = cap / trillion;
      const bilVal = (cap % trillion) / billion;
      if (bilVal >= 1) {
        return `${trilVal.toFixed(1)}조 원`;
      }
      return `${Math.round(trilVal)}조 원`;
    } else if (cap >= billion) {
      return `${Math.round(cap / billion)}억 원`;
    }
    return `${cap.toLocaleString()} 원`;
  };

  return (
    <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl space-y-6">
      
      {/* Header and Filters */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-2.5">
          <Globe size={20} className="text-cyan-400" />
          <div>
            <h2 className="text-base font-bold text-slate-200">자산 탐색기</h2>
            <p className="text-[10px] text-slate-500 font-medium">국내외 주식, 가상자산 및 해외선물 종목 검색 및 분석</p>
          </div>
        </div>

        {/* Filters Wrapper */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto">
          {/* Search Box */}
          <div className="relative flex-1 sm:flex-initial">
            <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
            <input
              type="text"
              placeholder="종목명 또는 단축코드 입력"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-slate-950/60 border border-slate-800/80 text-xs font-semibold text-slate-300 pl-9 pr-4 py-2 rounded-lg w-full sm:w-60 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Market Tab Selector */}
          <div className="flex bg-slate-950/60 p-0.5 rounded-lg border border-slate-850">
            {(["ALL", "KOSPI", "KOSDAQ", "COIN", "FUTURES"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMarket(m)}
                className={`px-3 py-1.5 rounded-md text-[10px] font-bold transition-all cursor-pointer ${
                  market === m
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 border border-transparent"
                }`}
              >
                {m === "ALL" 
                  ? "전체 시장" 
                  : m === "COIN" 
                    ? "가상자산" 
                    : m === "FUTURES" 
                      ? "해외선물" 
                      : m}
              </button>
            ))}
          </div>

          {/* Sync Button */}
          <button
            onClick={handleSync}
            disabled={syncing}
            className={`flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-950/60 hover:bg-slate-900 text-[10px] font-bold rounded-lg border border-slate-800/80 active:scale-95 transition-all cursor-pointer disabled:opacity-50 ${
              syncing ? "text-cyan-400 border-cyan-500/20" : "text-slate-400 hover:text-cyan-400"
            }`}
          >
            <RefreshCw size={12} className={syncing ? "animate-spin text-cyan-400" : ""} />
            {syncing ? "주가 동기화 중..." : "최신 주가 동기화"}
          </button>
        </div>
      </div>

      {/* Stock Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 font-semibold">
              <th className="py-3 px-4">종목 코드</th>
              <th className="py-3 px-4">종목명</th>
              <th className="py-3 px-4">시장</th>
              <th className="py-3 px-4">업종 (Sector)</th>
              <th className="py-3 px-4 text-right">현재 종가</th>
              <th className="py-3 px-4 text-right">시가총액</th>
              <th className="py-3 px-4 text-center">상세 보기</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40 text-slate-300 font-medium">
            {stocks.map((stock) => (
              <tr 
                key={stock.code} 
                onClick={() => onSelectStock(stock.code)}
                className="hover:bg-slate-800/10 transition cursor-pointer group"
              >
                <td className="py-3.5 px-4 font-mono font-bold text-slate-400">{stock.code}</td>
                <td className="py-3.5 px-4 font-semibold text-slate-100 group-hover:text-cyan-400 transition">{stock.name}</td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-1.5">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                      stock.market === "KOSPI" 
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                        : stock.market === "KOSDAQ"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : stock.market === "COIN"
                            ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                            : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    }`}>
                      {stock.market}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                      stock.market === "COIN" || stock.market === "FUTURES"
                        ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        : "bg-slate-500/10 text-slate-400 border border-slate-500/20"
                    }`}>
                      {stock.market === "COIN" || stock.market === "FUTURES" ? "선물" : "현물"}
                    </span>
                  </div>
                </td>
                <td className="py-3.5 px-4 text-slate-400">{stock.sector}</td>
                <td className="py-3.5 px-4 text-right font-mono font-bold">{formatPrice(stock.closePrice, stock.market, stock.code)}</td>
                <td className="py-3.5 px-4 text-right font-mono">{formatMarketCap(stock.marketCap, stock.market, stock.code)}</td>
                <td className="py-3.5 px-4 text-center">
                  <span className="inline-flex p-1 bg-slate-950/40 border border-slate-850 hover:border-cyan-500/30 text-slate-500 group-hover:text-cyan-400 rounded-lg transition active:scale-95">
                    <ChevronRight size={12} />
                  </span>
                </td>
              </tr>
            ))}

            {stocks.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500 font-semibold">
                  검색 조건에 맞는 종목이 데이터베이스에 존재하지 않습니다.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Load More Button */}
      {hasMore && stocks.length > 0 && (
        <div className="flex justify-center pt-2">
          <button
            onClick={handleLoadMore}
            disabled={loading}
            className="flex items-center gap-1.5 px-5 py-2 bg-slate-950/60 hover:bg-slate-900 text-slate-300 hover:text-cyan-400 text-xs font-bold rounded-lg border border-slate-800/80 active:scale-95 transition cursor-pointer disabled:opacity-50"
          >
            {loading ? <RefreshCw size={12} className="animate-spin text-cyan-400" /> : <BarChart2 size={12} />}
            종목 더 보기
          </button>
        </div>
      )}

    </div>
  );
};
