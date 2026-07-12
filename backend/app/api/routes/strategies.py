from fastapi import APIRouter, HTTPException

from app.database import get_db

router = APIRouter()

@router.get("/api/strategies/{strategy_id}")
def get_strategy_detail_api(strategy_id: str):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch backtest statistics from strategy_backtests table
        cursor.execute("""
            SELECT cum_return, mdd, sharpe, win_rate, profit_factor, total_trades, chart_path, simulated_trades
            FROM strategy_backtests
            WHERE strategy_id = ? LIMIT 1
        """, (strategy_id,))
        backtest_row = cursor.fetchone()
        
        metrics = {}
        chart_path = ""
        benchmark_chart_path = ""
        benchmark_return = ""
        simulated_trades = []
        
        if backtest_row:
            metrics = {
                "cumReturn": f"{backtest_row['cum_return']:.1f}%",
                "mdd": f"-{backtest_row['mdd']:.1f}%",
                "sharpe": f"{backtest_row['sharpe']:.2f}",
                "winRate": f"{int(backtest_row['win_rate'])}%",
                "profitFactor": f"{backtest_row['profit_factor']:.2f}",
                "totalTrades": str(backtest_row["total_trades"])
            }
            raw_chart = backtest_row["chart_path"]
            import json
            if raw_chart and raw_chart.startswith("{"):
                try:
                    c_data = json.loads(raw_chart)
                    chart_path = c_data.get("strategy", "")
                    benchmark_chart_path = c_data.get("benchmark", "")
                    benchmark_return = f"{c_data.get('benchmark_return', 0.0):.1f}%"
                except Exception:
                    chart_path = raw_chart
            else:
                chart_path = raw_chart
                
            try:
                simulated_trades = json.loads(backtest_row["simulated_trades"]) if backtest_row["simulated_trades"] else []
            except Exception:
                simulated_trades = []
        else:
            metrics = {
                "cumReturn": "0.0%",
                "mdd": "0.0%",
                "sharpe": "0.00",
                "winRate": "0%",
                "profitFactor": "0.00",
                "totalTrades": "0"
            }
            chart_path = ""
            simulated_trades = []

        # KOSPI/KOSDAQ 주식 관련 스크리닝인 경우
        if strategy_id in ("ud_dividend", "op_growth", "sector_growth"):
            import pandas as pd
            
            # DB 로드
            stocks_df = pd.read_sql_query("SELECT * FROM stocks WHERE is_active = 1", conn)
            raw_financials = pd.read_sql_query("SELECT * FROM company_financials", conn)
            
            # corp_name 조인
            corp_names = stocks_df[["stock_code", "stock_name"]].rename(columns={"stock_name": "corp_name"})
            raw_financials = raw_financials.merge(corp_names, on="stock_code", how="left")
            
            # 중복 컬럼 분리
            financials_cols_to_drop = [
                "eps", "cash_dividend_yield", "cash_dividend_per_share", 
                "cash_dividend_total", "cash_dividend_payout_ratio"
            ]
            financials_df = raw_financials.drop(columns=financials_cols_to_drop, errors="ignore")
            
            dividends_cols_to_keep = [
                "corp_code", "bsns_year", "eps", "cash_dividend_yield", 
                "cash_dividend_per_share", "cash_dividend_total", "cash_dividend_payout_ratio"
            ]
            dividends_df = raw_financials[dividends_cols_to_keep].copy()
            dividends_df["fiscal_year"] = dividends_df["bsns_year"].astype(str)
            dividends_df = dividends_df.drop(columns=["bsns_year"])
            
            # cash_dividend_per_eps_ratio 계산
            dividends_df["eps"] = pd.to_numeric(dividends_df["eps"], errors="coerce")
            dividends_df["cash_dividend_per_share"] = pd.to_numeric(dividends_df["cash_dividend_per_share"], errors="coerce")
            dividends_df["cash_dividend_per_eps_ratio"] = (
                dividends_df["cash_dividend_per_share"] / dividends_df["eps"]
            ).fillna(0)
            
            # 최신 가격
            query = """
                SELECT dp.* FROM daily_prices dp
                INNER JOIN (
                    SELECT stock_code, MAX(trade_date) as max_date
                    FROM daily_prices
                    GROUP BY stock_code
                ) latest ON dp.stock_code = latest.stock_code AND dp.trade_date = latest.max_date
            """
            daily_prices_df = pd.read_sql_query(query, conn)
            
            positions = []
            
            if strategy_id == "ud_dividend":
                from app.strategies.undervalued_dividend_strategy import screen_undervalued_dividend_stocks
                res = screen_undervalued_dividend_stocks(
                    financial_statements=financials_df,
                    dividends=dividends_df,
                    daily_prices=daily_prices_df,
                    stocks=stocks_df,
                    minimum_total_score=0.0
                )
                if not res.empty:
                    candidates = res[res["is_candidate"] == True]
                    top = candidates.sort_values(by="total_score", ascending=False).head(10)
                    for _, r in top.iterrows():
                        pbr_val = f"PBR: {r['pbr']:.2f}" if pd.notna(r.get('pbr')) else "-"
                        yield_val = f"{r['dividend_yield']:.2f}%" if pd.notna(r.get('dividend_yield')) else "0.0%"
                        payout_val = f"{r['payout_ratio']:.1f}%" if pd.notna(r.get('payout_ratio')) else "0.0%"
                        close_price_formatted = f"{int(r['close_price']):,}" if pd.notna(r.get('close_price')) else "-"
                        
                        positions.append({
                            "name": str(r["stock_name"]),
                            "code": str(r["stock_code"]),
                            "qty": f"{int(r['total_score'])}점",
                            "entryPrice": pbr_val,
                            "currentPrice": close_price_formatted,
                            "pnl": f"배당수익률: {yield_val}",
                            "pnlPct": f"성향: {payout_val}"
                        })
            elif strategy_id == "op_growth":
                # op_growth
                from app.strategies.opportunity_growth_strategy import screen_opportunity_growth_stocks
                res = screen_opportunity_growth_stocks(
                    financial_statements=financials_df,
                    dividends=dividends_df,
                    daily_prices=daily_prices_df,
                    stocks=stocks_df,
                    minimum_total_score=0.0
                )
                if not res.empty:
                    candidates = res[res["is_candidate"] == True]
                    top = candidates.sort_values(by="total_score", ascending=False).head(10)
                    for _, r in top.iterrows():
                        roe_val = f"ROE: {r['roe']:.1f}%" if pd.notna(r.get('roe')) else "-"
                        per_val = f"PER: {r['per']:.1f}" if pd.notna(r.get('per')) else "-"
                        close_price_formatted = f"{int(r['close_price']):,}" if pd.notna(r.get('close_price')) else "-"
                        
                        positions.append({
                            "name": str(r["stock_name"]),
                            "code": str(r["stock_code"]),
                            "qty": f"{int(r['total_score'])}점",
                            "entryPrice": roe_val,
                            "currentPrice": close_price_formatted,
                            "pnl": per_val,
                            "pnlPct": f"성장성: {r.get('growth_score', 0):.0f}점"
                        })
            else:
                # sector_growth
                from app.strategies.sector_diversified_growth_strategy import screen_sector_diversified_growth_stocks
                res = screen_sector_diversified_growth_stocks(
                    financial_statements=financials_df,
                    dividends=dividends_df,
                    daily_prices=daily_prices_df,
                    stocks=stocks_df,
                    minimum_total_score=60.0
                )
                if not res.empty:
                    candidates = res[res["is_candidate"] == True]
                    top = candidates.sort_values(by="total_score", ascending=False).head(10)
                    for _, r in top.iterrows():
                        roe_val = f"ROE: {r['roe']:.1f}%" if pd.notna(r.get('roe')) else "-"
                        per_val = f"PER: {r['per']:.1f}" if pd.notna(r.get('per')) else "-"
                        close_price_formatted = f"{int(r['close_price']):,}" if pd.notna(r.get('close_price')) else "-"
                        
                        positions.append({
                            "name": str(r["stock_name"]),
                            "code": str(r["stock_code"]),
                            "qty": f"{int(r['total_score'])}점",
                            "entryPrice": roe_val,
                            "currentPrice": close_price_formatted,
                            "pnl": per_val,
                            "pnlPct": f"성장성: {r.get('growth_score', 0):.0f}점"
                        })
            return {
                "strategyId": strategy_id, 
                "positions": positions, 
                "metrics": metrics, 
                "chartPath": chart_path, 
                "benchmarkChartPath": benchmark_chart_path,
                "benchmarkReturn": benchmark_return,
                "simulatedTrades": simulated_trades
            }
        else:
            # 기타 자산배분/원자재/가상자산 전략
            return {
                "strategyId": strategy_id, 
                "positions": [], 
                "metrics": metrics, 
                "chartPath": chart_path, 
                "benchmarkChartPath": benchmark_chart_path,
                "benchmarkReturn": benchmark_return,
                "simulatedTrades": []
            }
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/api/strategies/{strategy_id}/backtest")
def run_strategy_backtest_api(strategy_id: str):
    if strategy_id not in ("ud_dividend", "op_growth", "sector_growth"):
        raise HTTPException(status_code=400, detail="This strategy does not support dynamic backtesting.")
    try:
        from app.strategies.stock_backtester import run_stock_backtest
        results = run_stock_backtest(strategy_id)
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
