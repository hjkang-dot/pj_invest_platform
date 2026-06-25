import os
import sys
import argparse
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Tuple

# App modules
from app.clients.krx_collector import fetch_daily_prices, Market
from app.cleaners.krx_price_cleaner import clean_daily_prices
from app.db.db import (
    upsert_daily_prices,
    get_existing_trade_dates,
    get_closed_market_dates,
    insert_closed_market_date,
    save_log
)

MARKETS: Tuple[Market, ...] = ("KOSPI", "KOSDAQ")
LOG_STRATEGY = "KRX_PRICE_SYNC"

def log_message(message: str):
    """Print to console and save to SQLite logs table."""
    print(message)
    try:
        save_log(LOG_STRATEGY, message)
    except Exception as e:
        print(f"Failed to save log to DB: {e}", file=sys.stderr)

def sync_krx_daily_prices(base_date: str) -> int:
    """
    Fetches, cleans, and upserts daily stock prices for KOSPI and KOSDAQ.
    If no rows are returned for both markets, records it as a closed market holiday.
    """
    log_message(f"Starting KRX price sync for {base_date}")
    raw_dfs = []
    
    for market in MARKETS:
        try:
            df = fetch_daily_prices(market, base_date)
            if not df.empty:
                raw_dfs.append(df)
                log_message(f"Fetched {len(df)} rows from {market} for {base_date}")
            else:
                log_message(f"No rows fetched from {market} for {base_date}")
        except Exception as e:
            log_message(f"Error fetching {market} data for {base_date}: {e}")
            
    if not raw_dfs:
        log_message(f"No stock data fetched for {base_date}. Inserting as closed market date.")
        try:
            insert_closed_market_date(base_date)
        except Exception as e:
            log_message(f"Failed to insert closed market date: {e}")
        return 0

    try:
        combined_df = pd.concat(raw_dfs, ignore_index=True)
        cleaned_df = clean_daily_prices(combined_df)
        
        inserted_rows = upsert_daily_prices(cleaned_df)
        log_message(f"Successfully upserted {inserted_rows} stock prices for {base_date}")
        return inserted_rows
    except Exception as e:
        log_message(f"Error processing/upserting daily prices for {base_date}: {e}")
        return 0

def parse_date_value(value: str, default_date: date = None) -> date:
    if not value:
        return default_date or date.today()
    if value.lower() == "today":
        return default_date or date.today()
    
    normalized = value.strip()
    if len(normalized) != 8 or not normalized.isdigit():
        raise ValueError("Date must be in YYYYMMDD format or 'today'")
    
    return date(int(normalized[:4]), int(normalized[4:6]), int(normalized[6:8]))

def iter_dates(start: date, end: date):
    curr = start
    while curr <= end:
        yield curr.strftime("%Y%m%d")
        curr += timedelta(days=1)

def sync_krx_daily_prices_range(start_date_str: str, end_date_str: str) -> int:
    """
    Syncs daily prices from start_date to end_date.
    Uses incremental sync by skipping dates already populated in DB or recorded as closed.
    """
    try:
        start_dt = parse_date_value(start_date_str)
        end_dt = parse_date_value(end_date_str)
    except ValueError as e:
        log_message(f"Invalid date range: {e}")
        return 0
        
    if start_dt > end_dt:
        log_message(f"Start date {start_date_str} is after end date {end_date_str}")
        return 0
        
    # Get initial cache of existing dates
    start_search_str = start_dt.strftime("%Y%m%d")
    try:
        existing_dates = get_existing_trade_dates(start_search_str)
        closed_dates = get_closed_market_dates(start_search_str)
    except Exception as e:
        log_message(f"Failed to fetch cached dates from DB: {e}. Proceeding without cache.")
        existing_dates = set()
        closed_dates = set()
        
    total_synced_records = 0
    target_dates = list(iter_dates(start_dt, end_dt))
    
    log_message(f"Syncing daily prices from {start_date_str} to {end_date_str} ({len(target_dates)} days)")
    
    for d_str in target_dates:
        if d_str in existing_dates:
            log_message(f"Date {d_str} already sync'd in daily_prices. Skipping.")
            continue
        if d_str in closed_dates:
            log_message(f"Date {d_str} is marked as closed market. Skipping.")
            continue
            
        synced = sync_krx_daily_prices(d_str)
        total_synced_records += synced
        
    log_message(f"Range sync completed. Total records synced: {total_synced_records}")
    return total_synced_records

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KRX Stock Price Sync Pipeline")
    parser.add_argument("--start-date", help="Start date in YYYYMMDD format or 'today'")
    parser.add_argument("--end-date", help="End date in YYYYMMDD format or 'today'")
    parser.add_argument("--days", type=int, help="Sync for last N days (mutually exclusive with --start-date)")
    
    args = parser.parse_args()
    
    today = date.today()
    
    # Resolve dates
    if args.days:
        if args.start_date:
            print("Error: --days and --start-date cannot be used together.", file=sys.stderr)
            sys.exit(1)
        end_d = parse_date_value(args.end_date) if args.end_date else today
        start_d = end_d - timedelta(days=args.days - 1)
        start_str = start_d.strftime("%Y%m%d")
        end_str = end_d.strftime("%Y%m%d")
    else:
        start_str = args.start_date if args.start_date else today.strftime("%Y%m%d")
        end_str = args.end_date if args.end_date else start_str
        
    sync_krx_daily_prices_range(start_str, end_str)
