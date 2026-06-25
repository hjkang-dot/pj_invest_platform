import React, { useEffect } from "react";
import { ArrowLeft, Landmark, DollarSign, Calendar, BarChart3, TrendingUp, AlertTriangle, ExternalLink } from "lucide-react";

interface FinancialPeriod {
  year: number;
  period: string;
  assets: number | null;
  liabilities: number | null;
  equity: number | null;
  revenue: number | null;
  operatingIncome: number | null;
  netIncome: number | null;
  debtRatio: number | null;
  currentRatio: number | null;
  operatingMargin: number | null;
  netMargin: number | null;
  eps: number | null;
  roe: number | null;
  dividendYield: number | null;
  dividendPerShare: number | null;
  payoutRatio: number | null;
}

interface PricePoint {
  date: string;
  openPrice: number;
  highPrice: number;
  lowPrice: number;
  closePrice: number;
  volume: number;
}

interface StockDetailData {
  code: string;
  name: string;
  market: string;
  sector: string;
  listedDate: string;
  listedShares: number;
  latestPrice: {
    date: string;
    closePrice: number;
    priceChange: number;
    changeRate: number;
    volume: number;
    marketCap: number;
  };
  financials: FinancialPeriod[];
  priceHistory: PricePoint[];
}

interface StockDetailProps {
  stockCode: string;
  onBack: () => void;
}

export const StockDetail: React.FC<StockDetailProps> = ({ stockCode, onBack }) => {
  const [data, setData] = React.useState<StockDetailData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [timeframe, setTimeframe] = React.useState<10 | 30 | 60 | 120>(30);

  const isUsd = data ? (data.market === "COIN" || data.market === "FUTURES" || data.code.includes("_USDT")) : false;

  useEffect(() => {
    const fetchStockDetail = async () => {
      try {
        const res = await fetch(`/api/stocks/${stockCode}`);
        if (res.ok) {
          const detail = await res.json();
          setData(detail);
        }
      } catch (e) {
        console.error("Failed to fetch stock detail:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchStockDetail();
  }, [stockCode]);

  const formatPrice = (price: number) => {
    if (isUsd) {
      const decimals = price < 1 ? 4 : 2;
      return `$${price.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
    }
    return `${price.toLocaleString()} 원`;
  };

  const formatMarketCap = (cap: number) => {
    if (cap === 0) return "-";
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
      return `${(cap / trillion).toFixed(1)}조 원`;
    } else if (cap >= billion) {
      return `${Math.round(cap / billion)}억 원`;
    }
    return `${cap.toLocaleString()} 원`;
  };

  const formatHoverPrice = (price: number) => {
    if (isUsd) {
      const decimals = price < 1 ? 4 : 2;
      return `$${price.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
    }
    return `${price.toLocaleString()} 원`;
  };

  const formatFinancialValue = (val: number | null, unit = "억 원") => {
    if (val === null || isNaN(val)) return "-";
    // In DART company_financials table, values are saved in Won or KRW.
    // e.g. 100,000,000,000 (100 billion won). Let's convert to 억 원 (divide by 10^8)
    const billionWon = 100000000;
    const valueInBillion = val / billionWon;
    return `${valueInBillion.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`;
  };

  const formatPercent = (val: number | null) => {
    if (val === null || isNaN(val)) return "-";
    return `${val.toFixed(1)}%`;
  };

  const formatDPS = (val: number | null) => {
    if (val === null || isNaN(val)) return "-";
    return `${val.toLocaleString()} 원`;
  };

  // Compute candle chart parameters for the selected timeframe
  const getCandleChartData = () => {
    if (!data || data.priceHistory.length === 0) return null;
    
    const visiblePrices = data.priceHistory.slice(-timeframe);
    if (visiblePrices.length === 0) return null;
    
    const pricesHigh = visiblePrices.map(p => p.highPrice);
    const pricesLow = visiblePrices.map(p => p.lowPrice);
    
    const max = Math.max(...pricesHigh);
    const min = Math.min(...pricesLow);
    const range = max - min || 1;
    
    return { visiblePrices, max, min, range };
  };

  if (loading) {
    return (
      <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-12 rounded-2xl flex justify-center items-center">
        <span className="text-slate-400 text-xs font-semibold">종목 재무 및 세부 정보 데이터를 로드하고 있습니다...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-8 rounded-2xl space-y-4 text-center">
        <AlertTriangle className="mx-auto text-amber-500" size={32} />
        <h3 className="text-slate-200 font-bold">오류가 발생했습니다.</h3>
        <p className="text-xs text-slate-500">요청하신 주식 정보를 찾을 수 없습니다.</p>
        <button onClick={onBack} className="px-4 py-2 bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-xl hover:text-cyan-400 transition cursor-pointer">
          목록으로 돌아가기
        </button>
      </div>
    );
  }

  const chart = getCandleChartData();
  const latest = data.latestPrice;
  const isUp = latest.priceChange >= 0;

  const getExternalLink = () => {
    if (data.market === "KOSPI" || data.market === "KOSDAQ") {
      return {
        label: "네이버 증권",
        url: `https://finance.naver.com/item/main.naver?code=${data.code}`,
      };
    } else if (data.market === "COIN") {
      return {
        label: "Aden 거래소",
        url: `https://aden.io/futures/${data.code}`,
      };
    } else if (data.market === "FUTURES") {
      const symbol = data.code.replace("_USDT", "");
      let tvSymbol = symbol;
      if (symbol === "XAU") tvSymbol = "XAUUSD";
      else if (symbol === "CL") tvSymbol = "USOIL";
      else if (symbol === "NAS100") tvSymbol = "NDX";
      return {
        label: "TradingView (출처)",
        url: `https://www.tradingview.com/symbols/${tvSymbol}/`,
      };
    }
    return null;
  };

  const linkInfo = getExternalLink();

  return (
    <div className="space-y-6">
      
      {/* Header */}
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
                data.market === "KOSPI" 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                  : data.market === "KOSDAQ"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : data.market === "COIN"
                      ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                      : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
              }`}>
                {data.market}
              </span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                isUsd
                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  : "bg-slate-500/10 text-slate-400 border border-slate-500/20"
              }`}>
                {isUsd ? "선물" : "현물"}
              </span>
              <span className="text-[10px] text-slate-500 font-medium">업종: {data.sector}</span>
            </div>
            <h1 className="text-lg font-black text-slate-100">{data.name}</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {linkInfo && (
            <a
              href={linkInfo.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs text-slate-350 hover:text-cyan-400 bg-slate-950/60 hover:bg-cyan-500/10 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-cyan-500/30 transition cursor-pointer"
            >
              <ExternalLink size={12} />
              <span>{linkInfo.label}</span>
            </a>
          )}
          {latest.date && (
            <span className="text-xs text-slate-400 font-mono bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-850">
              기준일: <span className="text-cyan-400 font-bold">{latest.date}</span>
            </span>
          )}
          {!isUsd && (
            <>
              <span className="text-xs text-slate-400 font-mono bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-850">
                상장 주식수: <span className="text-cyan-400 font-bold">{data.listedShares.toLocaleString()} 주</span>
              </span>
              <span className="text-xs text-slate-400 font-mono bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-850">
                상장일: <span className="text-cyan-400 font-bold">{data.listedDate}</span>
              </span>
            </>
          )}
        </div>
      </header>

      {/* Grid: Price Card, Mini Chart, KPIs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Latest Price Summary Card */}
        <div className="lg:col-span-1 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center gap-2.5 mb-4">
            <DollarSign className="text-cyan-400" size={16} />
            <span className="text-xs font-bold text-slate-300">최신 시세 요약</span>
            {latest.date && (
              <span className="text-[10px] text-slate-500 font-mono ml-auto">({latest.date})</span>
            )}
          </div>
          
          <div className="space-y-4">
            <div>
              <span className="text-[10px] text-slate-500 font-bold block">현재 종가</span>
              <h2 className="text-3xl font-black text-slate-100 font-mono mt-0.5">{formatPrice(latest.closePrice)}</h2>
              <div className="mt-1 flex items-baseline gap-1.5">
                <span className={`text-xs font-bold font-mono ${isUp ? "text-emerald-400" : "text-rose-400"}`}>
                  {isUp ? "+" : ""}{isUsd ? "$" : ""}{Math.abs(latest.priceChange).toLocaleString(undefined, { minimumFractionDigits: isUsd ? 2 : 0, maximumFractionDigits: isUsd ? 4 : 0 })} {isUsd ? "" : "원"} ({isUp ? "+" : ""}{latest.changeRate.toFixed(2)}%)
                </span>
                <span className="text-[10px] text-slate-500">전일 대비</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 border-t border-slate-900/80 pt-4">
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">거래량</span>
                <span className="text-xs font-black text-slate-300 font-mono block mt-0.5">{latest.volume.toLocaleString()} {isUsd ? "" : "주"}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">시가총액</span>
                <span className="text-xs font-black text-slate-300 font-mono block mt-0.5">{formatMarketCap(latest.marketCap)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* SVG Candle Chart with Timeframe Selector */}
        <div className="lg:col-span-2 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 border-b border-slate-900/80 pb-3">
            <div className="flex items-center gap-2">
              <BarChart3 size={16} className="text-cyan-400" />
              <div>
                <h3 className="text-xs font-bold text-slate-300">주가 흐름 (캔들 차트)</h3>
                <p className="text-[10px] text-slate-500 font-medium">최고 {formatPrice(chart?.max || 0)} / 최저 {formatPrice(chart?.min || 0)}</p>
              </div>
            </div>
            
            {/* Timeframe Select Tabs */}
            <div className="flex bg-slate-950/60 p-0.5 rounded-lg border border-slate-850 self-start sm:self-auto">
              {([10, 30, 60, 120] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTimeframe(t)}
                  className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all cursor-pointer ${
                    timeframe === t
                      ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm"
                      : "text-slate-500 hover:text-slate-300 border border-transparent"
                  }`}
                >
                  {t}일
                </button>
              ))}
            </div>
          </div>

          <div className="w-full h-44 my-2 relative">
            {chart && (
              <svg className="w-full h-full" viewBox="0 0 600 200" preserveAspectRatio="none">
                {/* Horizontal Grid Lines */}
                <line x1="40" y1="20" x2="590" y2="20" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                <line x1="40" y1="100" x2="590" y2="100" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                <line x1="40" y1="180" x2="590" y2="180" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                
                {/* Price labels on Y axis (left side) */}
                <text x="5" y="24" fill="#64748b" className="text-[9px] font-mono">{Math.round(chart.max).toLocaleString()}</text>
                <text x="5" y="104" fill="#64748b" className="text-[9px] font-mono">{Math.round((chart.max + chart.min) / 2).toLocaleString()}</text>
                <text x="5" y="184" fill="#64748b" className="text-[9px] font-mono">{Math.round(chart.min).toLocaleString()}</text>

                {/* Candles */}
                {(() => {
                  const width = 600;
                  const height = 200;
                  const paddingLeft = 50;
                  const paddingRight = 10;
                  const paddingTop = 20;
                  const paddingBottom = 20;
                  const chartW = width - paddingLeft - paddingRight;
                  const chartH = height - paddingTop - paddingBottom;
                  
                  const count = chart.visiblePrices.length;
                  const candleWidth = chartW / count;
                  
                  const getY = (price: number) => {
                    return height - paddingBottom - ((price - chart.min) / chart.range) * chartH;
                  };

                  return chart.visiblePrices.map((p, idx) => {
                    const x = paddingLeft + idx * candleWidth + candleWidth / 2;
                    const yHigh = getY(p.highPrice || 0);
                    const yLow = getY(p.lowPrice || 0);
                    const yOpen = getY(p.openPrice || 0);
                    const yClose = getY(p.closePrice || 0);
                    
                    const isUpCandle = (p.closePrice || 0) >= (p.openPrice || 0);
                    const bodyTop = Math.min(yOpen, yClose);
                    const bodyBottom = Math.max(yOpen, yClose);
                    const bodyH = Math.max(bodyBottom - bodyTop, 2.0); // Minimum 2px height
                    
                    const rectW = Math.max(candleWidth - (count > 60 ? 1 : 2), 1.5);
                    const color = isUpCandle ? "#10b981" : "#f43f5e";
                    
                    return (
                      <g key={idx} className="hover:opacity-80 transition-opacity">
                        <title>
                          {`${p.date.slice(0,4)}-${p.date.slice(4,6)}-${p.date.slice(6,8)}\n시가: ${formatHoverPrice(p.openPrice)}\n고가: ${formatHoverPrice(p.highPrice)}\n저가: ${formatHoverPrice(p.lowPrice)}\n종가: ${formatHoverPrice(p.closePrice)}\n거래량: ${p.volume?.toLocaleString()}`}
                        </title>
                        {/* Wick */}
                        <line
                          x1={x}
                          y1={yHigh}
                          x2={x}
                          y2={yLow}
                          stroke={color}
                          strokeWidth={count > 60 ? "1" : "1.5"}
                        />
                        {/* Body */}
                        <rect
                          x={x - rectW / 2}
                          y={bodyTop}
                          width={rectW}
                          height={bodyH}
                          fill={color}
                        />
                      </g>
                    );
                  });
                })()}
              </svg>
            )}
            
            {(!chart || data.priceHistory.length === 0) && (
              <div className="absolute inset-0 flex items-center justify-center text-slate-600 text-xs">
                최근 주가 데이터 흐름이 존재하지 않습니다.
              </div>
            )}
          </div>

          <div className="flex justify-between items-center text-[9px] text-slate-500 font-mono border-t border-slate-900/40 pt-2">
            <span>{chart?.visiblePrices[0]?.date ? `${chart.visiblePrices[0].date.slice(0,4)}-${chart.visiblePrices[0].date.slice(4,6)}-${chart.visiblePrices[0].date.slice(6,8)}` : ""}</span>
            <span>현재 ({latest.date})</span>
          </div>
        </div>

      </div>

      {/* 4. Multi-Year Financial Statements Table */}
      <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl">
        <h3 className="text-xs font-bold text-slate-200 mb-4 flex items-center gap-2 border-b border-slate-800 pb-3">
          <Landmark size={14} className="text-cyan-400" />
          다년간의 기업 주요 재무제표 및 배당 분석 히스토리 (DART)
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[11px]">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-2.5 px-3">주요 실적 지표</th>
                {data.financials.map((f) => (
                  <th key={f.year} className="py-2.5 px-3 text-right font-mono font-bold text-slate-200">
                    {f.year}년 ({f.period})
                  </th>
                ))}
                {data.financials.length === 0 && <th className="py-2.5 px-3 text-center">-</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40 text-slate-300 font-medium">
              <tr>
                <td className="py-3 px-3 text-slate-400 font-semibold">매출액 (Revenue)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono">{formatFinancialValue(f.revenue)}</td>
                ))}
              </tr>
              <tr>
                <td className="py-3 px-3 text-slate-400 font-semibold">영업이익 (Operating Income)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono">{formatFinancialValue(f.operatingIncome)}</td>
                ))}
              </tr>
              <tr>
                <td className="py-3 px-3 text-slate-400 font-semibold">당기순이익 (Net Income)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono">{formatFinancialValue(f.netIncome)}</td>
                ))}
              </tr>
              <tr className="bg-slate-900/10">
                <td className="py-3 px-3 text-cyan-400 font-semibold">자기자본이익률 (ROE)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono font-bold text-cyan-300">{formatPercent(f.roe)}</td>
                ))}
              </tr>
              <tr>
                <td className="py-3 px-3 text-slate-400 font-semibold">부채비율 (Debt Ratio)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono">{formatPercent(f.debtRatio)}</td>
                ))}
              </tr>
              <tr>
                <td className="py-3 px-3 text-slate-400 font-semibold">유동비율 (Current Ratio)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono">{formatPercent(f.currentRatio)}</td>
                ))}
              </tr>
              <tr className="bg-emerald-500/[0.02]">
                <td className="py-3 px-3 text-emerald-400 font-semibold">주당 배당금 (DPS)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono font-bold text-emerald-300">{formatDPS(f.dividendPerShare)}</td>
                ))}
              </tr>
              <tr className="bg-emerald-500/[0.02]">
                <td className="py-3 px-3 text-emerald-400 font-semibold">배당수익률 (Dividend Yield)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono font-bold text-emerald-300">{formatPercent(f.dividendYield)}</td>
                ))}
              </tr>
              <tr className="bg-emerald-500/[0.02]">
                <td className="py-3 px-3 text-emerald-400 font-semibold">배당성향 (Payout Ratio)</td>
                {data.financials.map((f) => (
                  <td key={f.year} className="py-3 px-3 text-right font-mono font-bold text-emerald-300">{formatPercent(f.payoutRatio)}</td>
                ))}
              </tr>
              {data.financials.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500 font-semibold">
                    {isUsd 
                      ? "이 자산(가상자산/해외선물)은 기업 재무 정보 및 DART 공시 대상이 아닙니다." 
                      : "이 회사에 매핑된 공시 재무보고서 데이터가 존재하지 않습니다. (DART 동기화 필요)"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
