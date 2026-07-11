import React, { useEffect } from "react";
import { ArrowLeft, Landmark, DollarSign, BarChart3, AlertTriangle, ExternalLink } from "lucide-react";

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
  const [cotData, setCotData] = React.useState<any[]>([]);
  const [cotLoading, setCotLoading] = React.useState(false);
  const [hoveredCotIdx, setHoveredCotIdx] = React.useState<number | null>(null);

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

  useEffect(() => {
    if (!data || data.market !== "FUTURES") {
      setCotData([]);
      return;
    }

    const fetchCotData = async () => {
      setCotLoading(true);
      try {
        const res = await fetch(`/api/futures/cot?symbol=${data.code}&limit=30`);
        if (res.ok) {
          const cot = await res.json();
          setCotData(cot);
        }
      } catch (e) {
        console.error("Failed to fetch COT data:", e);
      } finally {
        setCotLoading(false);
      }
    };
    fetchCotData();
  }, [data]);

  const getCotChartParams = () => {
    if (cotData.length === 0) return null;
    const netPositions = cotData.map((d) => d.netPosition);
    const maxVal = Math.max(...netPositions);
    const minVal = Math.min(...netPositions);
    const range = maxVal - minVal || 1;
    const max = maxVal + range * 0.1;
    const min = minVal - range * 0.1;
    const finalRange = max - min;

    const width = 600;
    const height = 180;
    const paddingLeft = 65;
    const paddingRight = 15;
    const paddingTop = 15;
    const paddingBottom = 25;

    const chartW = width - paddingLeft - paddingRight;
    const chartH = height - paddingTop - paddingBottom;

    const points = cotData.map((d, idx) => {
      const x = paddingLeft + (idx / (cotData.length - 1)) * chartW;
      const y = height - paddingBottom - ((d.netPosition - min) / finalRange) * chartH;
      return { x, y, date: d.date, value: d.netPosition, oi: d.openInterest };
    });

    let zeroY: number | null = null;
    if (min < 0 && max > 0) {
      zeroY = height - paddingBottom - ((0 - min) / finalRange) * chartH;
    }

    return { points, max, min, width, height, paddingLeft, paddingRight, paddingTop, paddingBottom, zeroY, chartW, chartH };
  };

  const cotChart = getCotChartParams();

  const getLinePath = (points: { x: number; y: number }[]) => {
    if (points.length === 0) return "";
    return points.reduce((path, p, idx) => {
      return idx === 0 ? `M ${p.x} ${p.y}` : `${path} L ${p.x} ${p.y}`;
    }, "");
  };

  const getAreaPath = (points: { x: number; y: number }[], height: number, paddingBottom: number) => {
    if (points.length === 0) return "";
    const linePath = getLinePath(points);
    const first = points[0];
    const last = points[points.length - 1];
    const baseHeight = height - paddingBottom;
    return `${linePath} L ${last.x} ${baseHeight} L ${first.x} ${baseHeight} Z`;
  };

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

      {/* 4. CFTC COT & Open Interest Analysis (for Futures) OR Financial Statements (for Stocks) */}
      {data.market === "FUTURES" ? (
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl space-y-6">
          <h3 className="text-xs font-bold text-slate-200 border-b border-slate-800 pb-3 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Landmark size={14} className="text-cyan-400" />
              CFTC COT (Commitment of Traders) & 투기 순포지션 추이
            </span>
            <span className="text-[10px] text-slate-500 font-mono">출처: CFTC.gov (매주 금요일 발표)</span>
          </h3>

          {cotLoading ? (
            <div className="text-center py-12 text-slate-400 text-xs font-semibold">
              COT 지표를 분석하고 있습니다...
            </div>
          ) : cotData.length > 0 ? (
            <div className="space-y-6">
              {/* SVG COT Net Position Chart */}
              <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-900 relative">
                <span className="text-[10px] font-bold text-slate-400 mb-2 block">비상업용(투기 세력) 순 매수/매도 포지션 추이</span>
                <div className="w-full h-44 relative mt-2">
                  {cotChart && (
                    <>
                      <svg className="w-full h-full" viewBox={`0 0 ${cotChart.width} ${cotChart.height}`} preserveAspectRatio="none">
                        <defs>
                          <linearGradient id="cotAreaGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.2" />
                            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>

                        {/* Horizontal grids */}
                        {[0.25, 0.5, 0.75].map((ratio, idx) => {
                          const y = cotChart.paddingTop + ratio * (cotChart.height - cotChart.paddingTop - cotChart.paddingBottom);
                          return (
                            <line
                              key={idx}
                              x1={cotChart.paddingLeft}
                              y1={y}
                              x2={cotChart.width - cotChart.paddingRight}
                              y2={y}
                              stroke="#1e293b"
                              strokeWidth="0.5"
                              strokeDasharray="3"
                            />
                          );
                        })}

                        {/* Zero position line */}
                        {cotChart.zeroY !== null && (
                          <line
                            x1={cotChart.paddingLeft}
                            y1={cotChart.zeroY}
                            x2={cotChart.width - cotChart.paddingRight}
                            y2={cotChart.zeroY}
                            stroke="#f43f5e"
                            strokeWidth="1.2"
                            strokeDasharray="4"
                          />
                        )}

                        {/* Area */}
                        <path
                          d={getAreaPath(cotChart.points, cotChart.height, cotChart.paddingBottom)}
                          fill="url(#cotAreaGrad)"
                        />

                        {/* Line */}
                        <path
                          d={getLinePath(cotChart.points)}
                          fill="none"
                          stroke="#22d3ee"
                          strokeWidth="2"
                        />

                        {/* Y-axis Labels */}
                        <text x="5" y={cotChart.paddingTop + 5} fill="#64748b" className="text-[8px] font-mono">
                          {cotChart.max.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </text>
                        <text x="5" y={cotChart.paddingTop + (cotChart.height - cotChart.paddingTop - cotChart.paddingBottom) / 2 + 3} fill="#64748b" className="text-[8px] font-mono">
                          {((cotChart.max + cotChart.min) / 2).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </text>
                        <text x="5" y={cotChart.height - cotChart.paddingBottom + 3} fill="#64748b" className="text-[8px] font-mono">
                          {cotChart.min.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </text>

                        {/* Tracker column triggers */}
                        {cotChart.points.map((p, idx) => {
                          const isHovered = hoveredCotIdx === idx;
                          const colW = cotChart.chartW / cotChart.points.length;
                          return (
                            <g key={idx}>
                              <rect
                                x={p.x - colW / 2}
                                y={cotChart.paddingTop}
                                width={colW}
                                height={cotChart.height - cotChart.paddingTop - cotChart.paddingBottom}
                                fill="transparent"
                                className="cursor-pointer"
                                onMouseEnter={() => setHoveredCotIdx(idx)}
                                onMouseLeave={() => setHoveredCotIdx(null)}
                              />
                              {(isHovered || idx === cotChart.points.length - 1) && (
                                <>
                                  <line
                                    x1={p.x}
                                    y1={cotChart.paddingTop}
                                    x2={p.x}
                                    y2={cotChart.height - cotChart.paddingBottom}
                                    stroke={isHovered ? "#22d3ee" : "#334155"}
                                    strokeWidth="0.8"
                                    strokeDasharray={isHovered ? "0" : "2"}
                                  />
                                  <circle
                                    cx={p.x}
                                    cy={p.y}
                                    r={isHovered ? 4.5 : 3}
                                    fill="#06b6d4"
                                    stroke="#0f172a"
                                    strokeWidth="1.5"
                                  />
                                </>
                              )}
                            </g>
                          );
                        })}
                      </svg>
                      
                      {/* Dates */}
                      <div className="flex justify-between items-center text-[8px] text-slate-500 font-mono mt-1 border-t border-slate-900/60 pt-1.5 px-12">
                        <span>{cotData[0]?.date}</span>
                        <span>{cotData[Math.floor(cotData.length / 2)]?.date}</span>
                        <span>{cotData[cotData.length - 1]?.date}</span>
                      </div>

                      {/* Tooltip */}
                      {hoveredCotIdx !== null && cotChart.points[hoveredCotIdx] && (
                        <div className="absolute top-2 right-4 bg-slate-950/95 border border-slate-850 rounded-lg p-2 shadow-lg font-mono text-[9px] backdrop-blur-md">
                          <span className="text-slate-500">기준일: {cotChart.points[hoveredCotIdx].date}</span>
                          <span className="text-slate-200 block font-bold mt-0.5">
                            순 투기 포지션:{" "}
                            <span className={cotChart.points[hoveredCotIdx].value >= 0 ? "text-cyan-400" : "text-rose-400"}>
                              {cotChart.points[hoveredCotIdx].value >= 0 ? "+" : ""}
                              {cotChart.points[hoveredCotIdx].value.toLocaleString()} 계약
                            </span>
                          </span>
                          <span className="text-slate-350 block mt-0.5">
                            미결제약정 (OI): {cotChart.points[hoveredCotIdx].oi.toLocaleString()} 계약
                          </span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                      <th className="py-2.5 px-3">발표 기준일</th>
                      <th className="py-2.5 px-3 text-right">미결제약정 (OI)</th>
                      <th className="py-2.5 px-3 text-right text-emerald-400">투기 매수 (Non-Comm Long)</th>
                      <th className="py-2.5 px-3 text-right text-rose-450">투기 매도 (Non-Comm Short)</th>
                      <th className="py-2.5 px-3 text-right text-cyan-400">투기 순 포지션 (Net)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 text-slate-300 font-medium">
                    {cotData.slice().reverse().map((c, idx) => {
                      const net = c.netPosition;
                      const isNetLong = net >= 0;
                      return (
                        <tr key={idx} className="hover:bg-slate-900/10 transition">
                          <td className="py-2.5 px-3 font-mono text-slate-400">{c.date}</td>
                          <td className="py-2.5 px-3 text-right font-mono">{c.openInterest.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-emerald-450">{c.noncommLong.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-rose-400">{c.noncommShort.toLocaleString()}</td>
                          <td className={`py-2.5 px-3 text-right font-mono font-bold ${isNetLong ? "text-cyan-400" : "text-rose-500"}`}>
                            {isNetLong ? "+" : ""}{net.toLocaleString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-550 text-xs">
              <AlertTriangle className="mx-auto text-amber-500 mb-2" size={24} />
              이 해외선물 자산({data.code})에 대한 CFTC COT 포지션 정보가 데이터베이스에 적재되어 있지 않습니다.
              <br />
              <span className="text-[10px] text-slate-650 block mt-1">
                (백엔드 파이프라인 `python -m app.pipelines.sync_cftc_cot_pipeline` 실행을 완료하면 노출됩니다)
              </span>
            </div>
          )}
        </div>
      ) : (
        /* 4. Multi-Year Financial Statements Table (for Stocks) */
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
      )}

    </div>
  );
};
