import os
import sys
import argparse
from datetime import datetime

# Add project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.clients.cftc_cot_collector import CftcCotCollector
from app.db.db import save_cftc_cot, save_log

LOG_STRATEGY = "CFTC_COT_SYNC"

def log_message(message: str):
    print(message)
    try:
        save_log(LOG_STRATEGY, message)
    except Exception as e:
        print(f"Failed to save log to DB: {e}", file=sys.stderr)

def sync_cftc_cot(year: int = None) -> int:
    if year is None:
        year = datetime.today().year
        
    log_message(f"Starting CFTC COT Sync for year {year}...")
    
    collector = CftcCotCollector()
    try:
        records = collector.fetch_cot_report(year=year)
        if not records:
            log_message("No records parsed.")
            return 0
            
        saved_count = save_cftc_cot(records)
        log_message(f"Successfully saved {saved_count} CFTC COT records to database.")
        return saved_count
    except Exception as e:
        log_message(f"Error during CFTC COT Sync: {e}")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CFTC COT positioning data sync pipeline")
    parser.add_argument("--year", type=int, default=None, help="Year of COT report to sync (default: current year)")
    args = parser.parse_args()
    
    sync_cftc_cot(year=args.year)
