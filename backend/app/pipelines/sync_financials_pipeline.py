import os
import sys
import argparse
import time
import pandas as pd
from datetime import date
from typing import Tuple

# App modules
from app.clients.krx_collector import fetch_listed_stocks, Market
from app.clients.dart_collector import fetch_corp_codes, fetch_financial_statement, fetch_dividend_info
from app.cleaners.krx_stock_cleaner import clean_listed_stocks
from app.cleaners.dart_corp_cleaner import clean_corp_codes
from app.cleaners.dart_financial_cleaner import clean_financial_statement
from app.cleaners.dart_dividend_cleaner import clean_dividends
from app.db.db import (
    upsert_stocks,
    upsert_company_financials,
    get_active_stocks_with_dart_code,
    get_synced_financials_keys,
    save_log
)

MARKETS: Tuple[Market, ...] = ("KOSPI", "KOSDAQ")
LOG_STRATEGY = "FINANCIALS_SYNC"

def log_message(message: str):
    """Print to console and save to SQLite logs table."""
    print(message)
    try:
        save_log(LOG_STRATEGY, message)
    except Exception as e:
        print(f"Failed to save log to DB: {e}", file=sys.stderr)

def sync_stocks_master() -> int:
    """
    1. Fetches KOSPI & KOSDAQ listed stocks from KRX.
    2. Fetches corp codes from DART.
    3. Merges them on stock_code.
    4. Upserts into stocks database table.
    """
    log_message("Starting KRX listed stocks & DART corp codes master synchronization...")
    
    from datetime import timedelta
    krx_combined = pd.DataFrame()
    base_dt = date.today()
    
    # Backtrack up to 7 days to find a valid trading day with listed stocks data
    for i in range(7):
        target_date_str = (base_dt - timedelta(days=i)).strftime("%Y%m%d")
        krx_dfs = []
        for market in MARKETS:
            try:
                df = fetch_listed_stocks(market, target_date_str)
                if not df.empty:
                    krx_dfs.append(df)
            except Exception as e:
                # Silently catch and try next date
                pass
                
        if len(krx_dfs) == len(MARKETS):
            krx_combined = pd.concat(krx_dfs, ignore_index=True)
            log_message(f"Successfully fetched listed stocks data for date: {target_date_str}")
            break
        else:
            log_message(f"No stock master data found for date {target_date_str}. Trying previous day...")
            
    if krx_combined.empty:
        log_message("Error: No KRX listed stocks data found in the last 7 days. Aborting master sync.")
        return 0
        
    krx_cleaned = clean_listed_stocks(krx_combined)
    log_message(f"Cleaned {len(krx_cleaned)} KRX stocks.")
    
    # 2. Fetch DART Corp Codes
    try:
        dart_raw = fetch_corp_codes()
        dart_cleaned = clean_corp_codes(dart_raw)
        log_message(f"Fetched & cleaned {len(dart_cleaned)} DART corp codes")
    except Exception as e:
        log_message(f"Warning: Failed to fetch DART corp codes: {e}. Syncing stocks without DART mappings.")
        dart_cleaned = pd.DataFrame(columns=["stock_code", "corp_code"])
        
    # 3. Merge KRX + DART
    if not dart_cleaned.empty:
        merged_df = pd.merge(
            krx_cleaned,
            dart_cleaned[["stock_code", "corp_code"]],
            on="stock_code",
            how="left"
        )
        merged_df = merged_df.rename(columns={"corp_code": "dart_corp_code"})
    else:
        merged_df = krx_cleaned.copy()
        merged_df["dart_corp_code"] = None
        
    # 4. Upsert into Database
    try:
        inserted = upsert_stocks(merged_df)
        log_message(f"Successfully synced {inserted} stocks to SQLite master table.")
        return inserted
    except Exception as e:
        log_message(f"Failed to upsert stocks to DB: {e}")
        return 0

def sync_single_corp_financials(corp_code: str, stock_code: str, business_year: str) -> pd.DataFrame:
    """
    Helper to fetch, clean, and merge financial statement and dividend data for a single company.
    """
    # 1. Financial Statement
    try:
        fin_raw = fetch_financial_statement(corp_code, business_year)
        fin_cleaned = clean_financial_statement(fin_raw)
    except Exception as e:
        # Common DART behavior when data doesn't exist for the year
        fin_cleaned = pd.DataFrame()
        
    # 2. Dividend Info
    try:
        div_raw = fetch_dividend_info(corp_code, business_year)
        div_cleaned = clean_dividends(div_raw)
    except Exception as e:
        div_cleaned = pd.DataFrame()
        
    if fin_cleaned.empty and div_cleaned.empty:
        return pd.DataFrame()
        
    # 3. Merge Financials and Dividends
    if not fin_cleaned.empty:
        fin_df = fin_cleaned.copy()
        fin_df["bsns_year"] = pd.to_numeric(fin_df["bsns_year"], errors="coerce")
    else:
        # Mock financial frame if only dividends are available
        fin_df = pd.DataFrame([{
            "corp_code": corp_code,
            "stock_code": stock_code,
            "bsns_year": int(business_year),
            "fiscal_period": f"{business_year}.12"
        }])
        
    if not div_cleaned.empty:
        # Focus on Ordinary shares (보통주) first, fallback to first entry
        div_ord = div_cleaned[div_cleaned["stock_knd"].isin(["보통주", "보통주식", "보통", "-"])]
        if div_ord.empty:
            div_ord = div_cleaned.head(1).copy()
        else:
            div_ord = div_ord.head(1).copy()
            
        div_ord["fiscal_year"] = pd.to_numeric(div_ord["fiscal_year"], errors="coerce")
        
        merged = pd.merge(
            fin_df,
            div_ord,
            left_on=["corp_code", "bsns_year"],
            right_on=["corp_code", "fiscal_year"],
            how="left"
        )
    else:
        merged = fin_df.copy()
        
    # Make sure stock_code is mapped from outer context if missing
    if "stock_code" not in merged.columns or merged["stock_code"].isna().all():
        merged["stock_code"] = stock_code
        
    return merged

def sync_financials_and_dividends(business_year: str, limit: int = 0, sleep_seconds: float = 0.2) -> int:
    """
    Syncs financial reports and dividend metrics for active stocks.
    Uses incremental sync to skip companies already synced for the specified year.
    """
    log_message(f"Starting DART financials & dividends sync for Business Year {business_year}...")
    
    # 1. Get targets from DB
    try:
        active_stocks = get_active_stocks_with_dart_code()
    except Exception as e:
        log_message(f"Failed to fetch active stocks from DB: {e}")
        return 0
        
    if not active_stocks:
        log_message("No active stocks with DART codes found in DB. Run --sync-stocks first.")
        return 0
        
    # 2. Get synced cache
    try:
        synced_keys = get_synced_financials_keys(int(business_year))
    except Exception as e:
        log_message(f"Failed to fetch synced keys: {e}. Proceeding without cache.")
        synced_keys = set()
        
    log_message(f"Found {len(active_stocks)} active stocks in DB. Synced cache has {len(synced_keys)} records.")
    
    # Filter out already synced
    targets = [s for s in active_stocks if s["dart_corp_code"] not in synced_keys]
    log_message(f"Identified {len(targets)} stocks to synchronize.")
    
    if limit > 0:
        targets = targets[:limit]
        log_message(f"Limit applied: synchronizing top {limit} stocks.")
        
    if not targets:
        log_message("All stocks are already up-to-date. Sync skipped.")
        return 0
        
    success_count = 0
    synced_records = []
    
    for idx, target in enumerate(targets):
        stock_code = target["stock_code"]
        corp_name = target["stock_name"]
        corp_code = target["dart_corp_code"]
        
        log_prefix = f"[{idx + 1}/{len(targets)}] {stock_code} {corp_name}"
        
        try:
            corp_df = sync_single_corp_financials(corp_code, stock_code, business_year)
            if not corp_df.empty:
                synced_records.append(corp_df)
                success_count += 1
                log_message(f"{log_prefix}: Synced successfully. rows={len(corp_df)}")
            else:
                log_message(f"{log_prefix}: No financials/dividends data returned.")
        except Exception as e:
            log_message(f"{log_prefix}: Failed sync due to error: {e}")
            
        time.sleep(sleep_seconds)
        
    if not synced_records:
        log_message("No financial statements synced in this batch.")
        return 0
        
    # 3. Concatenate and Upsert
    try:
        combined = pd.concat(synced_records, ignore_index=True)
        inserted = upsert_company_financials(combined)
        log_message(f"Sync complete. Successfully upserted {inserted} financial periods for {success_count} companies.")
        return inserted
    except Exception as e:
        log_message(f"Failed to upsert financial batch: {e}")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DART Financials & Dividends Sync Pipeline")
    parser.add_argument("--sync-stocks", action="store_true", help="Sync stock master directory from KRX & DART")
    parser.add_argument("--sync-financials", action="store_true", help="Sync financials & dividends from DART")
    parser.add_argument("--business-year", default=str(date.today().year - 1), help="Report year for financials (default: last year)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of companies to sync (useful for testing)")
    parser.add_argument("--sleep-seconds", type=float, default=0.2, help="Delay between API requests to respect rate limits")
    
    args = parser.parse_args()
    
    # Require at least one action
    if not args.sync_stocks and not args.sync_financials:
        parser.print_help()
        sys.exit(1)
        
    if args.sync_stocks:
        sync_stocks_master()
        
    if args.sync_financials:
        sync_financials_and_dividends(
            business_year=args.business_year,
            limit=args.limit,
            sleep_seconds=args.sleep_seconds
        )
