import sys
import os
import argparse
import sqlite3
import pandas as pd
import numpy as np
import json

# Ensure backend root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.db import migrate_db
from app.strategies.undervalued_dividend_strategy import screen_undervalued_dividend_stocks
from app.strategies.opportunity_growth_strategy import screen_opportunity_growth_stocks
from app.strategies.sector_diversified_growth_strategy import screen_sector_diversified_growth_stocks

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "invest_platform.db"))

def run_stock_backtest(strategy_id: str):
    """
    Runs historical backtest for a stock strategy ('ud_dividend', 'op_growth', or 'sector_growth')
    using the historical prices and dividends in SQLite database.
    """
    if strategy_id not in ("ud_dividend", "op_growth", "sector_growth"):
        raise ValueError(f"Strategy '{strategy_id}' is not supported for stock backtesting.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        migrate_db(conn)

        # 1. Load dataframes
        stocks_df = pd.read_sql_query("SELECT * FROM stocks WHERE is_active = 1", conn)
        raw_financials = pd.read_sql_query("SELECT * FROM company_financials", conn)
        
        # Merge corp_name
        corp_names = stocks_df[["stock_code", "stock_name"]].rename(columns={"stock_name": "corp_name"})
        raw_financials = raw_financials.merge(corp_names, on="stock_code", how="left")
        
        # Prepare financial statements df
        financials_cols_to_drop = [
            "eps", "cash_dividend_yield", "cash_dividend_per_share", 
            "cash_dividend_total", "cash_dividend_payout_ratio"
        ]
        financials_df = raw_financials.drop(columns=financials_cols_to_drop, errors="ignore")
        
        # Prepare dividends df
        dividends_cols_to_keep = [
            "corp_code", "bsns_year", "eps", "cash_dividend_yield", 
            "cash_dividend_per_share", "cash_dividend_total", "cash_dividend_payout_ratio"
        ]
        dividends_df = raw_financials[dividends_cols_to_keep].copy()
        dividends_df["fiscal_year"] = dividends_df["bsns_year"].astype(str)
        dividends_df = dividends_df.drop(columns=["bsns_year"])
        
        # cash_dividend_per_eps_ratio
        dividends_df["eps"] = pd.to_numeric(dividends_df["eps"], errors="coerce")
        dividends_df["cash_dividend_per_share"] = pd.to_numeric(dividends_df["cash_dividend_per_share"], errors="coerce")
        dividends_df["cash_dividend_per_eps_ratio"] = (
            dividends_df["cash_dividend_per_share"] / dividends_df["eps"]
        ).fillna(0)

        # 2. Fetch all daily prices
        all_prices = pd.read_sql_query("SELECT trade_date, stock_code, close_price, market_cap FROM daily_prices", conn)
        if all_prices.empty:
            raise ValueError("No historical price data found in daily_prices.")

        # Get sorted list of unique trade dates for KRX stocks to avoid crypto/futures holidays
        krx_dates_df = pd.read_sql_query(
            "SELECT DISTINCT trade_date FROM daily_prices WHERE market IN ('KOSPI', 'KOSDAQ')", 
            conn
        )
        trade_dates = sorted(krx_dates_df["trade_date"].tolist())
        if not trade_dates:
            raise ValueError("No historical KRX price dates found in daily_prices.")
        
        # Identify monthly rebalancing dates (last trading day of each month)
        df_dates = pd.DataFrame({"trade_date": trade_dates})
        df_dates["ym"] = df_dates["trade_date"].astype(str).str[:6]
        rebalance_dates = df_dates.groupby("ym")["trade_date"].max().tolist()
        
        # 3. Simulate portfolio returns
        initial_capital = 100000000.0 # 100M KRW
        capital = initial_capital
        
        portfolio_history = []  # List of tuples: (date, value)
        benchmark_history = []  # List of tuples: (date, value)
        simulated_trades = []   # List of dicts representing transactions
        
        holdings = {}           # stock_code -> quantity
        holdings_entry_prices = {} # stock_code -> entry_price
        closed_trades_pnl = []  # List of closed trade PnL values
        
        market_val = 100.0      # Benchmark starts at 100
        prev_prices_dict = {}
        
        for i, r_date in enumerate(rebalance_dates):
            # Fetch prices as of current date
            prices_at_date = all_prices[all_prices["trade_date"] == r_date]
            prices_dict = dict(zip(prices_at_date["stock_code"], prices_at_date["close_price"]))
            
            # 1. Calculate current portfolio value (cash + market value of holdings)
            current_portfolio_value = capital
            for code, qty in list(holdings.items()):
                curr_p = prices_dict.get(code)
                if curr_p is None or curr_p <= 0:
                    curr_p = holdings_entry_prices.get(code, 0.0)
                current_portfolio_value += qty * curr_p
                
            # 2. Handle Benchmark (market average return)
            if i == 0:
                benchmark_history.append((r_date, market_val))
                prev_prices_dict = prices_dict
            else:
                # Average price change of stocks that exist in both months
                ratios = []
                for code, prev_p in prev_prices_dict.items():
                    curr_p = prices_dict.get(code)
                    if curr_p is not None and prev_p > 0:
                        ratios.append(curr_p / prev_p)
                if ratios:
                    market_val *= np.mean(ratios)
                benchmark_history.append((r_date, market_val))
                prev_prices_dict = prices_dict
                
            # 3. Determine new target portfolio
            # Filter daily prices to pass to the strategy screening
            prices_df_filtered = prices_at_date[["stock_code", "close_price", "market_cap"]].copy()
            prices_df_filtered = prices_df_filtered.merge(
                stocks_df[["stock_code", "stock_name", "market"]], on="stock_code", how="inner"
            )
            
            as_of_year = int(str(r_date)[:4])
            
            # Run the screening function
            if strategy_id == "ud_dividend":
                screened_df = screen_undervalued_dividend_stocks(
                    financial_statements=financials_df,
                    dividends=dividends_df,
                    daily_prices=prices_df_filtered,
                    stocks=stocks_df,
                    minimum_total_score=0.0,
                    as_of_year=as_of_year
                )
            elif strategy_id == "op_growth":
                screened_df = screen_opportunity_growth_stocks(
                    financial_statements=financials_df,
                    dividends=dividends_df,
                    daily_prices=prices_df_filtered,
                    stocks=stocks_df,
                    minimum_total_score=0.0,
                    as_of_year=as_of_year
                )
            else:
                # sector_growth
                screened_df = screen_sector_diversified_growth_stocks(
                    financial_statements=financials_df,
                    dividends=dividends_df,
                    daily_prices=prices_df_filtered,
                    stocks=stocks_df,
                    minimum_total_score=60.0,
                    as_of_year=as_of_year
                )
                
            # Select top 5 candidates
            target_codes = []
            target_names_dict = {}
            target_prices_dict = {}
            if not screened_df.empty and "is_candidate" in screened_df.columns:
                candidates = screened_df[screened_df["is_candidate"] == True]
                top_candidates = candidates.sort_values(by="total_score", ascending=False).head(5)
                if not top_candidates.empty:
                    target_codes = top_candidates["stock_code"].tolist()
                    target_names_dict = dict(zip(top_candidates["stock_code"], top_candidates["stock_name"]))
                    target_prices_dict = dict(zip(top_candidates["stock_code"], top_candidates["close_price"]))
            
            # If this is the last rebalancing date, we liquidate everything and finish
            if i == len(rebalance_dates) - 1:
                for code, qty in list(holdings.items()):
                    curr_p = prices_dict.get(code)
                    if curr_p is None or curr_p <= 0:
                        curr_p = holdings_entry_prices.get(code, 0.0)
                    pos_val = qty * curr_p
                    entry_p = holdings_entry_prices.get(code, curr_p)
                    trade_pnl = pos_val - (qty * entry_p)
                    closed_trades_pnl.append(trade_pnl)
                    
                    s_name_row = stocks_df[stocks_df["stock_code"] == code]
                    s_name = s_name_row["stock_name"].values[0] if not s_name_row.empty else code
                    
                    simulated_trades.append({
                        "date": f"{str(r_date)[:4]}-{str(r_date)[4:6]}-{str(r_date)[6:8]}",
                        "type": "SELL",
                        "symbol": code,
                        "name": s_name,
                        "price": float(curr_p),
                        "qty": float(qty),
                        "amount": float(pos_val)
                    })
                capital = current_portfolio_value
                holdings = {}
                holdings_entry_prices = {}
                portfolio_history.append((r_date, capital))
                break
                
            # 4. Perform Rebalancing
            new_holdings = {}
            new_holdings_entry_prices = {}
            
            # Liquidate exits (existing holdings NOT in target codes)
            for code, qty in list(holdings.items()):
                if code not in target_codes:
                    curr_p = prices_dict.get(code)
                    if curr_p is None or curr_p <= 0:
                        curr_p = holdings_entry_prices.get(code, 0.0)
                    pos_val = qty * curr_p
                    entry_p = holdings_entry_prices.get(code, curr_p)
                    trade_pnl = pos_val - (qty * entry_p)
                    closed_trades_pnl.append(trade_pnl)
                    
                    s_name_row = stocks_df[stocks_df["stock_code"] == code]
                    s_name = s_name_row["stock_name"].values[0] if not s_name_row.empty else code
                    
                    simulated_trades.append({
                        "date": f"{str(r_date)[:4]}-{str(r_date)[4:6]}-{str(r_date)[6:8]}",
                        "type": "SELL",
                        "symbol": code,
                        "name": s_name,
                        "price": float(curr_p),
                        "qty": float(qty),
                        "amount": float(pos_val)
                    })
            
            # === Full-liquidation rebalancing model ===
            # We assume all current holdings are liquidated at current prices (no slippage/fees),
            # then the total portfolio value is redistributed equally across 5 fixed slots (20% each).
            # If fewer than 5 stocks qualify, the remaining slots stay in cash.
            # NOTE: This is a simplified model — real-world execution would incur transaction costs.
            capital = current_portfolio_value
            target_val_per_stock = current_portfolio_value / 5
            
            # Allocate target value per stock
            num_targets = len(target_codes)
            if num_targets > 0:
                for code in target_codes:
                    close_p = target_prices_dict.get(code, 0.0)
                    name = target_names_dict.get(code, code)
                    if close_p > 0:
                        target_qty = target_val_per_stock / close_p
                        new_holdings[code] = target_qty
                        capital -= target_val_per_stock
                        
                        if code in holdings:
                            # Kept stock: silently update quantity, reuse original entry price
                            new_holdings_entry_prices[code] = holdings_entry_prices[code]
                        else:
                            # New entry: BUY transaction logged
                            new_holdings_entry_prices[code] = close_p
                            simulated_trades.append({
                                "date": f"{str(r_date)[:4]}-{str(r_date)[4:6]}-{str(r_date)[6:8]}",
                                "type": "BUY",
                                "symbol": code,
                                "name": name,
                                "price": float(close_p),
                                "qty": float(target_qty),
                                "amount": float(target_val_per_stock)
                            })
                            
            holdings = new_holdings
            holdings_entry_prices = new_holdings_entry_prices
            portfolio_history.append((r_date, current_portfolio_value))
            
        # 4. Calculate stats
        balances = [h[1] for h in portfolio_history]
        bench_vals = [h[1] for h in benchmark_history]
        
        # Cumulative return
        cum_return = ((balances[-1] - initial_capital) / initial_capital) * 100.0
        
        # Max Drawdown (MDD)
        peak = initial_capital
        mdd = 0.0
        for bal in balances:
            if bal > peak:
                peak = bal
            drawdown = (peak - bal) / peak * 100.0
            if drawdown > mdd:
                mdd = drawdown
                
        # Sharpe ratio
        monthly_returns = []
        for k in range(1, len(balances)):
            prev = balances[k-1]
            curr = balances[k]
            if prev > 0:
                monthly_returns.append((curr - prev) / prev)
                
        if monthly_returns:
            mean_ret = np.mean(monthly_returns)
            std_ret = np.std(monthly_returns)
            sharpe = (mean_ret / std_ret * np.sqrt(12)) if std_ret > 0 else 0.0
        else:
            sharpe = 0.0
            
        # Win Rate & Profit Factor
        if closed_trades_pnl:
            wins = [p for p in closed_trades_pnl if p > 0]
            losses = [p for p in closed_trades_pnl if p < 0]
            win_rate = (len(wins) / len(closed_trades_pnl)) * 100.0 if closed_trades_pnl else 50.0
            
            total_gains = sum(wins)
            total_losses = abs(sum(losses))
            profit_factor = (total_gains / total_losses) if total_losses > 0 else (total_gains if total_gains > 0 else 1.0)
            total_trades = len(closed_trades_pnl)
        else:
            win_rate = 50.0
            profit_factor = 1.0
            total_trades = 0
            
        # 5. Generate SVG path for strategy and benchmark
        all_vals = balances + bench_vals
        min_val = min(all_vals)
        max_val = max(all_vals)
        val_range = max_val - min_val if max_val > min_val else 1.0
        
        strat_points = []
        for idx, val in enumerate(balances):
            x = 10 + idx * (280 / (len(balances) - 1))
            y = 90 - ((val - min_val) / val_range * 80)
            strat_points.append(f"{x:.1f},{y:.1f}")
        chart_path = "M " + " L ".join(strat_points)
        
        bench_points = []
        for idx, val in enumerate(bench_vals):
            x = 10 + idx * (280 / (len(bench_vals) - 1))
            y = 90 - ((val - min_val) / val_range * 80)
            bench_points.append(f"{x:.1f},{y:.1f}")
        bench_path = "M " + " L ".join(bench_points)
        
        bench_return = bench_vals[-1] - 100.0
        
        # Save both paths and benchmark statistics to chart_path column as JSON
        chart_data_json = json.dumps({
            "strategy": chart_path,
            "benchmark": bench_path,
            "benchmark_return": round(bench_return, 1)
        }, ensure_ascii=False)
        
        # 6. Save back to DB (including simulated_trades JSON)
        simulated_trades_json = json.dumps(simulated_trades, ensure_ascii=False)
        
        cursor.execute("""
            INSERT OR REPLACE INTO strategy_backtests 
            (strategy_id, cum_return, mdd, sharpe, win_rate, profit_factor, total_trades, chart_path, simulated_trades, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (strategy_id, round(cum_return, 1), round(mdd, 1), round(sharpe, 2), round(win_rate, 1), round(profit_factor, 2), total_trades, chart_data_json, simulated_trades_json))
        conn.commit()

        stats = {
            "cumReturn": f"{cum_return:.1f}%",
            "mdd": f"-{mdd:.1f}%",
            "sharpe": f"{sharpe:.2f}",
            "winRate": f"{int(win_rate)}%",
            "profitFactor": f"{profit_factor:.2f}",
            "totalTrades": str(total_trades),
            "chartPath": chart_path,
            "benchmarkChartPath": bench_path,
            "benchmarkReturn": f"{bench_return:.1f}%",
            "simulatedTrades": simulated_trades
        }
        return stats

    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run stock quant strategy backtester.")
    parser.add_argument("--strategy", type=str, required=True, choices=["ud_dividend", "op_growth", "sector_growth"],
                        help="Strategy ID to backtest")
    args = parser.parse_args()

    print(f"[CLI] Running backtest for: {args.strategy}")
    try:
        results = run_stock_backtest(args.strategy)
        print("\n=== Backtest Success ===")
        print(f"Cumulative Return: {results['cumReturn']}")
        print(f"MDD:               {results['mdd']}")
        print(f"Sharpe Ratio:      {results['sharpe']}")
        print(f"Win Rate:          {results['winRate']}")
        print(f"Profit Factor:     {results['profitFactor']}")
        print(f"Total Trades:      {results['totalTrades']}")
        print(f"Simulated Trades:  {len(results['simulatedTrades'])} events logged.")
    except Exception as err:
        print(f"[CLI Error] Backtest failed: {err}")
        sys.exit(1)
