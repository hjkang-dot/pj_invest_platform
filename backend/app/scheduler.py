import asyncio
from datetime import date, datetime, timedelta, timezone

from app.database import get_db
from app.db.db import get_latest_trade_date
from app.pipelines.krx_daily_price_pipeline import sync_krx_daily_prices_range
from app.pipelines.sync_cftc_cot_pipeline import sync_cftc_cot
from app.pipelines.sync_macro_pipeline import sync_macro_data
from app.pipelines.sync_yahoo_futures_pipeline import sync_yahoo_futures

is_syncing = False

async def run_catchup_sync_and_scheduler():
    print("[Scheduler] Initiating startup catch-up sync task...")
    try:
        # 1. Fetch the latest synced trade date from SQLite
        last_date_str = get_latest_trade_date()
        today_obj = date.today()
        
        if last_date_str:
            try:
                # Try YYYY-MM-DD
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            except ValueError:
                try:
                    # Try YYYYMMDD
                    last_date = datetime.strptime(last_date_str, "%Y%m%d").date()
                except ValueError:
                    last_date = today_obj - timedelta(days=5)
        else:
            # Default catch-up fallback to last 5 days
            last_date = today_obj - timedelta(days=5)
            
        if last_date < today_obj:
            start_str = (last_date + timedelta(days=1)).strftime("%Y%m%d")
            end_str = today_obj.strftime("%Y%m%d")
            days_diff = (today_obj - last_date).days
            
            print(f"[Scheduler] Detected gap between {last_date_str} and {today_obj.strftime('%Y-%m-%d')}. Fetching {days_diff} days of missing data.")
            
            # Sync missing KRX daily prices
            try:
                sync_krx_daily_prices_range(start_str, end_str)
            except Exception as e:
                print(f"[Scheduler Error] KRX catch-up sync failed: {e}")
                
            # Sync missing Yahoo futures
            try:
                sync_yahoo_futures(days=max(days_diff + 2, 5))
            except Exception as e:
                print(f"[Scheduler Error] Yahoo futures catch-up sync failed: {e}")
                
            # Sync Macro indicators & CFTC COT
            try:
                sync_macro_data(limit=60, days_forward=14)
            except Exception as e:
                print(f"[Scheduler Error] Macro data catch-up sync failed: {e}")
                
            try:
                sync_cftc_cot()
            except Exception as e:
                print(f"[Scheduler Error] CFTC COT catch-up sync failed: {e}")
                
        else:
            print("[Scheduler] Database is already up to date. No catch-up sync needed.")
    except Exception as e:
        print(f"[Scheduler Error] Failed during startup catch-up sync: {e}")
        
    # 2. Start periodic check loop every 1 hour (3600 seconds)
    print("[Scheduler] Periodic check scheduler loop successfully started.")
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        # Run daily sync check at 18:00 (6 PM) to grab KOSPI/KOSDAQ and futures of today
        if now.hour == 18:
            print("[Scheduler] Running daily scheduled data synchronization...")
            today_str = now.strftime("%Y%m%d")
            try:
                sync_krx_daily_prices_range(today_str, today_str)
                sync_yahoo_futures(days=3)
                sync_macro_data(limit=30, days_forward=14)
                sync_cftc_cot()
            except Exception as e:
                print(f"[Scheduler Error] Failed during daily scheduled sync: {e}")

def run_catchup_sync():
    global is_syncing
    if is_syncing:
        return
    is_syncing = True
    print("[Startup Sync] Checking for missing trade prices...")
    try:
        try:
            sync_yahoo_futures()
        except Exception as e:
            print(f"[Startup Sync] Yahoo futures sync failed: {e}")
            
        try:
            from app.pipelines.sync_cftc_cot_pipeline import sync_cftc_cot
            sync_cftc_cot()
        except Exception as e:
            print(f"[Startup Sync] CFTC COT sync failed: {e}")
            
        try:
            from app.pipelines.sync_macro_pipeline import sync_macro_data
            sync_macro_data()
        except Exception as e:
            print(f"[Startup Sync] Macro data sync failed: {e}")
            
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        row = cursor.fetchone()
        conn.close()
        
        max_date_str = row[0] if row and row[0] else None
        
        from datetime import datetime, timezone, timedelta, date
        kst_tz = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst_tz)
        today_kst = now_kst.date()
        
        if not max_date_str:
            # Fallback to 5 days ago if DB has no price data at all
            start_date_d = today_kst - timedelta(days=5)
            max_date_str = start_date_d.strftime("%Y%m%d")
            print(f"[Startup Sync] No trade dates found in DB. Starting from 5 days ago: {max_date_str}")
        
        # Calculate target end date (today if past 16:00 KST, else yesterday)
        if now_kst.hour >= 16:
            end_date_d = today_kst
        else:
            end_date_d = today_kst - timedelta(days=1)
            
        end_date_str = end_date_d.strftime("%Y%m%d")
        
        try:
            max_date_d = date(int(max_date_str[:4]), int(max_date_str[4:6]), int(max_date_str[6:8]))
        except Exception:
            max_date_d = today_kst - timedelta(days=5)
            
        if max_date_d < end_date_d:
            start_sync_d = max_date_d + timedelta(days=1)
            start_sync_str = start_sync_d.strftime("%Y%m%d")
            print(f"[Startup Sync] Syncing missing trade prices from {start_sync_str} to {end_date_str}")
            
            from app.pipelines.krx_daily_price_pipeline import sync_krx_daily_prices_range
            synced_count = sync_krx_daily_prices_range(start_sync_str, end_date_str)
            print(f"[Startup Sync] Sync complete. Synced {synced_count} records.")
        else:
            print(f"[Startup Sync] Already up to date (DB: {max_date_str}, Target: {end_date_str}).")
    except Exception as e:
        print(f"[Startup Sync] Error during catchup sync: {e}")
    finally:
        is_syncing = False

async def schedule_daily_sync():
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

