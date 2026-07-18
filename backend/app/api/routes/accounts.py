from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas import AccountCashUpdate

router = APIRouter()

@router.get("/api/accounts")
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
                unrealised_pnl = float(pos.get("unrealised_pnl", 0))
                margin_val = float(pos.get("margin", 0)) or float(pos.get("initial_margin", 0))
                leverage = int(float(pos.get("leverage", pos.get("lever", 1))))
                liq_price = float(pos.get("liq_price", 0))
                
                pos_type = "SHORT" if size < 0 else "LONG"
                
                # ROE % (Return on Equity/Margin)
                if margin_val > 0:
                    pnl_pct = (unrealised_pnl / margin_val) * 100
                else:
                    if pos_type == "SHORT":
                        pnl_pct = ((entry_p - mark_p) / entry_p) * 100 * leverage if entry_p > 0 else 0.0
                    else:
                        pnl_pct = ((mark_p - entry_p) / entry_p) * 100 * leverage if entry_p > 0 else 0.0
                
                positions_list.append({
                    "contract": pos.get("contract"),
                    "size": abs(size),
                    "posType": pos_type,
                    "leverage": leverage,
                    "entryPrice": entry_p,
                    "markPrice": mark_p,
                    "value": float(pos.get("value", 0)),
                    "margin": margin_val,
                    "liqPrice": liq_price,
                    "unrealisedPnl": unrealised_pnl,
                    "pnlPct": round(pnl_pct, 2)
                })
        except Exception as e:
            print(f"[Accounts Warning] Failed to fetch Aden account details: {e}")

        # 5. Fetch KIS (한국투자증권) Account if configured
        kis_account = None
        try:
            from app.clients.kis_client import KISClient
            kis_client = KISClient()
            if kis_client.is_configured() and kis_client.cano:
                kis_account = kis_client.get_account_balance()
        except Exception as e:
            print(f"[Accounts Warning] Failed to fetch KIS account details: {e}")

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
            },
            "kisAccount": kis_account
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.put("/api/accounts/cash")
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

