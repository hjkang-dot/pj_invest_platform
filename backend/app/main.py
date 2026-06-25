import os
import sqlite3
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

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

class CashUpdate(BaseModel):
    cash: float

# Initialize Database on Startup
init_default_data()

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

        # 2. Fetch active holdings
        cursor.execute("""
            SELECT id, stock_code, stock_name, entry_price, quantity, current_price, valuation, holding_return, score_at_entry, strategy_type 
            FROM ud_portfolio_holdings 
            WHERE status = 'ACTIVE'
        """)
        holding_rows = cursor.fetchall()
        
        holdings_list = []
        stock_val_krw = 0
        coin_val_krw = 0
        usd_rate = 1350.0

        for row in holding_rows:
            symbol = row["stock_code"]
            is_usd = row["strategy_type"] == "vol_climax" or "_" in symbol or symbol == "GOLD_FUT"
            rate = usd_rate if is_usd else 1.0
            
            val_native = row["quantity"] * row["current_price"]
            val_krw = val_native * rate

            if is_usd:
                coin_val_krw += val_krw
            else:
                stock_val_krw += val_krw

            holdings_list.append({
                "id": str(row["id"]),
                "code": symbol,
                "name": row["stock_name"],
                "type": "COIN" if is_usd else "STOCK",
                "quantity": row["quantity"],
                "entryPrice": row["entry_price"],
                "currentPrice": row["current_price"],
                "valuation": val_native,  # Frontend format
                "pnl": val_native - (row["quantity"] * row["entry_price"]),
                "pnlPct": float(row["holding_return"]),
                "score": int(row["score_at_entry"]) if row["score_at_entry"] else None,
                "posType": "LONG" if is_usd else None
            })

        total_asset = cash_balance + stock_val_krw + coin_val_krw
        stock_weight = round((stock_val_krw / total_asset) * 100) if total_asset > 0 else 0
        coin_weight = round((coin_val_krw / total_asset) * 100) if total_asset > 0 else 0
        cash_weight = 100 - stock_weight - coin_weight

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
          "dailyReturn": 2430000,
          "dailyReturnPct": 1.6,
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
            txs.append({
                "id": str(r["id"]),
                "date": r["date"],
                "assetClass": "COIN" if "_" in r["symbol"] or r["symbol"] == "GOLD_FUT" else "STOCK",
                "strategyId": r["strategyId"],
                "type": r["type"],
                "symbol": r["symbol"],
                "name": r["name"],
                "price": r["price"],
                "qty": r["qty"],
                "fee": 0,
                "memo": ""
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
        # 1. Fetch current cash balance
        cursor.execute("SELECT current_cash FROM ud_portfolio_status LIMIT 1")
        status_row = cursor.fetchone()
        cash = status_row["current_cash"] if status_row else 33337250.0

        is_usd = tx.assetClass in ["COIN", "FUTURES"] or "_" in tx.symbol or tx.symbol == "GOLD_FUT"
        rate = 1350.0 if is_usd else 1.0
        amount_krw = (tx.qty * tx.price + tx.fee) * rate

        # Validate cash balance for buying
        if tx.type == "BUY":
            if cash < amount_krw:
                raise HTTPException(status_code=400, detail="예수금이 부족합니다.")
            new_cash = cash - amount_krw
        else:
            new_cash = cash + amount_krw

        # 2. Insert into transactions
        cursor.execute("""
            INSERT INTO ud_portfolio_transactions (trade_date, stock_code, stock_name, transaction_type, price, quantity, amount, score, strategy_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tx.date, tx.symbol, tx.name, tx.type, tx.price, tx.qty, tx.qty * tx.price, 0.0, tx.strategyId))

        # 3. Update cash balance
        cursor.execute("UPDATE ud_portfolio_status SET current_cash = ?", (new_cash,))

        # 4. Update holdings
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

def sync_yahoo_futures():
    print("[Yahoo Futures Sync] Starting sync of futures and overseas stock assets...")
    ticker_mapping = {
        "XAU_USDT": "GC=F",
        "CL_USDT": "CL=F",
        "NAS100_USDT": "NQ=F",
        "AAPL_USDT": "AAPL",
        "TSLA_USDT": "TSLA"
    }
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT stock_code, stock_name, market, sector FROM stocks WHERE market = 'FUTURES'")
        stocks_rows = cursor.fetchall()
        stock_meta = {r["stock_code"]: dict(r) for r in stocks_rows}
        
        import urllib.request
        import json
        import datetime
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for code, yf_ticker in ticker_mapping.items():
            if code not in stock_meta:
                continue
                
            meta = stock_meta[code]
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}?range=180d&interval=1d"
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_data = json.loads(response.read().decode())
                    results = res_data.get("chart", {}).get("result", [])
                    if not results:
                        continue
                    chart_data = results[0]
                    timestamps = chart_data.get("timestamp", [])
                    quotes = chart_data.get("indicators", {}).get("quote", [{}])[0]
                    
                    opens = quotes.get("open", [])
                    highs = quotes.get("high", [])
                    lows = quotes.get("low", [])
                    closes = quotes.get("close", [])
                    volumes = quotes.get("volume", [])
                    
                    rows_to_insert = []
                    for idx in range(len(timestamps)):
                        t = timestamps[idx]
                        o = opens[idx]
                        h = highs[idx]
                        l = lows[idx]
                        c = closes[idx]
                        v = volumes[idx] if idx < len(volumes) and volumes[idx] is not None else 0
                        
                        if o is None or h is None or l is None or c is None:
                            continue
                            
                        dt = datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=9)))
                        trade_date = dt.strftime("%Y%m%d")
                        
                        if idx > 0 and closes[idx - 1] is not None:
                            prev_close = closes[idx - 1]
                            price_change = c - prev_close
                            change_rate = (price_change / prev_close) * 100
                        else:
                            price_change = c - o
                            change_rate = (price_change / o) * 100 if o > 0 else 0
                            
                        listed_shares = 1000000
                        market_cap = c * listed_shares
                        
                        rows_to_insert.append((
                            trade_date,
                            code,
                            meta["stock_name"],
                            meta["market"],
                            None,
                            float(o),
                            float(h),
                            float(l),
                            float(c),
                            float(price_change),
                            float(change_rate),
                            int(v),
                            float(c * v),
                            float(market_cap),
                            int(listed_shares)
                        ))
                        
                    if rows_to_insert:
                        cursor.executemany("""
                            INSERT OR REPLACE INTO daily_prices (
                                trade_date, stock_code, stock_name, market, section,
                                open_price, high_price, low_price, close_price,
                                price_change, change_rate, volume, trading_value,
                                market_cap, listed_shares
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, rows_to_insert)
                        conn.commit()
                        print(f"[Yahoo Futures Sync] Synced and cached {len(rows_to_insert)} daily candles for {code} ({yf_ticker})")
            except Exception as e:
                print(f"[Yahoo Futures Sync] Error syncing {code} ({yf_ticker}): {e}")
    except Exception as e:
        print(f"[Yahoo Futures Sync] Query failed: {e}")
    finally:
        conn.close()
    print("[Yahoo Futures Sync] Finished syncing futures and overseas stock assets.")

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

@app.on_event("startup")
def on_startup():
    # Start catchup sync in a background thread so it doesn't block FastAPI server startup
    asyncio.create_task(asyncio.to_thread(run_catchup_sync))

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
