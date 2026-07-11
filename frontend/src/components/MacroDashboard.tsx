import React, { useState, useEffect } from "react";
import { Globe, Calendar, TrendingUp, Clock, Info, Filter, RefreshCw, AlertTriangle } from "lucide-react";

interface IndicatorPoint {
  date: string;
  value: number;
}

interface IndicatorsData {
  [key: string]: IndicatorPoint[];
}

interface CalendarEvent {
  event_date: string;
  event_time: string;
  country: string;
  event_name: string;
  impact: "HIGH" | "MEDIUM" | "LOW";
  actual: string | null;
  forecast: string | null;
  previous: string | null;
}

export const MacroDashboard: React.FC = () => {
  const [indicators, setIndicators] = useState<IndicatorsData>({});
  const [calendar, setCalendar] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedIndicator, setSelectedIndicator] = useState<string>("FEDFUNDS");
  const [calendarImpactFilter, setCalendarImpactFilter] = useState<"ALL" | "HIGH" | "MEDIUM" | "LOW">("ALL");
  const [calendarCountryFilter, setCalendarCountryFilter] = useState<string>("ALL");
  const [hoveredPointIdx, setHoveredPointIdx] = useState<number | null>(null);

  const fetchMacroData = async () => {
    try {
      // Fetch key macro indicators (last 120 observations)
      const indRes = await fetch("/api/macro/indicators?limit=120");
      if (indRes.ok) {
        const indData = await indRes.json();
        setIndicators(indData);
      }

      // Fetch economic calendar for upcoming 14 days
      const calRes = await fetch("/api/macro/calendar?days=14");
      if (calRes.ok) {
        const calData = await calRes.json();
        setCalendar(calData);
      }
    } catch (e) {
      console.error("Failed to fetch macroeconomic data:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMacroData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchMacroData();
  };

  // Derive 10Y-2Y Yield Spread dynamically
  const getYieldSpread = (): IndicatorPoint[] => {
    const us10y = indicators["US10Y"] || [];
    const us2y = indicators["US2Y"] || [];
    const us2yMap = new Map(us2y.map((item) => [item.date, item.value]));

    return us10y
      .map((item) => {
        const y2Val = us2yMap.get(item.date);
        if (y2Val !== undefined) {
          return {
            date: item.date,
            value: Number((item.value - y2Val).toFixed(3)),
          };
        }
        return null;
      })
      .filter((item): item is IndicatorPoint => item !== null);
  };

  // Get current active timeseries data to chart
  const getActiveSeries = (): { name: string; description: string; unit: string; data: IndicatorPoint[] } => {
    if (selectedIndicator === "SPREAD") {
      return {
        name: "장단기 금리차 (10Y-2Y)",
        description: "미 국채 10년물 금리에서 2년물 금리를 뺀 값. 일반적으로 마이너스(장단기 금리 역전) 발생 시 경기 침체의 전조로 해석됩니다.",
        unit: "%p",
        data: getYieldSpread(),
      };
    }

    const seriesMap: Record<string, { name: string; description: string; unit: string }> = {
      FEDFUNDS: {
        name: "미 연방기금 기준금리 (Fed Funds Rate)",
        description: "미국 중앙은행(Fed)의 정책 금리. 시중 유동성과 글로벌 금리의 기준 역할을 합니다.",
        unit: "%",
      },
      US10Y: {
        name: "미 국채 10년물 금리 (US 10-Year Bond Yield)",
        description: "글로벌 장기 금리의 벤치마크 역할을 하는 장기 국채 수익률입니다.",
        unit: "%",
      },
      US2Y: {
        name: "미 국채 2년물 금리 (US 2-Year Bond Yield)",
        description: "통화 정책 금리 전망에 민감하게 연동되는 단기 국채 수익률입니다.",
        unit: "%",
      },
      CPI: {
        name: "소비자 물가 지수 (CPI-U)",
        description: "소비자가 구입하는 상품 및 서비스의 평균 가격 변동을 나타내는 대표적인 물가 지표입니다.",
        unit: "Index (1982-1984=100)",
      },
      UNRATE: {
        name: "미국 실업률 (Unemployment Rate)",
        description: "미국 전체 경제 활동 인구 중 실업자의 비율을 나타내는 대표적인 고용 시장 지표입니다.",
        unit: "%",
      },
      GDP: {
        name: "미국 실질 GDP (Real GDP)",
        description: "물가 요인을 제거한 미국의 실질 경제 생산 총액 (분기별 연율화 데이터).",
        unit: "$ Billions",
      },
    };

    const details = seriesMap[selectedIndicator] || { name: "알 수 없는 지표", description: "", unit: "" };
    return {
      ...details,
      data: indicators[selectedIndicator] || [],
    };
  };

  const activeSeries = getActiveSeries();

  // Helper to format values
  const formatIndicatorValue = (val: number, unit: string) => {
    if (unit === "$ Billions") {
      return `$${(val / 1000).toFixed(2)}T`;
    }
    return `${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${unit}`;
  };

  // SVG Chart Computations
  const getChartParams = (data: IndicatorPoint[]) => {
    if (data.length === 0) return null;
    const values = data.map((d) => d.value);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const range = maxVal - minVal || 1.0;
    
    // Padding on top and bottom of the chart
    const max = maxVal + range * 0.1;
    const min = minVal - range * 0.1;
    const finalRange = max - min;

    const width = 600;
    const height = 240;
    const paddingLeft = 55;
    const paddingRight = 15;
    const paddingTop = 25;
    const paddingBottom = 35;

    const chartW = width - paddingLeft - paddingRight;
    const chartH = height - paddingTop - paddingBottom;

    const points = data.map((d, idx) => {
      const x = paddingLeft + (idx / (data.length - 1)) * chartW;
      const y = height - paddingBottom - ((d.value - min) / finalRange) * chartH;
      return { x, y, date: d.date, value: d.value };
    });

    // Zero-line Y coordinate if range spans across zero (like 10Y-2Y spread)
    let zeroY: number | null = null;
    if (min < 0 && max > 0) {
      zeroY = height - paddingBottom - ((0 - min) / finalRange) * chartH;
    }

    return { points, max, min, width, height, paddingLeft, paddingRight, paddingTop, paddingBottom, zeroY, chartW, chartH };
  };

  const chartParams = getChartParams(activeSeries.data);

  // Generate SVG Path
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

  // Unique list of countries for Calendar Filter
  const countries = ["ALL", ...Array.from(new Set(calendar.map((c) => c.country)))];

  // Filter economic calendar items
  const filteredCalendar = calendar.filter((item) => {
    const matchImpact = calendarImpactFilter === "ALL" || item.impact === calendarImpactFilter;
    const matchCountry = calendarCountryFilter === "ALL" || item.country === calendarCountryFilter;
    return matchImpact && matchCountry;
  });

  const getImpactBadgeColor = (impact: "HIGH" | "MEDIUM" | "LOW") => {
    switch (impact) {
      case "HIGH":
        return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      case "MEDIUM":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      case "LOW":
        return "bg-slate-800 text-slate-400 border border-slate-700/50";
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-12 rounded-2xl flex justify-center items-center">
        <span className="text-slate-400 text-xs font-semibold">거시경제 지표 및 발표 일정을 불러오고 있습니다...</span>
      </div>
    );
  }

  // Get current status summary values
  const getLatestIndicatorValue = (key: string) => {
    let series = indicators[key] || [];
    if (key === "SPREAD") {
      series = getYieldSpread();
    }
    if (series.length === 0) return "-";
    const latest = series[series.length - 1];
    return latest.value;
  };

  const getLatestIndicatorDate = (key: string) => {
    let series = indicators[key] || [];
    if (key === "SPREAD") {
      series = getYieldSpread();
    }
    if (series.length === 0) return "";
    const latest = series[series.length - 1];
    return latest.date;
  };

  return (
    <div className="space-y-6">
      
      {/* 1. Metric Indicators Quick Glance Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { key: "FEDFUNDS", label: "기준 금리", color: "text-rose-400 font-mono", unit: "%" },
          { key: "US10Y", label: "미 국채 10년", color: "text-amber-400 font-mono", unit: "%" },
          { key: "US2Y", label: "미 국채 2년", color: "text-slate-350 font-mono", unit: "%" },
          { key: "SPREAD", label: "장단기 금리차", color: "text-cyan-400 font-mono", unit: "%p" },
          { key: "CPI", label: "소비자 물가", color: "text-emerald-400 font-mono", unit: "" },
          { key: "UNRATE", label: "실업률", color: "text-indigo-400 font-mono", unit: "%" }
        ].map((item) => {
          const val = getLatestIndicatorValue(item.key);
          const date = getLatestIndicatorDate(item.key);
          const isSelected = selectedIndicator === item.key;
          return (
            <button
              key={item.key}
              onClick={() => {
                setSelectedIndicator(item.key);
                setHoveredPointIdx(null);
              }}
              className={`p-4 rounded-xl border text-left transition duration-200 hover:scale-[1.02] active:scale-95 cursor-pointer flex flex-col justify-between h-24 ${
                isSelected
                  ? "bg-cyan-500/10 border-cyan-500/35 shadow-md shadow-cyan-500/5"
                  : "bg-slate-900/30 backdrop-blur-xl border-slate-900 hover:border-slate-800"
              }`}
            >
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">{item.label}</span>
                <span className={`text-base font-extrabold ${item.color} mt-1 block`}>
                  {typeof val === "number" ? formatIndicatorValue(val, item.unit) : val}
                </span>
              </div>
              {date && (
                <span className="text-[8px] text-slate-500 font-mono block self-end">
                  {date}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Main Grid: Chart & Calendar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Chart Card */}
        <div className="lg:col-span-2 bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl flex flex-col justify-between">
          <div className="border-b border-slate-800 pb-4 mb-4">
            <div className="flex justify-between items-start gap-4">
              <div>
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <TrendingUp size={16} className="text-cyan-400" />
                  {activeSeries.name}
                </h3>
                <p className="text-[10px] text-slate-500 mt-1 leading-relaxed max-w-xl">
                  {activeSeries.description}
                </p>
              </div>
              <button
                onClick={handleRefresh}
                className="flex items-center justify-center p-1.5 bg-slate-950/60 hover:bg-slate-900 text-slate-400 hover:text-cyan-400 rounded-lg border border-slate-850 active:scale-95 transition cursor-pointer"
              >
                <RefreshCw size={12} className={refreshing ? "animate-spin text-cyan-400" : ""} />
              </button>
            </div>
          </div>

          {/* Interactive Chart Container */}
          <div className="relative w-full h-64 flex-1 my-2">
            {chartParams && activeSeries.data.length > 0 ? (
              <>
                <svg className="w-full h-full" viewBox={`0 0 ${chartParams.width} ${chartParams.height}`} preserveAspectRatio="none">
                  {/* Gradients */}
                  <defs>
                    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.18" />
                      <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Gridlines */}
                  {[0.2, 0.5, 0.8].map((ratio, idx) => {
                    const y = chartParams.paddingTop + ratio * chartParams.chartH;
                    return (
                      <line
                        key={idx}
                        x1={chartParams.paddingLeft}
                        y1={y}
                        x2={chartParams.width - chartParams.paddingRight}
                        y2={y}
                        stroke="#1e293b"
                        strokeWidth="0.5"
                        strokeDasharray="3"
                      />
                    );
                  })}

                  {/* Zero Line (if spread can go negative) */}
                  {chartParams.zeroY !== null && (
                    <line
                      x1={chartParams.paddingLeft}
                      y1={chartParams.zeroY}
                      x2={chartParams.width - chartParams.paddingRight}
                      y2={chartParams.zeroY}
                      stroke="#f43f5e"
                      strokeWidth="1"
                      strokeDasharray="5"
                    />
                  )}

                  {/* Chart Line Area */}
                  <path
                    d={getAreaPath(chartParams.points, chartParams.height, chartParams.paddingBottom)}
                    fill="url(#areaGrad)"
                  />

                  {/* Chart Line */}
                  <path
                    d={getLinePath(chartParams.points)}
                    fill="none"
                    stroke="#22d3ee"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Dynamic Y Axis Values */}
                  <text x={10} y={chartParams.paddingTop + 5} fill="#64748b" className="text-[9px] font-mono font-semibold">
                    {formatIndicatorValue(chartParams.max, activeSeries.unit)}
                  </text>
                  <text x={10} y={chartParams.paddingTop + chartParams.chartH / 2 + 3} fill="#64748b" className="text-[9px] font-mono font-semibold">
                    {formatIndicatorValue((chartParams.max + chartParams.min) / 2, activeSeries.unit)}
                  </text>
                  <text x={10} y={chartParams.height - chartParams.paddingBottom + 3} fill="#64748b" className="text-[9px] font-mono font-semibold">
                    {formatIndicatorValue(chartParams.min, activeSeries.unit)}
                  </text>

                  {/* Hover Interaction Dots */}
                  {chartParams.points.map((p, idx) => {
                    const isHovered = hoveredPointIdx === idx;
                    // Render interactive trigger columns for smoother mouse hover
                    const colW = chartParams.chartW / chartParams.points.length;
                    return (
                      <g key={idx}>
                        <rect
                          x={p.x - colW / 2}
                          y={chartParams.paddingTop}
                          width={colW}
                          height={chartParams.chartH}
                          fill="transparent"
                          className="cursor-pointer"
                          onMouseEnter={() => setHoveredPointIdx(idx)}
                          onMouseLeave={() => setHoveredPointIdx(null)}
                        />
                        {(isHovered || idx === chartParams.points.length - 1) && (
                          <>
                            {/* Vertical tracker line */}
                            <line
                              x1={p.x}
                              y1={chartParams.paddingTop}
                              x2={p.x}
                              y2={chartParams.height - chartParams.paddingBottom}
                              stroke={isHovered ? "#22d3ee" : "#334155"}
                              strokeWidth="0.8"
                              strokeDasharray={isHovered ? "0" : "2"}
                            />
                            {/* Dot */}
                            <circle
                              cx={p.x}
                              cy={p.y}
                              r={isHovered ? 5 : 3.5}
                              fill={isHovered ? "#06b6d4" : "#0891b2"}
                              stroke="#0f172a"
                              strokeWidth={isHovered ? 2.5 : 1.5}
                              className="transition-all duration-100"
                            />
                          </>
                        )}
                      </g>
                    );
                  })}
                </svg>

                {/* X Axis Dates Labels (First, Middle, Last) */}
                <div className="flex justify-between items-center text-[9px] text-slate-500 font-mono border-t border-slate-900 pt-2.5 px-12">
                  <span>{activeSeries.data[0]?.date}</span>
                  <span>{activeSeries.data[Math.floor(activeSeries.data.length / 2)]?.date}</span>
                  <span>{activeSeries.data[activeSeries.data.length - 1]?.date}</span>
                </div>

                {/* Hover Tooltip Overlay */}
                {hoveredPointIdx !== null && chartParams.points[hoveredPointIdx] && (
                  <div className="absolute top-2 right-4 bg-slate-950/90 border border-slate-800 rounded-lg p-2.5 shadow-xl backdrop-blur-md">
                    <span className="text-[9px] text-slate-500 font-mono block">지표 측정일: {chartParams.points[hoveredPointIdx].date}</span>
                    <span className="text-xs font-black text-slate-200 font-mono mt-0.5 block">
                      수치: {formatIndicatorValue(chartParams.points[hoveredPointIdx].value, activeSeries.unit)}
                    </span>
                  </div>
                )}
              </>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 text-xs">
                <AlertTriangle size={24} className="text-amber-500 mb-2" />
                적재된 시계열 데이터가 존재하지 않습니다.
              </div>
            )}
          </div>
        </div>

        {/* Economic Calendar Card */}
        <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-900 p-6 rounded-2xl flex flex-col h-[340px] lg:h-auto">
          <div className="border-b border-slate-800 pb-3 mb-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Calendar size={16} className="text-cyan-400" />
              글로벌 거시경제 주요 일정
            </h3>
            <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
              TradingView 발표 기준 향후 2주간 예정된 지표 일정 목록입니다.
            </p>
          </div>

          {/* Calendar Filters */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            {/* Impact Filter */}
            <div className="flex flex-col">
              <span className="text-[9px] text-slate-500 font-bold mb-1 flex items-center gap-1">
                <Filter size={8} /> 중요도 필터
              </span>
              <select
                value={calendarImpactFilter}
                onChange={(e) => setCalendarImpactFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 text-[10px] text-slate-350 rounded-lg px-2 py-1.5 focus:border-cyan-500/50 outline-none cursor-pointer font-bold"
              >
                <option value="ALL">전체 중요도</option>
                <option value="HIGH">HIGH (고영향)</option>
                <option value="MEDIUM">MEDIUM (중영향)</option>
                <option value="LOW">LOW (저영향)</option>
              </select>
            </div>

            {/* Country Filter */}
            <div className="flex flex-col">
              <span className="text-[9px] text-slate-500 font-bold mb-1 flex items-center gap-1">
                <Globe size={8} /> 국가 필터
              </span>
              <select
                value={calendarCountryFilter}
                onChange={(e) => setCalendarCountryFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-[10px] text-slate-350 rounded-lg px-2 py-1.5 focus:border-cyan-500/50 outline-none cursor-pointer font-bold"
              >
                <option value="ALL">전체 국가</option>
                {countries.filter(c => c !== "ALL").map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Economic Calendar List */}
          <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 max-h-80 lg:max-h-96 scrollbar-thin scrollbar-thumb-slate-850 scrollbar-track-transparent">
            {filteredCalendar.map((item, idx) => (
              <div
                key={idx}
                className="p-3 bg-slate-950/40 border border-slate-900 rounded-xl hover:border-slate-850 hover:bg-slate-950/70 transition flex flex-col gap-1.5"
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] text-cyan-400 font-mono font-semibold flex items-center gap-0.5">
                      <Clock size={8} /> {item.event_date} {item.event_time}
                    </span>
                    <span className="text-[9px] text-slate-400 bg-slate-850 px-1.5 py-0.2 rounded font-bold uppercase">
                      {item.country}
                    </span>
                  </div>
                  <span className={`px-1.5 py-0.2 rounded text-[7px] font-bold tracking-wider ${getImpactBadgeColor(item.impact)}`}>
                    {item.impact}
                  </span>
                </div>
                <h4 className="text-[10px] font-bold text-slate-200 leading-snug">
                  {item.event_name}
                </h4>
                
                {/* Details values */}
                <div className="grid grid-cols-3 gap-1 text-[8px] font-mono border-t border-slate-900/60 pt-1.5">
                  <div>
                    <span className="text-slate-550 block">실제값</span>
                    <span className="text-slate-300 font-semibold block">{item.actual || "-"}</span>
                  </div>
                  <div>
                    <span className="text-slate-550 block">예측값</span>
                    <span className="text-slate-350 font-semibold block">{item.forecast || "-"}</span>
                  </div>
                  <div>
                    <span className="text-slate-550 block">이전값</span>
                    <span className="text-slate-450 block">{item.previous || "-"}</span>
                  </div>
                </div>
              </div>
            ))}

            {filteredCalendar.length === 0 && (
              <div className="py-12 text-center text-slate-550 text-xs flex flex-col items-center justify-center gap-2">
                <Info size={16} />
                조건에 일치하는 발표 일정이 없습니다.
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
};
