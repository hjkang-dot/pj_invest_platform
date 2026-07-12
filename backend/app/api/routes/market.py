from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/api/futures/cot")
def get_futures_cot(symbol: str = "XAU_USDT", limit: int = 52):
    """
    Returns weekly Commitment of Traders (COT) positioning data for a given contract.
    """
    from app.db.db import get_cftc_cot
    try:
        cot_data = get_cftc_cot(symbol, limit=limit)
        return cot_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/macro/calendar")
def get_economic_calendar(days: int = 14):
    """
    Returns upcoming macroeconomic events from TradingView economic calendar.
    """
    from app.db.db import get_macro_calendar
    from datetime import date, timedelta
    today_str = date.today().strftime("%Y-%m-%d")
    end_str = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        events = get_macro_calendar(today_str, end_str)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/macro/indicators")
def get_macro_indicators_data(limit: int = 120):
    """
    Returns historical timeseries observations for major macroeconomic indicators.
    """
    from app.db.db import get_macro_indicators
    series_ids = ["FEDFUNDS", "US10Y", "US2Y", "CPI", "UNRATE", "GDP"]
    try:
        data = get_macro_indicators(series_ids, limit=limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/logs")
def get_system_logs(strategy: Optional[str] = None, limit: int = 100):
    """
    Returns pipeline or strategy execution logs.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if strategy:
            cursor.execute("""
                SELECT timestamp, message FROM logs 
                WHERE strategy = ? 
                ORDER BY id DESC LIMIT ?
            """, (strategy, limit))
        else:
            cursor.execute("""
                SELECT timestamp, message FROM logs 
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        logs_list = []
        for row in reversed(rows):
            ts, msg = row
            if msg.startswith("["):
                logs_list.append(msg)
            else:
                logs_list.append(f"[{ts}] {msg}")
        return logs_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


