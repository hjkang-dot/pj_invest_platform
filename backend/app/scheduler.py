import asyncio
from datetime import date, datetime, timedelta, timezone
import sys

from app.database import get_db
from app.db.db import get_latest_trade_date
from app.pipelines.krx_daily_price_pipeline import sync_krx_daily_prices_range
from app.pipelines.sync_cftc_cot_pipeline import sync_cftc_cot
from app.pipelines.sync_macro_pipeline import sync_macro_data
from app.pipelines.sync_yahoo_futures_pipeline import sync_yahoo_futures

is_syncing = False

async def run_catchup_sync_and_scheduler():
    """
    Background scheduler loop. Triggers catchup sync every 12 hours.
    """
    print("[Scheduler] Starting background scheduler loop...")
    while True:
        try:
            # Sleep for 12 hours (43200 seconds)
            await asyncio.sleep(43200)
            print("[Scheduler] Triggering periodic background sync...")
            await asyncio.to_thread(run_catchup_sync)
        except Exception as e:
            print(f"[Scheduler] Error in scheduler loop: {e}")
            await asyncio.sleep(300)

