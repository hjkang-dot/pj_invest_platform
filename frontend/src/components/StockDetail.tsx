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
  
  // 마우스 휠 줌 및 드래그 패닝을 위한 상태
  const [visibleCount, setVisibleCount] = React.useState<number>(60); // 기본 60일치 노출
  const [endIdx, setEndIdx] = React.useState<number | null>(null);
  const [isDragging, setIsDragging] = React.useState(false);
  const [dragStartX, setDragStartX] = React.useState(0);
  const [dragStartEndIdx, setDragStartEndIdx] = React.useState(0);
  
  const chartContainerRef = React.useRef<HTMLDivElement>(null);

  const [cotData, setCotData] = React.useState<any[]>([]);
  const [cotLoading, setCotLoading] = React.useState(false);
  const [hoveredCotIdx, setHoveredCotIdx] = React.useState<number | null>(null);

  // 차트 호버 툴팁용 상태 추가
  const [hoveredCandle, setHoveredCandle] = React.useState<PricePoint | null>(null);
  const [hoveredX, setHoveredX] = React.useState<number | null>(null);

  const isUsd = data ? (data.market === "COIN" || data.market === "FUTURES" || data.code.includes("_USDT")) : false;

  useEffect(() => {
    const fetchStockDetail = async () => {
      try {
        const res = await fetch(`/api/stocks/${stockCode}`);
        if (res.ok) {
          const detail = await res.json();
          setData(detail);
          setEndIdx(detail.priceHistory.length);
        }
      } catch (e) {
        console.error("Failed to fetch stock detail:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchStockDetail();
  }, [stockCode]);

  // 마우스 휠 줌 리스너 바인딩 (e.preventDefault 작동을 보장하기 위해 native 리스너 사용)
  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container || !data || data.priceHistory.length === 0) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY;
      
      setVisibleCount((prev) => {
        const step = Math.max(1, Math.round(prev * 0.08)); // 현재 보이는 개수의 8% 줌 강도
        const next = prev + (delta > 0 ? step : -step);
        return Math.max(10, Math.min(next, data.priceHistory.length));
      });
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      container.removeEventListener("wheel", handleWheel);
    };
  }, [data, visibleCount]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!data || data.priceHistory.length === 0) return;
    setIsDragging(true);
    setDragStartX(e.clientX);
    const currentEndIdx = endIdx !== null ? endIdx : data.priceHistory.length;
    setDragStartEndIdx(currentEndIdx);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !data || data.priceHistory.length === 0) return;
    const deltaX = e.clientX - dragStartX;
    const candleWidth = 540 / visibleCount;
    const shift = Math.round(deltaX / candleWidth);
    
    if (shift !== 0) {
      const targetEndIdx = dragStartEndIdx - shift;
      const minEndIdx = visibleCount;
      const maxEndIdx = data.priceHistory.length;
      setEndIdx(Math.max(minEndIdx, Math.min(targetEndIdx, maxEndIdx)));
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (!data || data.market !== "FUTURES") {
      setCotData([]);
      return;
    }
    const fetchCot = async () => {
      setCotLoading(true);
      try {
        const res = await fetch(`/api/futures/cot?symbol=${stockCode}`);
        if (res.ok) {
          const detail = await res.json();
          setCotData(detail);
        }
      } catch (e) {
        console.error("Failed to fetch COT:", e);
      } finally {
        setCotLoading(false);
      }
    };
    fetchCot();
  }, [stockCode, data]);

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


  const formatFinancialValue = (val: number | null, unit = "억 원") => {
    if (val === null || isNaN(val)) return "-";
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

  // Compute candle chart parameters for the selected timeframe / zoom count
  const getCandleChartData = () => {
    if (!data || data.priceHistory.length === 0) return null;
    
    const currentEndIdx = endIdx !== null ? endIdx : data.priceHistory.length;
    const startIdx = Math.max(0, currentEndIdx - visibleCount);
    const visiblePrices = data.priceHistory.slice(startIdx, currentEndIdx);
    
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

  // Compute COT Net position points for rendering
  const getCotChartData = () => {
    if (cotData.length === 0) return null;
    
    const netPositions = cotData.map(c => c.net_position);
    const max = Math.max(...netPositions);
    const min = Math.min(...netPositions);
    const range = max - min || 1;
    
    const width = 600;
    const height = 200;
    const paddingLeft = 50;
    const paddingRight = 10;
    const paddingTop = 20;
    const paddingBottom = 20;
    const chartW = width - paddingLeft - paddingRight;
    const chartH = height - paddingTop - paddingBottom;
    
    const count = cotData.length;
    const stepX = chartW / (count - 1 || 1);
    
    const points = cotData.map((c, idx) => {
      const x = paddingLeft + idx * stepX;
      const y = height - paddingBottom - ((c.net_position - min) / range) * chartH;
      return { x, y };
    });
    
    // Find where net position = 0 intersects on Y axis
    let zeroY = null;
    if (max > 0 && min < 0) {
      zeroY = height - paddingBottom - ((0 - min) / range) * chartH;
    }
    
    return { points, max, min, zeroY, width, height, paddingLeft, paddingRight, paddingTop, paddingBottom };
  };

  const cotChart = getCotChartData();

  const getLinePath = (points: { x: number; y: number }[]) => {
    if (points.length === 0) return "";
    return "M " + points.map(p => `${p.x} ${p.y}`).join(" L ");
  };

  const getAreaPath = (points: { x: number; y: number }[], height: number, paddingBottom: number) => {
    if (points.length === 0) return "";
    const linePath = getLinePath(points);
    const first = points[0];
    const last = points[points.length - 1];
    const baseHeight = height - paddingBottom;
    return `${linePath} L ${last.x} ${baseHeight} L ${first.x} ${baseHeight} Z`;
  };

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
              className="flex items-center gap-1.5 text-xs text-slate-355 hover:text-cyan-400 bg-slate-950/60 hover:bg-cyan-500/10 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-cyan-500/30 transition cursor-pointer"
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

      {/* Grid: Price Card, Candle Chart, KPIs */}
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
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2.5 border-b border-slate-900/80 pb-3">
            <div className="flex items-center gap-2">
              <BarChart3 size={16} className="text-cyan-400" />
              <div>
                <h3 className="text-xs font-bold text-slate-300">주가 흐름 (캔들 차트)</h3>
                <p className="text-[10px] text-slate-500 font-medium">최고 {formatPrice(chart?.max || 0)} / 최저 {formatPrice(chart?.min || 0)}</p>
              </div>
            </div>
            
            {/* Timeframe Select Tabs */}
            <div className="flex bg-slate-950/60 p-0.5 rounded-lg border border-slate-855 self-start sm:self-auto">
              {([10, 30, 60, 120] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setVisibleCount(t);
                    if (data) {
                      setEndIdx(data.priceHistory.length);
                    }
                  }}
                  className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all cursor-pointer ${
                    visibleCount === t
                      ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/10 shadow-sm"
                      : "text-slate-500 hover:text-slate-300 border border-transparent"
                  }`}
                >
                  {t}일
                </button>
              ))}
            </div>
          </div>

          {/* Dynamic OHLCV Info Bar (Hover details dashboard) */}
          {(() => {
            const activeCandle = chart && chart.visiblePrices.length > 0 ? chart.visiblePrices[chart.visiblePrices.length - 1] : null;
            const currentCandle = hoveredCandle || activeCandle;
            return (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] sm:text-[11px] font-semibold bg-slate-950/40 border border-slate-900/60 px-3 py-1.5 rounded-xl mb-3 shadow-inner">
                <span className="text-slate-500">
                  일자: <span className="text-slate-300 font-mono font-bold">{currentCandle ? `${currentCandle.date.slice(0,4)}-${currentCandle.date.slice(4,6)}-${currentCandle.date.slice(6,8)}` : "-"}</span>
                </span>
                <span className="text-slate-500">
                  시가(O): <span className="text-slate-300 font-mono font-bold">{currentCandle ? formatPrice(currentCandle.openPrice) : "-"}</span>
                </span>
                <span className="text-slate-500">
                  고가(H): <span className="text-emerald-400 font-mono font-bold">{currentCandle ? formatPrice(currentCandle.highPrice) : "-"}</span>
                </span>
                <span className="text-slate-500">
                  저가(L): <span className="text-rose-400 font-mono font-bold">{currentCandle ? formatPrice(currentCandle.lowPrice) : "-"}</span>
                </span>
                <span className="text-slate-500">
                  종가(C): <span className="text-slate-300 font-mono font-bold">{currentCandle ? formatPrice(currentCandle.closePrice) : "-"}</span>
                </span>
                <span className="text-slate-500">
                  거래량(V): <span className="text-slate-300 font-mono font-bold">{currentCandle ? currentCandle.volume.toLocaleString() : "-"}</span>
                </span>
              </div>
            );
          })()}

          <div 
            ref={chartContainerRef}
            className="w-full h-44 my-1 relative select-none cursor-ew-resize"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => {
              handleMouseLeave();
              setHoveredCandle(null);
              setHoveredX(null);
            }}
          >
            {chart && (
              <svg 
                className="w-full h-full" 
                viewBox="0 0 600 200" 
                preserveAspectRatio="none"
                onMouseLeave={() => {
                  setHoveredCandle(null);
                  setHoveredX(null);
                }}
              >
                {/* Horizontal Grid Lines */}
                <line x1="40" y1="20" x2="590" y2="20" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                <line x1="40" y1="100" x2="590" y2="100" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                <line x1="40" y1="180" x2="590" y2="180" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3" />
                
                {/* Price labels on Y axis (left side) */}
                <text x="5" y="24" fill="#64748b" className="text-[9px] font-mono">{Math.round(chart.max).toLocaleString()}</text>
                <text x="5" y="104" fill="#64748b" className="text-[9px] font-mono">{Math.round((chart.max + chart.min) / 2).toLocaleString()}</text>
                <text x="5" y="184" fill="#64748b" className="text-[9px] font-mono">{Math.round(chart.min).toLocaleString()}</text>

                {/* Vertical Crosshair Guideline */}
                {hoveredX !== null && (
                  <line
                    x1={hoveredX}
                    y1={10}
                    x2={hoveredX}
                    y2={190}
                    stroke="rgba(6, 182, 212, 0.45)"
                    strokeWidth="1.2"
                    strokeDasharray="2"
                    pointerEvents="none"
                  />
                )}

                {/* Volume & Candles */}
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

                  const maxVolume = Math.max(...chart.visiblePrices.map(p => p.volume || 0)) || 1;

                  return (
                    <>
                      {/* Volume Bars (Background) */}
                      {chart.visiblePrices.map((p, idx) => {
                        const x = paddingLeft + idx * candleWidth + candleWidth / 2;
                        const isUpCandle = (p.closePrice || 0) >= (p.openPrice || 0);
                        const rectW = Math.max(candleWidth - (count > 60 ? 1 : 2), 1.5);
                        const volumeHeight = ((p.volume || 0) / maxVolume) * 45; // Max height 45px
                        const y = height - paddingBottom - volumeHeight;
                        const color = isUpCandle ? "rgba(16, 185, 129, 0.16)" : "rgba(244, 63, 94, 0.16)";
                        
                        return (
                          <rect
                            key={`vol-${idx}`}
                            x={x - rectW / 2}
                            y={y}
                            width={rectW}
                            height={Math.max(volumeHeight, 1)}
                            fill={color}
                          />
                        );
                      })}

                      {/* Candles (Foreground) */}
                      {chart.visiblePrices.map((p, idx) => {
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
                          <g key={idx}>
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
                            {/* Invisible wide hover zone for mouse events */}
                            <rect
                              x={x - candleWidth / 2}
                              y={10}
                              width={candleWidth}
                              height={180}
                              fill="transparent"
                              className="cursor-crosshair"
                              onMouseEnter={() => {
                                setHoveredCandle(p);
                                setHoveredX(x);
                              }}
                              onMouseMove={() => {
                                setHoveredCandle(p);
                                setHoveredX(x);
                              }}
                            />
                          </g>
                        );
                      })}
                    </>
                  );
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
            <span className="text-[8px] text-slate-600 font-sans font-medium">※ DB 내 희소 주가 데이터 적재(총 97개 일자)로 인해 조회 달력이 넓게 노출됩니다.</span>
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

                        {/* Hover Guides & Points */}
                        {cotChart.points.map((pt, idx) => {
                          const isHovered = hoveredCotIdx === idx;
                          return (
                            <g key={idx}>
                              <circle
                                cx={pt.x}
                                cy={pt.y}
                                r={isHovered ? 4 : 2}
                                fill={isHovered ? "#22d3ee" : "#0891b2"}
                                stroke="#0f172a"
                                strokeWidth={isHovered ? 1.5 : 1}
                                className="transition-all duration-150"
                              />
                              <rect
                                x={pt.x - 10}
                                y={cotChart.paddingTop}
                                width={20}
                                height={cotChart.height - cotChart.paddingTop - cotChart.paddingBottom}
                                fill="transparent"
                                className="cursor-crosshair"
                                onMouseEnter={() => setHoveredCotIdx(idx)}
                                onMouseLeave={() => setHoveredCotIdx(null)}
                              />
                            </g>
                          );
                        })}
                      </svg>

                      {/* Floating COT Tooltip */}
                      {hoveredCotIdx !== null && cotData[hoveredCotIdx] && (
                        <div className="absolute top-2 left-12 bg-slate-900/95 border border-cyan-500/30 px-3 py-2 rounded-xl text-[10px] space-y-1 pointer-events-none shadow-xl backdrop-blur-md">
                          <div className="font-bold text-slate-200">일자: {cotData[hoveredCotIdx].date}</div>
                          <div className="text-cyan-400 font-black">
                            비상업용 순 포지션: {cotData[hoveredCotIdx].net_position.toLocaleString()} 계약
                          </div>
                          <div className="text-slate-400">
                            매수: {cotData[hoveredCotIdx].long_position.toLocaleString()} | 매도: {cotData[hoveredCotIdx].short_position.toLocaleString()}
                          </div>
                          <div className="text-slate-500">
                            미결제약정 (OI): {cotData[hoveredCotIdx].open_interest.toLocaleString()}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
                <div className="flex justify-between text-[8px] text-slate-500 font-mono mt-1 border-t border-slate-900/60 pt-2">
                  <span>{cotData[0]?.date || ""}</span>
                  <span>{cotData[Math.floor(cotData.length / 2)]?.date || ""}</span>
                  <span>최신 ({cotData[cotData.length - 1]?.date || ""})</span>
                </div>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-[10px]">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                      <th className="py-2 px-3">발표 일자</th>
                      <th className="py-2 px-3 text-right">투기 순 포지션</th>
                      <th className="py-2 px-3 text-right">투기 매수 (Long)</th>
                      <th className="py-2 px-3 text-right">투기 매도 (Short)</th>
                      <th className="py-2 px-3 text-right">미결제약정 (OI)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 text-slate-300 font-medium font-mono">
                    {cotData.slice().reverse().slice(0, 5).map((row, idx) => {
                      const isNetLong = row.net_position >= 0;
                      return (
                        <tr key={idx} className="hover:bg-slate-800/10">
                          <td className="py-2 px-3">{row.date}</td>
                          <td className={`py-2 px-3 text-right font-bold ${isNetLong ? "text-cyan-400" : "text-rose-400"}`}>
                            {isNetLong ? "+" : ""}{row.net_position.toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-right">{row.long_position.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right">{row.short_position.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-slate-400">{row.open_interest.toLocaleString()}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-600 text-xs font-semibold">
              이 자산에 대한 CFTC COT 주간 배치 수집 기록이 존재하지 않습니다.
            </div>
          )}
        </div>
      ) : (
        /* 4. Financial Statements & Dividends Grid (for Stocks) */
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl space-y-6">
          <h3 className="text-xs font-bold text-slate-200 border-b border-slate-800 pb-3 flex items-center gap-2">
            <Landmark size={14} className="text-cyan-400" />
            연간 기업 재무제표 및 배당 분석 로그
          </h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[10px]">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                  <th className="py-2 px-3">연도.월 (기간)</th>
                  <th className="py-2 px-3 text-right">매출액</th>
                  <th className="py-2 px-3 text-right">영업이익 (이익률)</th>
                  <th className="py-2 px-3 text-right">당기순이익 (순이익률)</th>
                  <th className="py-2 px-3 text-right">부채비율 (유동비율)</th>
                  <th className="py-2 px-3 text-right font-bold text-slate-350">ROE</th>
                  <th className="py-2 px-3 text-right">EPS</th>
                  <th className="py-2 px-3 text-right text-cyan-400">주당 배당금 (수익률)</th>
                  <th className="py-2 px-3 text-right text-cyan-400">배당성향</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-slate-300 font-medium font-mono">
                {data.financials.map((f, idx) => {
                  const opMargin = f.operatingIncome && f.revenue ? (f.operatingIncome / f.revenue) * 100 : null;
                  const netMargin = f.netIncome && f.revenue ? (f.netIncome / f.revenue) * 100 : null;
                  return (
                    <tr key={idx} className="hover:bg-slate-800/10">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">{f.period}</td>
                      <td className="py-2.5 px-3 text-right">{formatFinancialValue(f.revenue)}</td>
                      <td className="py-2.5 px-3 text-right">
                        {formatFinancialValue(f.operatingIncome)}
                        <span className="text-[9px] text-slate-500 block font-normal">({formatPercent(opMargin)})</span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {formatFinancialValue(f.netIncome)}
                        <span className="text-[9px] text-slate-500 block font-normal">({formatPercent(netMargin)})</span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {formatPercent(f.debtRatio)}
                        <span className="text-[9px] text-slate-500 block font-normal">({formatPercent(f.currentRatio)})</span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-200">{formatPercent(f.roe)}</td>
                      <td className="py-2.5 px-3 text-right">{f.eps ? `${Math.round(f.eps).toLocaleString()} 원` : "-"}</td>
                      <td className="py-2.5 px-3 text-right text-cyan-400 font-bold">
                        {formatDPS(f.dividendPerShare)}
                        <span className="text-[9px] text-cyan-500/80 block font-normal">({formatPercent(f.dividendYield)})</span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-cyan-400">{formatPercent(f.payoutRatio)}</td>
                    </tr>
                  );
                })}
                {data.financials.length === 0 && (
                  <tr>
                    <td colSpan={9} className="py-12 text-center text-slate-500 font-semibold">
                      DART 공시 시스템에 등록된 기업 재무제표 및 배당 이력 정보가 없습니다.
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
