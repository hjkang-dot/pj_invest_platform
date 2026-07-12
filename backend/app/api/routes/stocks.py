from datetime import datetime, date, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

import app.scheduler as scheduler
from app.database import get_db
from app.scheduler import sync_yahoo_futures

router = APIRouter()

@router.post("/api/stocks/sync")
def trigger_stock_sync(background_tasks: BackgroundTasks):
    if scheduler.is_syncing:
        raise HTTPException(status_code=409, detail="이미 주가 데이터 동기화가 진행 중입니다.")
        
    def run_manual_sync():
        scheduler.is_syncing = True
        print("[Manual Sync] Triggered manual sync...")
        try:
            try:
                sync_yahoo_futures()
            except Exception as e:
                print(f"[Manual Sync] Yahoo futures sync failed: {e}")
                
            try:
                from app.pipelines.sync_cftc_cot_pipeline import sync_cftc_cot
                sync_cftc_cot()
            except Exception as e:
                print(f"[Manual Sync] CFTC COT sync failed: {e}")
                
            try:
                from app.pipelines.sync_macro_pipeline import sync_macro_data
                sync_macro_data()
            except Exception as e:
                print(f"[Manual Sync] Macro data sync failed: {e}")
            from datetime import datetime, timezone, timedelta, date
            kst_tz = timezone(timedelta(hours=9))
            now_kst = datetime.now(kst_tz)
            today_str = now_kst.strftime("%Y%m%d")
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
            row = cursor.fetchone()
            conn.close()
            
            max_date_str = row[0] if row and row[0] else None
            if not max_date_str:
                start_date_d = now_kst.date() - timedelta(days=5)
                max_date_str = start_date_d.strftime("%Y%m%d")
                
            try:
                max_date_d = date(int(max_date_str[:4]), int(max_date_str[4:6]), int(max_date_str[6:8]))
            except Exception:
                max_date_d = now_kst.date() - timedelta(days=5)
                
            start_sync_d = max_date_d + timedelta(days=1)
            start_sync_str = start_sync_d.strftime("%Y%m%d")
            
            if start_sync_d <= now_kst.date():
                print(f"[Manual Sync] Syncing trade prices from {start_sync_str} to {today_str}")
                from app.pipelines.krx_daily_price_pipeline import sync_krx_daily_prices_range
                sync_krx_daily_prices_range(start_sync_str, today_str)
            else:
                print(f"[Manual Sync] Already up to date up to today: {today_str}")
        except Exception as e:
            print(f"[Manual Sync] Error during manual sync: {e}")
        finally:
            scheduler.is_syncing = False
            
    background_tasks.add_task(run_manual_sync)
    return {"status": "success", "message": "주가 동기화가 백그라운드에서 시작되었습니다."}

@router.get("/api/stocks/sync/status")
def get_sync_status():
    return {"isSyncing": scheduler.is_syncing}

@router.get("/api/stocks")
def get_stocks(search: str = "", market: str = "", limit: int = 50, offset: int = 0):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Query active stocks and join with their latest daily close price if available
        query = """
            SELECT s.stock_code, s.stock_name, s.market, s.sector, dp.close_price, dp.market_cap
            FROM stocks s
            LEFT JOIN daily_prices dp ON s.stock_code = dp.stock_code AND dp.trade_date = (
                SELECT MAX(trade_date) FROM daily_prices WHERE stock_code = s.stock_code
            )
            WHERE s.is_active = 1
        """
        params = []
        if search:
            query += " AND (s.stock_code LIKE ? OR s.stock_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if market:
            query += " AND s.market = ?"
            params.append(market)
            
        query += " ORDER BY s.stock_name ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Check if we have any coin in the results
        has_aden_assets = False
        for r in rows:
            if r["market"] == "COIN":
                has_aden_assets = True
                break
                
        ticker_map = {}
        if has_aden_assets:
            try:
                from app.clients.aden_client import AdenClient
                client = AdenClient()
                tickers = client.get_tickers()
                if tickers:
                    for t in tickers:
                        ticker_map[t["contract"]] = t
            except Exception as e:
                print(f"Failed to fetch tickers from AdenClient: {e}")

        result = []
        for r in rows:
            code = r["stock_code"]
            market = r["market"]
            close_price = r["close_price"] or 0
            market_cap = r["market_cap"] or 0
            
            if market == "COIN" and code in ticker_map:
                t = ticker_map[code]
                close_price = float(t.get("last", 0))
                market_cap = float(t.get("volume_24h_usd", 0)) or (float(t.get("mark_price", 0)) * 1000000)
                
            result.append({
                "code": code,
                "name": r["stock_name"],
                "market": market,
                "sector": r["sector"] or "미분류",
                "closePrice": close_price,
                "marketCap": market_cap
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/api/stocks/{stock_code}")
def get_stock_detail(stock_code: str):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch stock master
        cursor.execute("""
            SELECT stock_code, stock_name, market, sector, listed_date, listed_shares, dart_corp_code 
            FROM stocks WHERE stock_code = ? LIMIT 1
        """, (stock_code,))
        stock_row = cursor.fetchone()
        if not stock_row:
            raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
        
        # Branch for COIN assets
        if stock_row["market"] == "COIN":
            # 1. Fetch latest ticker
            ticker_data = {}
            try:
                from app.clients.aden_client import AdenClient
                client = AdenClient()
                tickers = client.get_tickers(contract=stock_code)
                if isinstance(tickers, list) and len(tickers) > 0:
                    ticker_data = tickers[0]
                elif isinstance(tickers, dict):
                    ticker_data = tickers
            except Exception as e:
                print(f"Failed to fetch ticker for {stock_code}: {e}")

            close_price = float(ticker_data.get("last", 0))
            volume_24h = float(ticker_data.get("volume_24h_usd", 0))
            market_cap = volume_24h or (float(ticker_data.get("mark_price", 0)) * 1000000)

            # 2. Fetch 240-day historical prices for candle chart
            price_history = []
            try:
                from app.clients.aden_client import AdenClient
                client = AdenClient()
                # Fetch 240 daily candles (1d interval)
                candles = client.get_candlesticks_cached(contract=stock_code, interval='1d', limit=240)
                from datetime import timezone, timedelta
                kst_tz = timezone(timedelta(hours=9))
                for c in candles:
                    dt = datetime.fromtimestamp(c["t"], kst_tz)
                    price_history.append({
                        "date": dt.strftime("%Y%m%d"),
                        "openPrice": c["o"],
                        "highPrice": c["h"],
                        "lowPrice": c["l"],
                        "closePrice": c["c"],
                        "volume": c["v"]
                    })
            except Exception as e:
                print(f"Failed to fetch historical candles for {stock_code}: {e}")

            # Compute price change relative to previous candle
            if close_price == 0 and price_history:
                close_price = price_history[-1]["closePrice"]

            if len(price_history) >= 2:
                prev_close = price_history[-2]["closePrice"]
                price_change = close_price - prev_close
                change_rate = (price_change / prev_close) * 100 if prev_close > 0 else 0.0
            elif len(price_history) == 1:
                open_price = price_history[-1]["openPrice"]
                price_change = close_price - open_price
                change_rate = (price_change / open_price) * 100 if open_price > 0 else 0.0
            else:
                price_change = 0.0
                change_rate = 0.0

            # Current date in KST format YYYY-MM-DD
            from datetime import timezone, timedelta
            kst_tz = timezone(timedelta(hours=9))
            now_kst = datetime.now(kst_tz)
            formatted_date = now_kst.strftime("%Y-%m-%d")

            latest_price = {
                "date": formatted_date,
                "closePrice": close_price,
                "priceChange": price_change,
                "changeRate": change_rate,
                "volume": volume_24h,
                "marketCap": market_cap
            }

            return {
                "code": stock_row["stock_code"],
                "name": stock_row["stock_name"],
                "market": stock_row["market"],
                "sector": stock_row["sector"] or "미분류",
                "listedDate": stock_row["listed_date"],
                "listedShares": stock_row["listed_shares"],
                "latestPrice": latest_price,
                "financials": [],
                "priceHistory": price_history
            }

        # Existing logic for KOSPI / KOSDAQ stocks
        # 2. Fetch latest price details
        cursor.execute("""
            SELECT trade_date, close_price, price_change, change_rate, volume, market_cap 
            FROM daily_prices 
            WHERE stock_code = ? 
            ORDER BY trade_date DESC LIMIT 1
        """, (stock_code,))
        price_row = cursor.fetchone()
        
        trade_date_raw = price_row["trade_date"] if price_row else ""
        formatted_date = ""
        if trade_date_raw and len(trade_date_raw) == 8:
            formatted_date = f"{trade_date_raw[:4]}-{trade_date_raw[4:6]}-{trade_date_raw[6:]}"
        else:
            formatted_date = trade_date_raw

        latest_price = {
            "date": formatted_date,
            "closePrice": price_row["close_price"] if price_row else 0,
            "priceChange": price_row["price_change"] if price_row else 0,
            "changeRate": price_row["change_rate"] if price_row else 0.0,
            "volume": price_row["volume"] if price_row else 0,
            "marketCap": price_row["market_cap"] if price_row else 0
        }

        # 3. Fetch financial statements history
        cursor.execute("""
            SELECT bsns_year, fiscal_period, total_assets, total_liabilities, total_equity, 
                   revenue, operating_income, net_income, debt_ratio, current_ratio, 
                   operating_margin, net_margin, eps, cash_dividend_yield, cash_dividend_per_share, 
                   cash_dividend_payout_ratio
            FROM company_financials
            WHERE stock_code = ?
            ORDER BY bsns_year ASC
        """, (stock_code,))
        financial_rows = cursor.fetchall()

        # 온디맨드 DART 동기화: KOSPI/KOSDAQ 주식인데 재무제표가 비어있는 경우
        if not financial_rows and stock_row["market"] in ("KOSPI", "KOSDAQ") and stock_row["dart_corp_code"]:
            print(f"[On-demand Sync] Financials empty for {stock_code} ({stock_row['stock_name']}). Fetching from DART...")
            try:
                from app.pipelines.sync_financials_pipeline import sync_single_corp_financials
                from app.db.db import upsert_company_financials
                import pandas as pd
                
                # 최근 3개년 동기화 시도
                current_year = datetime.now().year
                years_to_sync = [str(y) for y in range(current_year - 3, current_year)]
                
                synced_dfs = []
                for y in years_to_sync:
                    try:
                        df = sync_single_corp_financials(stock_row["dart_corp_code"], stock_code, y)
                        if not df.empty:
                            synced_dfs.append(df)
                    except Exception as ex:
                        print(f"[On-demand Sync Warning] Failed to sync year {y} for {stock_code}: {ex}")
                
                if synced_dfs:
                    combined = pd.concat(synced_dfs, ignore_index=True)
                    upsert_company_financials(combined)
                    print(f"[On-demand Sync] Successfully synced financials for {stock_code}. Re-fetching...")
                    
                    # 재조회
                    cursor.execute("""
                        SELECT bsns_year, fiscal_period, total_assets, total_liabilities, total_equity, 
                               revenue, operating_income, net_income, debt_ratio, current_ratio, 
                               operating_margin, net_margin, eps, cash_dividend_yield, cash_dividend_per_share, 
                               cash_dividend_payout_ratio
                        FROM company_financials
                        WHERE stock_code = ?
                        ORDER BY bsns_year ASC
                    """, (stock_code,))
                    financial_rows = cursor.fetchall()
            except Exception as e:
                print(f"[On-demand Sync Error] General failure syncing financials for {stock_code}: {e}")
        
        financials = []
        for f in financial_rows:
            roe = None
            if f["total_equity"] and f["net_income"] and f["total_equity"] != 0:
                roe = (f["net_income"] / f["total_equity"]) * 100

            # fiscal_period(예: "2024.12")에서 실제 결산 연도를 추출하여 UI 연도로 사용
            actual_year = f["bsns_year"]
            if f["fiscal_period"] and "." in f["fiscal_period"]:
                try:
                    actual_year = int(f["fiscal_period"].split(".")[0])
                except Exception:
                    pass

            financials.append({
                "year": actual_year,
                "period": f["fiscal_period"],
                "assets": f["total_assets"],
                "liabilities": f["total_liabilities"],
                "equity": f["total_equity"],
                "revenue": f["revenue"],
                "operatingIncome": f["operating_income"],
                "netIncome": f["net_income"],
                "debtRatio": f["debt_ratio"],
                "currentRatio": f["current_ratio"],
                "operatingMargin": f["operating_margin"],
                "netMargin": f["net_margin"],
                "eps": f["eps"],
                "roe": roe,
                "dividendYield": f["cash_dividend_yield"],
                "dividendPerShare": f["cash_dividend_per_share"],
                "payoutRatio": f["cash_dividend_payout_ratio"]
            })

        # 결산월(period) 기준으로 최종 정렬하여 시간 순서 보장
        financials = sorted(financials, key=lambda x: x["period"] or "")

        # 4. Fetch 240-day historical prices for candle chart
        cursor.execute("""
            SELECT trade_date, open_price, high_price, low_price, close_price, volume
            FROM daily_prices 
            WHERE stock_code = ? 
            ORDER BY trade_date DESC LIMIT 240
        """, (stock_code,))
        history_rows = cursor.fetchall()
        
        price_history = []
        for h in reversed(history_rows):
            price_history.append({
                "date": h["trade_date"],
                "openPrice": h["open_price"],
                "highPrice": h["high_price"],
                "lowPrice": h["low_price"],
                "closePrice": h["close_price"],
                "volume": h["volume"]
            })

        return {
            "code": stock_row["stock_code"],
            "name": stock_row["stock_name"],
            "market": stock_row["market"],
            "sector": stock_row["sector"] or "미분류",
            "listedDate": stock_row["listed_date"],
            "listedShares": stock_row["listed_shares"],
            "latestPrice": latest_price,
            "financials": financials,
            "priceHistory": price_history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ----------------- FUTURES & MACRO API ENDPOINTS -----------------

