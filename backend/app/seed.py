from app.database import get_db

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

        # Check and populate default strategy backtest statistics
        cursor.execute("SELECT COUNT(*) FROM strategy_backtests")
        if cursor.fetchone()[0] == 0:
            print("[System] Inserting default strategy backtest statistics...")
            backtests = [
                ("ud_dividend", 12.4, 6.2, 1.65, 68.0, 2.1, 142, "M10 80 Q30 75, 50 68 T90 55 T130 50 T170 38 T210 25 T250 18 T290 8"),
                ("op_growth", 24.8, 8.5, 1.95, 62.0, 2.3, 84, "M10 80 Q30 78, 50 72 T90 62 T130 52 T170 45 T210 32 T250 15 T290 -5"),
                ("sector_growth", 19.2, 9.8, 1.72, 60.0, 2.05, 95, "M10 80 Q30 76, 50 70 T90 58 T130 55 T170 42 T210 30 T250 20 T290 5"),
                ("deep_value_contra", 18.5, 12.4, 1.42, 59.0, 1.95, 61, "M10 80 Q30 85, 50 82 T90 70 T130 75 T170 58 T210 65 T250 42 T290 20"),
                ("vol_climax", 32.1, 18.2, 1.82, 55.0, 2.4, 112, "M10 80 Q30 78, 50 85 T90 62 T130 65 T170 40 T210 42 T250 12 T290 -8")
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO strategy_backtests (strategy_id, cum_return, mdd, sharpe, win_rate, profit_factor, total_trades, chart_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, backtests)
            conn.commit()
    except Exception as e:
        print(f"[System] Failed to auto-populate DB: {e}")
    finally:
        conn.close()

