import os
import sys
import argparse
from datetime import datetime

# Add project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.clients.macro_collector import MacroCollector
from app.db.db import save_macro_indicators, save_macro_calendar, save_log

LOG_STRATEGY = "MACRO_DATA_SYNC"

def log_message(message: str):
    print(message)
    try:
        save_log(LOG_STRATEGY, message)
    except Exception as e:
        print(f"Failed to save log to DB: {e}", file=sys.stderr)

def sync_macro_data(limit: int = 120, days_forward: int = 14) -> bool:
    log_message("Starting Macroeconomic Data Sync...")
    collector = MacroCollector()
    
    # 1. Sync Macro indicators
    try:
        indicator_records = collector.fetch_macro_indicators(limit=limit)
        if indicator_records:
            saved_indicators = save_macro_indicators(indicator_records)
            log_message(f"Successfully saved {saved_indicators} macro indicators history records.")
        else:
            log_message("No macro indicators fetched.")
    except Exception as e:
        log_message(f"Error syncing macro indicators: {e}")
        
    # 2. Sync Macro calendar events
    try:
        calendar_records = collector.fetch_economic_calendar(days_forward=days_forward)
        if calendar_records:
            saved_calendar = save_macro_calendar(calendar_records)
            log_message(f"Successfully saved {saved_calendar} economic calendar events.")
        else:
            log_message("No calendar events fetched.")
    except Exception as e:
        log_message(f"Error syncing economic calendar: {e}")
        
    log_message("Macroeconomic Data Sync completed.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Macroeconomic indicators and calendar sync pipeline")
    parser.add_argument("--limit", type=int, default=120, help="Number of historical observation records to sync for indicators")
    parser.add_argument("--days", type=int, default=14, help="Number of days forward to sync for economic calendar")
    args = parser.parse_args()
    
    sync_macro_data(limit=args.limit, days_forward=args.days)
