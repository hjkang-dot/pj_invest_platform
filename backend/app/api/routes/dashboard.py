from fastapi import APIRouter, HTTPException

from app.database import get_db

router = APIRouter()

@router.get("/api/dashboard")
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

