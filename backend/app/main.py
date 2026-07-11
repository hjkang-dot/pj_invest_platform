import os
import sqlite3
import asyncio
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from app.pipelines.krx_daily_price_pipeline import sync_krx_daily_prices_range
from app.pipelines.sync_yahoo_futures_pipeline import sync_yahoo_futures
from app.pipelines.sync_macro_pipeline import sync_macro_data
from app.pipelines.sync_cftc_cot_pipeline import sync_cftc_cot
from app.db.db import get_latest_trade_date

app = FastAPI(title="Astron Trading Engine API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve DB Path (backend/app/main.py is 2 levels deep from root)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "invest_platform.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Helper to initialize default portfolio data on first run if empty
def init_default_data():
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Check if tables exist. If they don't, create them.
        # Note: app.db.db.init_db is already run or verified.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ud_portfolio_status'")
        if not cursor.fetchone():
            print("[System] Database tables do not exist. Please run init_db.py first.")
            return

        cursor.execute("SELECT COUNT(*) FROM ud_portfolio_status")
        if cursor.fetchone()[0] == 0:
            print("[System] DB is empty. Initializing default portfolio data...")
            
            # 1. ud_portfolio_status
            cursor.execute("""
                INSERT INTO ud_portfolio_status (strategy_type, initial_balance, current_cash, current_valuation, total_asset, mdd, total_return, win_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('DIVIDEND', 154200000.0, 33337250.0, 120862750.0, 154200000.0, 4.2, 24.8, 62.0))
            
            # 2. ud_portfolio_holdings
            holdings = [
                ("005930", "삼성전자", "2026-06-01", 72000.0, 150.0, 75200.0, 11280000.0, 4.4, 72.0, "ACTIVE", "op_growth"),
                ("000660", "SK하이닉스", "2026-06-03", 178000.0, 60.0, 182500.0, 10950000.0, 2.5, 68.0, "ACTIVE", "op_growth"),
                ("035720", "카카오", "2026-06-05", 48500.0, 100.0, 47200.0, 4720000.0, -2.7, 58.0, "ACTIVE", "ud_dividend"),
                ("BTC_USDT", "Bitcoin", "2026-06-10", 63280.0, 0.85, 65140.0, 55369.0, 2.9, 0.0, "ACTIVE", "vol_climax"),
                ("ETH_USDT", "Ethereum", "2026-06-12", 3450.0, 4.2, 3380.0, 14196.0, -2.0, 0.0, "ACTIVE", "vol_climax")
            ]
            cursor.executemany("""
                INSERT INTO ud_portfolio_holdings (stock_code, stock_name, entry_date, entry_price, quantity, current_price, valuation, holding_return, score_at_entry, status, strategy_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, holdings)

            # 3. ud_portfolio_transactions
            transactions = [
                ("2026-06-01", "005930", "삼성전자", "BUY", 72000.0, 150.0, 10800000.0, 72.0, "op_growth"),
                ("2026-06-03", "000660", "SK하이닉스", "BUY", 178000.0, 60.0, 10680000.0, 68.0, "op_growth"),
                ("2026-06-05", "BTC_USDT", "Bitcoin", "BUY", 63280.0, 0.85, 53788.0, 0.0, "vol_climax"),
                ("2026-06-06", "ETH_USDT", "Ethereum", "BUY", 3450.0, 4.2, 14490.0, 0.0, "vol_climax"),
                ("2026-06-10", "035720", "카카오", "BUY", 48500.0, 100.0, 4850000.0, 58.0, "ud_dividend")
            ]
            cursor.executemany("""
                INSERT INTO ud_portfolio_transactions (trade_date, stock_code, stock_name, transaction_type, price, quantity, amount, score, strategy_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, transactions)
            conn.commit()

        # Check and populate default crypto and futures master assets
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE market IN ('COIN', 'FUTURES')")
        if cursor.fetchone()[0] == 0:
            print("[System] Inserting default crypto and futures master assets...")
            assets = [
                ("BTC_USDT", "Bitcoin", "COIN", "가상자산", "BTC", "2020-01-01", 1000000, 1),
                ("ETH_USDT", "Ethereum", "COIN", "가상자산", "ETH", "2020-01-01", 1000000, 1),
                ("SOL_USDT", "Solana", "COIN", "가상자산", "SOL", "2020-01-01", 1000000, 1),
                ("XAU_USDT", "Gold Futures (금 선물)", "FUTURES", "원자재", "XAU", "2020-01-01", 1000000, 1),
                ("CL_USDT", "Crude Oil Futures (크루드 오일)", "FUTURES", "에너지", "CL", "2020-01-01", 1000000, 1),
                ("NAS100_USDT", "Nasdaq 100 Futures (나스닥 100)", "FUTURES", "지수", "NAS100", "2020-01-01", 1000000, 1),
                ("AAPL_USDT", "Apple Stock Futures (애플 선물)", "FUTURES", "해외주식", "AAPL", "2020-01-01", 1000000, 1),
                ("TSLA_USDT", "Tesla Stock Futures (테슬라 선물)", "FUTURES", "해외주식", "TSLA", "2020-01-01", 1000000, 1)
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO stocks (stock_code, stock_name, market, sector, dart_corp_code, listed_date, listed_shares, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, assets)
            conn.commit()
    except Exception as e:
        print(f"[System] Failed to auto-populate DB: {e}")
    finally:
        conn.close()

# Pydantic Schemas
class TransactionCreate(BaseModel):
    date: str
    assetClass: str  # 'STOCK' | 'COIN' | 'FUTURES' | 'GOLD'
    strategyId: str  # 'ud_dividend' | 'op_growth' | 'deep_value_contra' | 'vol_climax' | 'NONE'
    type: str        # 'BUY' | 'SELL'
    symbol: str
    name: str
    price: float
    qty: float
    fee: float
    memo: str
    currency: Optional[str] = "KRW"

class CashUpdate(BaseModel):
    cash: float

class AccountCashUpdate(BaseModel):
    accountType: str  # 'STOCK' | 'FUTURES'
    amount: float

async def run_catchup_sync_and_scheduler():
    print("[Scheduler] Initiating startup catch-up sync task...")
    try:
        # 1. Fetch the latest synced trade date from SQLite
        last_date_str = get_latest_trade_date()
        today_obj = date.today()
        
        if last_date_str:
            try:
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
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

@app.on_event("startup")
async def startup_event():
    # Auto populate initial default data
    init_default_data()
    # Spawn catch-up sync and scheduler task asynchronously in background loop
    asyncio.create_task(run_catchup_sync_and_scheduler())

# ----------------- API ROUTES -----------------

@app.get("/api/dashboard")
def get_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch cash balance & summary
        cursor.execute("SELECT current_cash, total_return, mdd FROM ud_portfolio_status LIMIT 1")
        status_row = cursor.fetchone()
        
        cash_balance = status_row["current_cash"] if status_row else 33337250.0
        cum_return = status_row["total_return"] if status_row else 24.8
        mdd_val = status_row["mdd"] if status_row else -4.2

        usd_rate = 1350.0
        holdings_list = []
        stock_val_krw = 0
        coin_val_krw = 0

        # 2. Fetch active holdings from Local DB
        cursor.execute("""
            SELECT id, stock_code, stock_name, entry_price, quantity, current_price, valuation, holding_return, score_at_entry, strategy_type 
            FROM ud_portfolio_holdings 
            WHERE status = 'ACTIVE'
        """)
        holding_rows = cursor.fetchall()
        
        db_coin_val_krw = 0
        db_coin_pnl_krw = 0
        stock_pnl_krw = 0
        for row in holding_rows:
            symbol = row["stock_code"]
            is_usd = row["strategy_type"] == "vol_climax" or "_" in symbol or symbol == "GOLD_FUT"
            rate = usd_rate if is_usd else 1.0
            
            val_native = row["quantity"] * row["current_price"]
            val_krw = val_native * rate
            pnl_krw = (row["quantity"] * (row["current_price"] - row["entry_price"])) * rate

            if is_usd:
                db_coin_val_krw += val_krw
                db_coin_pnl_krw += pnl_krw
            else:
                stock_val_krw += val_krw
                stock_pnl_krw += pnl_krw
                holdings_list.append({
                    "id": str(row["id"]),
                    "code": symbol,
                    "name": row["stock_name"],
                    "type": "STOCK",
                    "quantity": row["quantity"],
                    "entryPrice": row["entry_price"],
                    "currentPrice": row["current_price"],
                    "valuation": val_native,  # Frontend format
                    "pnl": val_native - (row["quantity"] * row["entry_price"]),
                    "pnlPct": float(row["holding_return"]),
                    "score": int(row["score_at_entry"]) if row["score_at_entry"] else None,
                    "posType": None
                })

        # 3. Fetch COIN holdings & balance from Aden Exchange API
        aden_success = False
        coin_pnl_krw = 0
        try:
            from app.clients.aden_client import AdenClient
            client = AdenClient()
            
            # Fetch Aden account total
            aden_acc = client.get_account()
            aden_total_usd = float(aden_acc.get("total", 0))
            coin_val_krw = aden_total_usd * usd_rate
            
            coin_upnl_usd = float(aden_acc.get("unrealised_pnl", 0))
            coin_pnl_krw = coin_upnl_usd * usd_rate
            
            # Fetch Aden positions
            aden_pos = client.get_positions()
            for idx, pos in enumerate(aden_pos):
                size = float(pos.get("size", 0))
                if size == 0:
                    continue
                entry_p = float(pos.get("entry_price", 0))
                mark_p = float(pos.get("mark_price", 0))
                val_usd = float(pos.get("value", 0))
                upnl = float(pos.get("unrealised_pnl", 0))
                
                pos_type = "SHORT" if size < 0 else "LONG"
                
                # Calculate pnl percentage based on direction
                if pos_type == "SHORT":
                    pnl_pct = ((entry_p - mark_p) / entry_p) * 100 if entry_p > 0 else 0.0
                else:
                    pnl_pct = ((mark_p - entry_p) / entry_p) * 100 if entry_p > 0 else 0.0

                holdings_list.append({
                    "id": f"aden_pos_{idx}",
                    "code": pos.get("contract"),
                    "name": pos.get("contract").split("_")[0] if "_" in pos.get("contract") else pos.get("contract"),
                    "type": "COIN",
                    "quantity": abs(size),
                    "entryPrice": entry_p,
                    "currentPrice": mark_p,
                    "valuation": val_usd, # natively in USD
                    "pnl": upnl, # natively in USD
                    "pnlPct": round(pnl_pct, 2),
                    "score": None,
                    "posType": pos_type
                })
            
            aden_success = True
        except Exception as e:
            print(f"[Dashboard Warning] Failed to sync with Aden Exchange: {e}")
            
        # Fallback if Aden API failed
        if not aden_success:
            coin_val_krw = db_coin_val_krw
            coin_pnl_krw = db_coin_pnl_krw
            # Append local DB coin holdings
            for row in holding_rows:
                symbol = row["stock_code"]
                is_usd = row["strategy_type"] == "vol_climax" or "_" in symbol or symbol == "GOLD_FUT"
                if is_usd:
                    val_native = row["quantity"] * row["current_price"]
                    holdings_list.append({
                        "id": str(row["id"]),
                        "code": symbol,
                        "name": row["stock_name"],
                        "type": "COIN",
                        "quantity": row["quantity"],
                        "entryPrice": row["entry_price"],
                        "currentPrice": row["current_price"],
                        "valuation": val_native,
                        "pnl": val_native - (row["quantity"] * row["entry_price"]),
                        "pnlPct": float(row["holding_return"]),
                        "score": int(row["score_at_entry"]) if row["score_at_entry"] else None,
                        "posType": "LONG"
                    })

        total_asset = cash_balance + stock_val_krw + coin_val_krw
        stock_weight = round((stock_val_krw / total_asset) * 100) if total_asset > 0 else 0
        coin_weight = round((coin_val_krw / total_asset) * 100) if total_asset > 0 else 0
        cash_weight = 100 - stock_weight - coin_weight

        # Calculate real-time profit metrics
        total_pnl = stock_pnl_krw + coin_pnl_krw
        total_purchase = total_asset - total_pnl
        total_pnl_pct = round((total_pnl / total_purchase) * 100, 2) if total_purchase > 0 else 0.0

        # 3. Fetch recent trades
        cursor.execute("""
            SELECT id, trade_date, stock_code, stock_name, transaction_type, price, quantity, amount, strategy_type 
            FROM ud_portfolio_transactions 
            ORDER BY id DESC LIMIT 5
        """)
        trade_rows = cursor.fetchall()
        
        recent_trades = []
        for r in trade_rows:
            is_buy = r["transaction_type"] == "BUY"
            pnl = (r["price"] * 0.04 * r["quantity"]) if not is_buy else None
            pnl_pct = 4.4 if not is_buy else None
            
            strategy_label = "직접 매매"
            if r["strategy_type"] == "ud_dividend":
                strategy_label = "저평가 고배당"
            elif r["strategy_type"] == "op_growth":
                strategy_label = "우량 기회 성장"
            elif r["strategy_type"] == "deep_value_contra":
                strategy_label = "낙폭과대 역발상"
            elif r["strategy_type"] == "vol_climax":
                strategy_label = "거래량 클라이맥스"

            recent_trades.append({
                "id": str(r["id"]),
                "time": f"{r['trade_date']} 15:30:00",
                "strategy": strategy_label,
                "asset": r["stock_name"],
                "type": r["transaction_type"],
                "price": r["price"],
                "quantity": r["quantity"],
                "pnl": pnl,
                "pnlPct": pnl_pct,
                "isLive": False
            })

        return {
          "totalAsset": total_asset,
          "cashBalance": cash_balance,
          "dailyReturn": total_pnl,
          "dailyReturnPct": total_pnl_pct,
          "cumulativeReturnPct": cum_return,
          "mdd": mdd_val,
          "stockWeight": stock_weight,
          "coinWeight": coin_weight,
          "cashWeight": cash_weight,
          "holdings": holdings_list,
          "recentTrades": recent_trades
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/stocks/search")
def search_stocks(q: str = "", market: str = ""):
    if not q:
        return []
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Search by code or name with market filter if provided
        query_pattern = f"%{q}%"
        if market:
            cursor.execute("""
                SELECT stock_code, stock_name, market FROM stocks
                WHERE (stock_code LIKE ? OR stock_name LIKE ?) AND is_active = 1 AND market = ?
                LIMIT 10
            """, (query_pattern, query_pattern, market.upper()))
        else:
            cursor.execute("""
                SELECT stock_code, stock_name, market FROM stocks
                WHERE (stock_code LIKE ? OR stock_name LIKE ?) AND is_active = 1
                LIMIT 10
            """, (query_pattern, query_pattern))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "code": r["stock_code"],
                "name": r["stock_name"],
                "market": r["market"]
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/transactions")
def get_transactions():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, trade_date as date, stock_code as symbol, stock_name as name, 
                   transaction_type as type, price, quantity as qty, amount, strategy_type as strategyId 
            FROM ud_portfolio_transactions 
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        txs = []
        for r in rows:
            is_usd = "_" in r["symbol"] or r["symbol"] == "GOLD_FUT" or r["symbol"].endswith("USDT")
            currency = "USD" if is_usd else "KRW"
            txs.append({
                "id": str(r["id"]),
                "date": r["date"],
                "assetClass": "COIN" if "_" in r["symbol"] and "FUT" not in r["symbol"] else "STOCK",
                "strategyId": r["strategyId"],
                "type": r["type"],
                "symbol": r["symbol"],
                "name": r["name"],
                "price": r["price"],
                "qty": r["qty"],
                "fee": 0,
                "memo": "",
                "currency": currency
            })
        return txs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/transactions")
def add_transaction(tx: TransactionCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Check asset class for targeting cash
        is_futures = tx.assetClass == "FUTURES" or tx.symbol.endswith("FUT") or ("_" in tx.symbol and tx.assetClass != "COIN")
        
        usd_rate = 1350.0
        tx_currency = tx.currency.upper() if tx.currency else "KRW"
        
        if is_futures:
            # 1. Fetch futures cash balance (USD) from bot_state
            cursor.execute("SELECT value FROM bot_state WHERE strategy = ? AND key = ? LIMIT 1", ('COMMON', 'futures_cash'))
            futures_cash_row = cursor.fetchone()
            cash = float(futures_cash_row[0]) if futures_cash_row else 10000.0
            
            # Calculate transaction amount in USD based on selected currency
            if tx_currency == "KRW":
                amount = (tx.qty * tx.price + tx.fee) / usd_rate
            else:
                amount = tx.qty * tx.price + tx.fee
            
            # Validate cash balance for buying
            if tx.type == "BUY":
                if cash < amount:
                    raise HTTPException(status_code=400, detail="예수금이 부족합니다. (선물 달러예수금 부족)")
                new_cash = cash - amount
            else:
                new_cash = cash + amount
                
            # Update futures cash balance
            cursor.execute("""
                INSERT OR REPLACE INTO bot_state (strategy, key, value)
                VALUES (?, ?, ?)
            """, ('COMMON', 'futures_cash', str(new_cash)))
            
        else:
            # STOCK / COIN (KRW based check on local status table)
            # 1. Fetch current cash balance
            cursor.execute("SELECT current_cash FROM ud_portfolio_status LIMIT 1")
            status_row = cursor.fetchone()
            cash = status_row["current_cash"] if status_row else 33337250.0

            # Calculate transaction amount in KRW based on selected currency
            if tx_currency == "USD":
                amount_krw = (tx.qty * tx.price + tx.fee) * usd_rate
            else:
                amount_krw = tx.qty * tx.price + tx.fee

            # Validate cash balance for buying
            if tx.type == "BUY":
                if cash < amount_krw:
                    raise HTTPException(status_code=400, detail="예수금이 부족합니다. (주식 원화예수금 부족)")
                new_cash = cash - amount_krw
            else:
                new_cash = cash + amount_krw

            # Update cash balance
            cursor.execute("UPDATE ud_portfolio_status SET current_cash = ?", (new_cash,))

        # 2. Insert into transactions
        cursor.execute("""
            INSERT INTO ud_portfolio_transactions (trade_date, stock_code, stock_name, transaction_type, price, quantity, amount, score, strategy_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tx.date, tx.symbol, tx.name, tx.type, tx.price, tx.qty, tx.qty * tx.price, 0.0, tx.strategyId))

        # 3. Update holdings
        cursor.execute("""
            SELECT id, quantity, entry_price FROM ud_portfolio_holdings 
            WHERE stock_code = ? AND status = 'ACTIVE' LIMIT 1
        """, (tx.symbol,))
        holding_row = cursor.fetchone()

        if tx.type == "BUY":
            if holding_row:
                old_qty = holding_row["quantity"]
                old_entry = holding_row["entry_price"]
                new_qty = old_qty + tx.qty
                new_entry = ((old_qty * old_entry) + (tx.qty * tx.price)) / new_qty
                
                # Mock current prices
                current_prices = {"005930": 75200, "000660": 182500, "035720": 47200, "BTC_USDT": 65140, "ETH_USDT": 3380, "GOLD_FUT": 2310.50}
                curr_price = current_prices.get(tx.symbol, new_entry)
                valuation = new_qty * curr_price
                pnl_pct = ((curr_price - new_entry) / new_entry) * 100 if new_entry > 0 else 0

                cursor.execute("""
                    UPDATE ud_portfolio_holdings 
                    SET quantity = ?, entry_price = ?, current_price = ?, valuation = ?, holding_return = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_qty, new_entry, curr_price, valuation, pnl_pct, holding_row["id"]))
            else:
                current_prices = {"005930": 75200, "000660": 182500, "035720": 47200, "BTC_USDT": 65140, "ETH_USDT": 3380, "GOLD_FUT": 2310.50}
                curr_price = current_prices.get(tx.symbol, tx.price)
                valuation = tx.qty * curr_price
                pnl_pct = ((curr_price - tx.price) / tx.price) * 100 if tx.price > 0 else 0

                cursor.execute("""
                    INSERT INTO ud_portfolio_holdings (stock_code, stock_name, entry_date, entry_price, quantity, current_price, valuation, holding_return, score_at_entry, status, strategy_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tx.symbol, tx.name, tx.date, tx.price, tx.qty, curr_price, valuation, pnl_pct, 0.0, "ACTIVE", tx.strategyId))
        else:
            # Sell Transaction
            if holding_row:
                old_qty = holding_row["quantity"]
                new_qty = old_qty - tx.qty
                if new_qty <= 0:
                    cursor.execute("""
                        UPDATE ud_portfolio_holdings 
                        SET status = 'EXIT', exit_date = ?, exit_price = ?, quantity = 0, valuation = 0, holding_return = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (tx.date, tx.price, holding_row["id"]))
                else:
                    curr_price = holding_row["entry_price"]  # default
                    current_prices = {"005930": 75200, "000660": 182500, "035720": 47200, "BTC_USDT": 65140, "ETH_USDT": 3380, "GOLD_FUT": 2310.50}
                    curr_price = current_prices.get(tx.symbol, curr_price)
                    valuation = new_qty * curr_price
                    entry_price = holding_row["entry_price"]
                    pnl_pct = ((curr_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

                    cursor.execute("""
                        UPDATE ud_portfolio_holdings 
                        SET quantity = ?, valuation = ?, holding_return = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_qty, valuation, pnl_pct, holding_row["id"]))
            else:
                raise HTTPException(status_code=400, detail="보유하지 않은 종목의 매도 요청입니다.")

        conn.commit()
        return {"status": "success", "message": "Transaction added successfully."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/transactions/{id}")
def delete_transaction(id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch transaction details
        cursor.execute("SELECT stock_code, transaction_type, price, quantity, strategy_type FROM ud_portfolio_transactions WHERE id = ?", (id,))
        tx_row = cursor.fetchone()
        if not tx_row:
            raise HTTPException(status_code=404, detail="거래 기록을 찾을 수 없습니다.")
        
        symbol = tx_row["stock_code"]
        tx_type = tx_row["transaction_type"]
        price = tx_row["price"]
        qty = tx_row["quantity"]
        strategy_id = tx_row["strategy_type"]

        is_usd = strategy_id == "vol_climax" or "_" in symbol or symbol == "GOLD_FUT"
        rate = 1350.0 if is_usd else 1.0
        amount_krw = (qty * price) * rate

        # 2. Fetch current cash balance
        cursor.execute("SELECT current_cash FROM ud_portfolio_status LIMIT 1")
        status_row = cursor.fetchone()
        cash = status_row["current_cash"] if status_row else 33337250.0

        # Reverse cash adjustment
        if tx_type == "BUY":
            new_cash = cash + amount_krw
        else:
            new_cash = cash - amount_krw

        cursor.execute("UPDATE ud_portfolio_status SET current_cash = ?", (new_cash,))

        # 3. Revert holding changes
        cursor.execute("SELECT id, quantity, entry_price FROM ud_portfolio_holdings WHERE stock_code = ? AND status = 'ACTIVE' LIMIT 1", (symbol,))
        holding_row = cursor.fetchone()

        if tx_type == "BUY":
            # If we bought it, delete/reduce the active holding
            if holding_row:
                old_qty = holding_row["quantity"]
                new_qty = old_qty - qty
                if new_qty <= 0:
                    cursor.execute("DELETE FROM ud_portfolio_holdings WHERE id = ?", (holding_row["id"],))
                else:
                    entry_price = holding_row["entry_price"]
                    current_prices = {"005930": 75200, "000660": 182500, "035720": 47200, "BTC_USDT": 65140, "ETH_USDT": 3380, "GOLD_FUT": 2310.50}
                    curr_price = current_prices.get(symbol, entry_price)
                    valuation = new_qty * curr_price
                    pnl_pct = ((curr_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

                    cursor.execute("""
                        UPDATE ud_portfolio_holdings 
                        SET quantity = ?, valuation = ?, holding_return = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_qty, valuation, pnl_pct, holding_row["id"]))
        else:
            # If we sold it, restore the sold quantity
            if holding_row:
                old_qty = holding_row["quantity"]
                new_qty = old_qty + qty
                entry_price = holding_row["entry_price"]
                current_prices = {"005930": 75200, "000660": 182500, "035720": 47200, "BTC_USDT": 65140, "ETH_USDT": 3380, "GOLD_FUT": 2310.50}
                curr_price = current_prices.get(symbol, entry_price)
                valuation = new_qty * curr_price
                pnl_pct = ((curr_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

                cursor.execute("""
                    UPDATE ud_portfolio_holdings 
                    SET quantity = ?, valuation = ?, holding_return = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_qty, valuation, pnl_pct, holding_row["id"]))
            else:
                # If the holding was closed, set it back to active
                cursor.execute("SELECT id, entry_price FROM ud_portfolio_holdings WHERE stock_code = ? AND status = 'EXIT' ORDER BY id DESC LIMIT 1", (symbol,))
                exited_row = cursor.fetchone()
                if exited_row:
                    entry_price = exited_row["entry_price"]
                    current_prices = {"005930": 75200, "000660": 182500, "035720": 47200, "BTC_USDT": 65140, "ETH_USDT": 3380, "GOLD_FUT": 2310.50}
                    curr_price = current_prices.get(symbol, entry_price)
                    valuation = qty * curr_price
                    pnl_pct = ((curr_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

                    cursor.execute("""
                        UPDATE ud_portfolio_holdings 
                        SET status = 'ACTIVE', quantity = ?, valuation = ?, holding_return = ?, exit_date = NULL, exit_price = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (qty, valuation, pnl_pct, exited_row["id"]))

        # 4. Delete transaction
        cursor.execute("DELETE FROM ud_portfolio_transactions WHERE id = ?", (id,))
        conn.commit()
        return {"status": "success", "message": "Transaction deleted and reversed."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/cash")
def update_cash(body: CashUpdate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE ud_portfolio_status SET current_cash = ?", (body.cash,))
        conn.commit()
        return {"status": "success", "message": "Cash balance updated successfully."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ----------------- STOCK PRICE SYNC ROUTINES -----------------
is_syncing = False

from app.pipelines.sync_yahoo_futures_pipeline import sync_yahoo_futures

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

@app.on_event("startup")
def on_startup():
    # Start catchup sync in a background thread so it doesn't block FastAPI server startup
    asyncio.create_task(asyncio.to_thread(run_catchup_sync))
    asyncio.create_task(schedule_daily_sync())

@app.post("/api/stocks/sync")
def trigger_stock_sync(background_tasks: BackgroundTasks):
    global is_syncing
    if is_syncing:
        raise HTTPException(status_code=409, detail="이미 주가 데이터 동기화가 진행 중입니다.")
        
    def run_manual_sync():
        global is_syncing
        is_syncing = True
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
            is_syncing = False
            
    background_tasks.add_task(run_manual_sync)
    return {"status": "success", "message": "주가 동기화가 백그라운드에서 시작되었습니다."}

@app.get("/api/stocks/sync/status")
def get_sync_status():
    global is_syncing
    return {"isSyncing": is_syncing}

@app.get("/api/stocks")
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

@app.get("/api/stocks/{stock_code}")
def get_stock_detail(stock_code: str):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch stock master
        cursor.execute("""
            SELECT stock_code, stock_name, market, sector, listed_date, listed_shares 
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

            # 2. Fetch 120-day historical prices for candle chart
            price_history = []
            try:
                from app.clients.aden_client import AdenClient
                client = AdenClient()
                # Fetch 120 daily candles (1d interval)
                candles = client.get_candlesticks_cached(contract=stock_code, interval='1d', limit=120)
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
        
        financials = []
        for f in financial_rows:
            roe = None
            if f["total_equity"] and f["net_income"] and f["total_equity"] != 0:
                roe = (f["net_income"] / f["total_equity"]) * 100
            financials.append({
                "year": f["bsns_year"],
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

        # 4. Fetch 120-day historical prices for candle chart
        cursor.execute("""
            SELECT trade_date, open_price, high_price, low_price, close_price, volume
            FROM daily_prices 
            WHERE stock_code = ? 
            ORDER BY trade_date DESC LIMIT 120
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

@app.get("/api/futures/cot")
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

@app.get("/api/macro/calendar")
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

@app.get("/api/macro/indicators")
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


@app.get("/api/logs")
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


@app.get("/api/accounts")
def get_accounts():
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Fetch STOCK cash, total_return & mdd from ud_portfolio_status
        cursor.execute("SELECT current_cash, total_return, mdd FROM ud_portfolio_status LIMIT 1")
        status_row = cursor.fetchone()
        cash_balance = status_row["current_cash"] if status_row else 33337250.0
        cum_return = status_row["total_return"] if status_row else 24.8
        mdd_val = status_row["mdd"] if status_row else -4.2

        # 2. Fetch FUTURES cash from bot_state
        cursor.execute("SELECT value FROM bot_state WHERE strategy = ? AND key = ? LIMIT 1", ('COMMON', 'futures_cash'))
        futures_cash_row = cursor.fetchone()
        futures_cash_usd = float(futures_cash_row[0]) if futures_cash_row else 10000.0

        # 3. Fetch active holdings from Local DB with market info
        cursor.execute("""
            SELECT h.stock_code, h.stock_name, h.entry_price, h.quantity, h.current_price, h.holding_return, s.market 
            FROM ud_portfolio_holdings h
            LEFT JOIN stocks s ON h.stock_code = s.stock_code
            WHERE h.status = 'ACTIVE'
        """)
        holding_rows = cursor.fetchall()
        
        stocks_list = []
        stock_val_krw = 0
        stock_pnl_krw = 0
        
        futures_list = []
        futures_val_usd = 0
        futures_pnl_usd = 0
        
        usd_rate = 1350.0

        for row in holding_rows:
            symbol = row["stock_code"]
            market = row["market"] or ""
            
            # Classify by s.market
            if market == "FUTURES" or symbol.endswith("FUT") or ("_" in symbol and market != "COIN"):
                # Global Futures Asset (calculated in USD natively)
                val_native = row["quantity"] * row["current_price"]
                futures_val_usd += val_native
                pnl_usd = row["quantity"] * (row["current_price"] - row["entry_price"])
                futures_pnl_usd += pnl_usd
                
                futures_list.append({
                    "code": symbol,
                    "name": row["stock_name"],
                    "quantity": row["quantity"],
                    "entryPrice": row["entry_price"],
                    "currentPrice": row["current_price"],
                    "valuation": val_native,
                    "pnlPct": float(row["holding_return"])
                })
            elif market == "COIN" or symbol.endswith("_USDT"):
                # Skip COIN assets from local holdings because we read coin positions from Aden Exchange API
                continue
            else:
                # KRX Stock Asset
                val = row["quantity"] * row["current_price"]
                stock_val_krw += val
                stock_pnl_krw += row["quantity"] * (row["current_price"] - row["entry_price"])
                stocks_list.append({
                    "code": symbol,
                    "name": row["stock_name"],
                    "quantity": row["quantity"],
                    "entryPrice": row["entry_price"],
                    "currentPrice": row["current_price"],
                    "valuation": val,
                    "pnlPct": float(row["holding_return"])
                })

        # 4. Fetch Aden Exchange Account (Coin)
        coin_total_usd = 0.0
        coin_available_usd = 0.0
        coin_upnl_usd = 0.0
        positions_list = []
        
        try:
            from app.clients.aden_client import AdenClient
            client = AdenClient()
            aden_acc = client.get_account()
            coin_total_usd = float(aden_acc.get("total", 0))
            coin_available_usd = float(aden_acc.get("available", 0))
            coin_upnl_usd = float(aden_acc.get("unrealised_pnl", 0))
            
            aden_pos = client.get_positions()
            for pos in aden_pos:
                size = float(pos.get("size", 0))
                if size == 0:
                    continue
                entry_p = float(pos.get("entry_price", 0))
                mark_p = float(pos.get("mark_price", 0))
                
                pos_type = "SHORT" if size < 0 else "LONG"
                if pos_type == "SHORT":
                    pnl_pct = ((entry_p - mark_p) / entry_p) * 100 if entry_p > 0 else 0.0
                else:
                    pnl_pct = ((mark_p - entry_p) / entry_p) * 100 if entry_p > 0 else 0.0
                
                positions_list.append({
                    "contract": pos.get("contract"),
                    "size": abs(size),
                    "posType": pos_type,
                    "entryPrice": entry_p,
                    "markPrice": mark_p,
                    "value": float(pos.get("value", 0)),
                    "unrealisedPnl": float(pos.get("unrealised_pnl", 0)),
                    "pnlPct": round(pnl_pct, 2)
                })
        except Exception as e:
            print(f"[Accounts Warning] Failed to fetch Aden account details: {e}")

        # Real-time portfolio totals
        coin_total_krw = coin_total_usd * usd_rate
        coin_pnl_krw = coin_upnl_usd * usd_rate
        
        futures_total_usd = futures_cash_usd + futures_val_usd
        futures_total_krw = futures_total_usd * usd_rate
        futures_pnl_krw = futures_pnl_usd * usd_rate
        
        stock_total_krw = cash_balance + stock_val_krw
        
        total_portfolio_asset = stock_total_krw + coin_total_krw + futures_total_krw
        
        # Calculate Account Weights
        stock_w = round((stock_total_krw / total_portfolio_asset) * 100) if total_portfolio_asset > 0 else 0
        coin_w = round((coin_total_krw / total_portfolio_asset) * 100) if total_portfolio_asset > 0 else 0
        futures_w = round((futures_total_krw / total_portfolio_asset) * 100) if total_portfolio_asset > 0 else 0
        
        # Normalize weights (sum to 100%)
        if total_portfolio_asset > 0:
            futures_w = 100 - stock_w - coin_w

        total_pnl = stock_pnl_krw + coin_pnl_krw + futures_pnl_krw
        total_purchase = total_portfolio_asset - total_pnl
        total_pnl_pct = round((total_pnl / total_purchase) * 100, 2) if total_purchase > 0 else 0.0

        return {
            "metrics": {
                "cumulativeReturnPct": cum_return,
                "mdd": mdd_val,
                "dailyReturn": total_pnl,
                "dailyReturnPct": total_pnl_pct,
                "stockWeight": stock_w,
                "coinWeight": coin_w,
                "cashWeight": futures_w, # map cashWeight to futures_w for legacy chart compat
                "futuresWeight": futures_w,
                "totalAsset": total_portfolio_asset
            },
            "stockAccount": {
                "cash": cash_balance,
                "valuation": stock_val_krw,
                "total": stock_total_krw,
                "holdings": stocks_list
            },
            "coinAccount": {
                "usdRate": usd_rate,
                "cashUsd": coin_available_usd,
                "valuationUsd": coin_total_usd - coin_available_usd,
                "totalUsd": coin_total_usd,
                "totalKrw": coin_total_krw,
                "unrealisedPnlUsd": coin_upnl_usd,
                "positions": positions_list
            },
            "futuresAccount": {
                "cashUsd": futures_cash_usd,
                "valuationUsd": futures_val_usd,
                "totalUsd": futures_total_usd,
                "totalKrw": futures_total_krw,
                "unrealisedPnlUsd": futures_pnl_usd,
                "holdings": futures_list
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.put("/api/accounts/cash")
def update_account_cash(payload: AccountCashUpdate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        if payload.accountType == "STOCK":
            # Update local portfolio cash balance in status table
            cursor.execute("UPDATE ud_portfolio_status SET current_cash = ?", (payload.amount,))
            conn.commit()
            print(f"[System] Updated Stock cash to {payload.amount}")
        elif payload.accountType == "FUTURES":
            # Update futures cash in bot_state table
            cursor.execute("""
                INSERT OR REPLACE INTO bot_state (strategy, key, value)
                VALUES (?, ?, ?)
            """, ('COMMON', 'futures_cash', str(payload.amount)))
            conn.commit()
            print(f"[System] Updated Futures cash to {payload.amount}")
        else:
            raise HTTPException(status_code=400, detail="Invalid account type")
        return {"status": "success", "amount": payload.amount}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
