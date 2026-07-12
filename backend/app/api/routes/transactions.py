from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas import CashUpdate, TransactionCreate

router = APIRouter()

@router.get("/api/stocks/search")
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


@router.get("/api/transactions")
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

@router.post("/api/transactions")
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

@router.delete("/api/transactions/{id}")
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

@router.put("/api/cash")
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

