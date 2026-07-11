import os
import sys
import argparse
import pandas as pd
import sqlite3
from datetime import datetime

# Add project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.clients.yahoo_collector import YahooCollector
from app.db.db import upsert_daily_prices, save_log, DB_PATH

TICKER_MAPPING = {
    "XAU_USDT": "GC=F",
    "CL_USDT": "CL=F",
    "NAS100_USDT": "NQ=F",
    "AAPL_USDT": "AAPL",
    "TSLA_USDT": "TSLA"
}

LOG_STRATEGY = "YAHOO_FUTURES_SYNC"

def log_message(message: str):
    print(message)
    try:
        save_log(LOG_STRATEGY, message)
    except Exception as e:
        print(f"Failed to save log to DB: {e}", file=sys.stderr)

def sync_yahoo_futures(days: int = 180) -> int:
    log_message(f"Starting Yahoo Futures Sync for last {days} days...")
    
    # 1. Fetch futures assets from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT stock_code, stock_name, market, sector FROM stocks WHERE market = 'FUTURES'")
        stocks_rows = cursor.fetchall()
        stock_meta = {r["stock_code"]: dict(r) for r in stocks_rows}
    except Exception as e:
        log_message(f"Failed to read stocks metadata: {e}")
        return 0
    finally:
        conn.close()
        
    collector = YahooCollector()
    range_str = f"{days}d"
    
    total_records = 0
    
    for code, yf_ticker in TICKER_MAPPING.items():
        if code not in stock_meta:
            log_message(f"Skipping {code}: Not registered in stocks master.")
            continue
            
        meta = stock_meta[code]
        log_message(f"Syncing {code} ({yf_ticker}) from Yahoo Finance...")
        
        try:
            candles = collector.fetch_daily_prices(yf_ticker, range_str=range_str)
            if not candles:
                log_message(f"No data returned for {code} ({yf_ticker})")
                continue
                
            rows_to_insert = []
            
            # Recompute price change and change rate sequentially
            for idx in range(len(candles)):
                curr = candles[idx]
                c = curr["close"]
                o = curr["open"]
                h = curr["high"]
                l = curr["low"]
                v = curr["volume"]
                
                if idx > 0:
                    prev_close = candles[idx - 1]["close"]
                    price_change = c - prev_close
                    change_rate = (price_change / prev_close) * 100 if prev_close > 0 else 0.0
                else:
                    price_change = c - o
                    change_rate = (price_change / o) * 100 if o > 0 else 0.0
                    
                listed_shares = 1000000
                market_cap = c * listed_shares
                
                rows_to_insert.append({
                    "trade_date": curr["trade_date"],
                    "stock_code": code,
                    "stock_name": meta["stock_name"],
                    "market": meta["market"],
                    "section": None,
                    "open_price": o,
                    "high_price": h,
                    "low_price": l,
                    "close_price": c,
                    "price_change": price_change,
                    "change_rate": change_rate,
                    "volume": v,
                    "trading_value": c * v,
                    "market_cap": market_cap,
                    "listed_shares": listed_shares
                })
                
            if rows_to_insert:
                df = pd.DataFrame(rows_to_insert)
                upserted = upsert_daily_prices(df)
                log_message(f"Successfully synced and upserted {upserted} records for {code}")
                total_records += upserted
                
        except Exception as e:
            log_message(f"Error syncing {code} ({yf_ticker}): {e}")
            
    log_message(f"Yahoo Futures Sync completed. Total records upserted: {total_records}")
    return total_records

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yahoo Futures daily price sync pipeline")
    parser.add_argument("--days", type=int, default=180, help="Number of days to sync")
    args = parser.parse_args()
    
    sync_yahoo_futures(days=args.days)
