import sqlite3
import os

# Resolves C:\pyproject\pj_invest_platform\data\invest_platform.db
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "invest_platform.db"))

def table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None

def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())

def add_column_if_missing(cursor, table_name: str, column_name: str, column_definition: str):
    if table_exists(cursor, table_name) and not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

def migrate_db(conn):
    """
    Applies lightweight SQLite schema migrations for existing local databases.
    Keep migrations additive so user data remains untouched.
    """
    cursor = conn.cursor()
    add_column_if_missing(cursor, "strategy_backtests", "simulated_trades", "TEXT")

def init_db(db_path=DB_PATH):
    """
    Initializes the SQLite database and creates the required tables if not exists.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ------------------ 1. COIN & COMMON TABLES ------------------
    
    # Create candlesticks table (For Coin K-lines)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candlesticks (
            contract TEXT,
            interval TEXT,
            t INTEGER,
            o REAL,
            h REAL,
            l REAL,
            c REAL,
            v REAL,
            sum REAL,
            PRIMARY KEY (contract, interval, t)
        )
    """)
    
    # Create trades table (Common Trade events for both assets)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            strategy TEXT,
            contract TEXT,
            type TEXT,
            pos_type TEXT,
            price REAL,
            size REAL,
            fee REAL,
            pnl REAL,
            reason TEXT,
            mode TEXT,
            balance REAL
        )
    """)
    
    # Create logs table (Common System & Strategy Logs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            strategy TEXT,
            message TEXT
        )
    """)
    
    # Create bot_state table (For Coin/Stock virtual account variables)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            strategy TEXT,
            key TEXT,
            value TEXT,
            PRIMARY KEY (strategy, key)
        )
    """)
    
    # ------------------ 2. STOCK TABLES (KRX & DART) ------------------
    
    # Create stocks table (KRX listed stocks master info)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL UNIQUE,
            stock_name TEXT NOT NULL,
            market TEXT NOT NULL,
            security_group TEXT,
            sector TEXT,
            dart_corp_code TEXT,
            listed_date TEXT,
            listed_shares INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create daily_prices table (Stock daily prices data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            market TEXT NOT NULL,
            section TEXT,
            open_price INTEGER NOT NULL,
            high_price INTEGER NOT NULL,
            low_price INTEGER NOT NULL,
            close_price INTEGER NOT NULL,
            price_change INTEGER NOT NULL,
            change_rate REAL NOT NULL,
            volume INTEGER NOT NULL,
            trading_value INTEGER NOT NULL,
            market_cap INTEGER NOT NULL,
            listed_shares INTEGER NOT NULL,
            last_synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (trade_date, stock_code)
        )
    """)
    
    # Create index on daily_prices for speed queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_prices_stock_code_trade_date
        ON daily_prices (stock_code, trade_date)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_prices_trade_date
        ON daily_prices (trade_date)
    """)
    
    # Create company_financials table (DART financial details & dividends)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corp_code TEXT NOT NULL,
            stock_code TEXT,
            bsns_year INTEGER NOT NULL,
            fs_div TEXT,
            fs_nm TEXT,
            currency TEXT,
            fiscal_period TEXT NOT NULL,
            current_assets REAL,
            non_current_assets REAL,
            total_assets REAL,
            current_liabilities REAL,
            non_current_liabilities REAL,
            total_liabilities REAL,
            total_equity REAL,
            revenue REAL,
            operating_income REAL,
            net_income REAL,
            debt_ratio REAL,
            current_ratio REAL,
            equity_ratio REAL,
            operating_margin REAL,
            net_margin REAL,
            par_value REAL,
            eps REAL,
            cash_dividend_yield REAL,
            cash_dividend_per_share REAL,
            cash_dividend_total REAL,
            cash_dividend_payout_ratio REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (corp_code, fiscal_period)
        )
    """)
    
    # Create index on company_financials
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_company_financials_corp_code_fiscal_period
        ON company_financials (corp_code, fiscal_period)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_company_financials_stock_code
        ON company_financials (stock_code)
    """)
    
    # Create market_closed_dates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_closed_dates (
            trade_date TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create stock_evaluations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            business_year INTEGER NOT NULL,
            base_date TEXT NOT NULL,
            strategy_type TEXT NOT NULL DEFAULT 'DIVIDEND',
            close_price INTEGER,
            market_cap INTEGER,
            net_income REAL,
            total_equity REAL,
            debt_ratio REAL,
            roe REAL,
            per REAL,
            pbr REAL,
            dividend_yield REAL,
            cash_dividend_per_share REAL,
            payout_ratio REAL,
            dividend_years INTEGER,
            dividend_decrease_count INTEGER,
            current_ratio REAL,
            revenue_growth REAL,
            operating_income_growth REAL,
            eps_growth REAL,
            financial_stability_score REAL,
            growth_score REAL,
            undervaluation_score REAL,
            shareholder_return_score REAL,
            market_governance_score REAL,
            total_score REAL,
            is_candidate INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (stock_code, business_year, base_date, strategy_type)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_evaluations_stock_code
        ON stock_evaluations (stock_code)
    """)
    
    # ------------------ 3. STOCK PORTFOLIO TABLES ------------------
    
    # Create ud_portfolio_status table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ud_portfolio_status (
            strategy_type TEXT PRIMARY KEY,
            initial_balance REAL NOT NULL,
            current_cash REAL NOT NULL,
            current_valuation REAL NOT NULL,
            total_asset REAL NOT NULL,
            mdd REAL NOT NULL DEFAULT 0.0,
            total_return REAL NOT NULL DEFAULT 0.0,
            win_rate REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create ud_portfolio_holdings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ud_portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            entry_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            current_price REAL NOT NULL,
            valuation REAL NOT NULL,
            holding_return REAL NOT NULL,
            score_at_entry REAL,
            exit_date TEXT,
            exit_price REAL,
            score_at_exit REAL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            strategy_type TEXT NOT NULL DEFAULT 'DIVIDEND',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create ud_portfolio_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ud_portfolio_history (
            trade_date TEXT NOT NULL,
            strategy_type TEXT NOT NULL DEFAULT 'DIVIDEND',
            cash REAL NOT NULL,
            valuation REAL NOT NULL,
            total_asset REAL NOT NULL,
            daily_return REAL NOT NULL,
            drawdown REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (trade_date, strategy_type)
        )
    """)
    
    # Create ud_portfolio_transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ud_portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            transaction_type TEXT NOT NULL, -- 'BUY' or 'SELL'
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            amount REAL NOT NULL,
            score REAL,
            strategy_type TEXT NOT NULL DEFAULT 'DIVIDEND',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create cftc_cot table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cftc_cot (
            trade_date TEXT,
            contract_code TEXT,
            contract_name TEXT,
            open_interest INTEGER,
            noncommercial_long INTEGER,
            noncommercial_short INTEGER,
            commercial_long INTEGER,
            commercial_short INTEGER,
            PRIMARY KEY (trade_date, contract_code)
        )
    """)
    
    # Create macro_indicators table (For macroeconomic timeseries data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_indicators (
            trade_date TEXT,
            series_id TEXT,
            value REAL,
            PRIMARY KEY (trade_date, series_id)
        )
    """)
    
    # Create macro_calendar table (For macroeconomic calendar schedule & actuals)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_calendar (
            event_date TEXT,
            event_time TEXT,
            country TEXT,
            event_name TEXT,
            impact TEXT,
            actual TEXT,
            forecast TEXT,
            previous TEXT,
            PRIMARY KEY (event_date, event_name, country)
        )
    """)

    # Create strategy_backtests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategy_backtests (
            strategy_id TEXT PRIMARY KEY,
            cum_return REAL NOT NULL,
            mdd REAL NOT NULL,
            sharpe REAL NOT NULL,
            win_rate REAL NOT NULL,
            profit_factor REAL NOT NULL,
            total_trades INTEGER NOT NULL,
            chart_path TEXT NOT NULL,
            simulated_trades TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    migrate_db(conn)
    
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized successfully at: {db_path}")

# ==================== COMMON HELPER FUNCTIONS ====================

def save_trade(strategy: str, trade_event: dict, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (time, strategy, contract, type, pos_type, price, size, fee, pnl, reason, mode, balance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade_event.get('time'),
        strategy,
        trade_event.get('contract'),
        trade_event.get('type'),
        trade_event.get('pos_type'),
        float(trade_event.get('price', 0.0)),
        float(trade_event.get('size', 0.0)),
        float(trade_event.get('fee', 0.0)),
        float(trade_event.get('pnl', 0.0)),
        trade_event.get('reason', ''),
        trade_event.get('mode', 'Dry-run'),
        float(trade_event.get('balance', 0.0))
    ))
    conn.commit()
    conn.close()

def get_trades(strategy: str, limit: int = 100, db_path=DB_PATH) -> list:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time, contract, type, pos_type, price, size, fee, pnl, reason, mode, balance 
        FROM trades 
        WHERE strategy = ? 
        ORDER BY time DESC 
        LIMIT ?
    """, (strategy, limit))
    rows = cursor.fetchall()
    conn.close()
    trades = [dict(row) for row in rows]
    trades.reverse()
    return trades

def save_log(strategy: str, message: str, db_path=DB_PATH):
    import datetime
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO logs (timestamp, strategy, message)
        VALUES (?, ?, ?)
    """, (timestamp, strategy, message))
    conn.commit()
    conn.close()

def get_logs(strategy: str, limit: int = 500, db_path=DB_PATH) -> list:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, message 
        FROM logs 
        WHERE strategy = ? 
        ORDER BY id DESC 
        LIMIT ?
    """, (strategy, limit))
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

def get_bot_state(strategy: str, key: str, default: str = None, db_path=DB_PATH) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT value FROM bot_state 
        WHERE strategy = ? AND key = ?
    """, (strategy, key))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return default

def set_bot_state(strategy: str, key: str, value: str, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO bot_state (strategy, key, value)
        VALUES (?, ?, ?)
    """, (strategy, key, str(value)))
    conn.commit()
    conn.close()

# ==================== STOCK PRICE HELPER FUNCTIONS ====================

DAILY_PRICE_COLUMNS = [
    "trade_date",
    "stock_code",
    "stock_name",
    "market",
    "section",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "price_change",
    "change_rate",
    "volume",
    "trading_value",
    "market_cap",
    "listed_shares",
]

def upsert_daily_prices(daily_prices, db_path=DB_PATH) -> int:
    """
    Upserts stock daily prices dataframe into SQLite daily_prices table.
    """
    import pandas as pd
    if daily_prices.empty:
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    rows = daily_prices[DAILY_PRICE_COLUMNS].to_dict("records")
    
    cursor.executemany("""
        INSERT OR REPLACE INTO daily_prices (
            trade_date,
            stock_code,
            stock_name,
            market,
            section,
            open_price,
            high_price,
            low_price,
            close_price,
            price_change,
            change_rate,
            volume,
            trading_value,
            market_cap,
            listed_shares
        )
        VALUES (
            :trade_date,
            :stock_code,
            :stock_name,
            :market,
            :section,
            :open_price,
            :high_price,
            :low_price,
            :close_price,
            :price_change,
            :change_rate,
            :volume,
            :trading_value,
            :market_cap,
            :listed_shares
        )
    """, rows)
    
    conn.commit()
    conn.close()
    return len(rows)

def get_daily_prices(start_date=None, end_date=None, stock_code=None, limit=None, descending=False, db_path=DB_PATH):
    """
    Fetches daily stock prices as a pandas DataFrame.
    """
    import pandas as pd
    conn = sqlite3.connect(db_path)
    
    conditions = []
    params = {}

    if start_date is not None:
        conditions.append("trade_date >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        conditions.append("trade_date <= :end_date")
        params["end_date"] = end_date
    if stock_code is not None:
        conditions.append("stock_code = :stock_code")
        params["stock_code"] = stock_code

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    order_dir = "DESC" if descending else "ASC"
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit

    df = pd.read_sql_query(f"""
        SELECT {", ".join(DAILY_PRICE_COLUMNS)}
        FROM daily_prices
        {where_clause}
        ORDER BY trade_date {order_dir}
        {limit_clause}
    """, conn, params=params)
    
    conn.close()
    return df

def get_existing_trade_dates(start_date: str, db_path=DB_PATH) -> set:
    """
    Gets unique trade dates from daily_prices starting from start_date that have KRX stocks.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT trade_date FROM daily_prices 
        WHERE trade_date >= ? AND market IN ('KOSPI', 'KOSDAQ')
    """, (start_date,))
    rows = cursor.fetchall()
    conn.close()
    return {row[0] for row in rows if row[0]}

def get_closed_market_dates(start_date: str, db_path=DB_PATH) -> set:
    """
    Gets market closed dates starting from start_date.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT trade_date FROM market_closed_dates 
        WHERE trade_date >= ?
    """, (start_date,))
    rows = cursor.fetchall()
    conn.close()
    return {row[0] for row in rows if row[0]}

def insert_closed_market_date(trade_date: str, db_path=DB_PATH):
    """
    Inserts a closed market holiday date.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO market_closed_dates (trade_date) 
        VALUES (?)
    """, (trade_date,))
    conn.commit()
    conn.close()

def get_latest_trade_date(db_path=DB_PATH) -> str:
    """
    Gets the maximum trade_date from daily_prices.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return None

def upsert_stocks(stocks, db_path=DB_PATH) -> int:
    """
    Upserts stock details dataframe into SQLite stocks table.
    """
    import pandas as pd
    if stocks.empty:
        return 0

    df = stocks.copy()
    
    # Map column names if necessary
    STOCK_COLUMNS = [
        "stock_code",
        "stock_name",
        "market",
        "security_group",
        "sector",
        "dart_corp_code",
        "listed_date",
        "listed_shares",
        "is_active",
    ]
    
    # Ensure all columns exist
    for col in STOCK_COLUMNS:
        if col not in df.columns:
            if col == "is_active":
                df[col] = 1
            else:
                df[col] = None

    rows = df[STOCK_COLUMNS].to_dict("records")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO stocks (
            stock_code,
            stock_name,
            market,
            security_group,
            sector,
            dart_corp_code,
            listed_date,
            listed_shares,
            is_active
        )
        VALUES (
            :stock_code,
            :stock_name,
            :market,
            :security_group,
            :sector,
            :dart_corp_code,
            :listed_date,
            :listed_shares,
            :is_active
        )
        ON CONFLICT(stock_code) DO UPDATE SET
            stock_name = excluded.stock_name,
            market = excluded.market,
            security_group = excluded.security_group,
            sector = excluded.sector,
            dart_corp_code = excluded.dart_corp_code,
            listed_date = excluded.listed_date,
            listed_shares = excluded.listed_shares,
            is_active = excluded.is_active,
            updated_at = CURRENT_TIMESTAMP
    """, rows)
    conn.commit()
    conn.close()
    return len(rows)

def upsert_company_financials(financials, db_path=DB_PATH) -> int:
    """
    Upserts financials details dataframe into SQLite company_financials table.
    """
    import pandas as pd
    if financials.empty:
        return 0

    df = financials.copy()

    COLUMNS_TO_SAVE = [
        "corp_code", "stock_code", "bsns_year", "fs_div", "fs_nm", "currency", "fiscal_period",
        "current_assets", "non_current_assets", "total_assets", "current_liabilities",
        "non_current_liabilities", "total_liabilities", "total_equity", "revenue",
        "operating_income", "net_income", "debt_ratio", "current_ratio", "equity_ratio",
        "operating_margin", "net_margin", "par_value", "eps", "cash_dividend_yield",
        "cash_dividend_per_share", "cash_dividend_total", "cash_dividend_payout_ratio"
    ]
    
    for col in COLUMNS_TO_SAVE:
        if col not in df.columns:
            df[col] = None

    rows = df[COLUMNS_TO_SAVE].to_dict("records")
    cleaned_rows = []
    for row in rows:
        cleaned_row = {}
        for k, v in row.items():
            if pd.isna(v):
                cleaned_row[k] = None
            else:
                cleaned_row[k] = v
        cleaned_rows.append(cleaned_row)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO company_financials (
            corp_code, stock_code, bsns_year, fs_div, fs_nm, currency, fiscal_period,
            current_assets, non_current_assets, total_assets, current_liabilities,
            non_current_liabilities, total_liabilities, total_equity, revenue,
            operating_income, net_income, debt_ratio, current_ratio, equity_ratio,
            operating_margin, net_margin, par_value, eps, cash_dividend_yield,
            cash_dividend_per_share, cash_dividend_total, cash_dividend_payout_ratio
        )
        VALUES (
            :corp_code, :stock_code, :bsns_year, :fs_div, :fs_nm, :currency, :fiscal_period,
            :current_assets, :non_current_assets, :total_assets, :current_liabilities,
            :non_current_liabilities, :total_liabilities, :total_equity, :revenue,
            :operating_income, :net_income, :debt_ratio, :current_ratio, :equity_ratio,
            :operating_margin, :net_margin, :par_value, :eps, :cash_dividend_yield,
            :cash_dividend_per_share, :cash_dividend_total, :cash_dividend_payout_ratio
        )
        ON CONFLICT(corp_code, fiscal_period) DO UPDATE SET
            stock_code = excluded.stock_code,
            bsns_year = excluded.bsns_year,
            fs_div = excluded.fs_div,
            fs_nm = excluded.fs_nm,
            currency = excluded.currency,
            current_assets = excluded.current_assets,
            non_current_assets = excluded.non_current_assets,
            total_assets = excluded.total_assets,
            current_liabilities = excluded.current_liabilities,
            non_current_liabilities = excluded.non_current_liabilities,
            total_liabilities = excluded.total_liabilities,
            total_equity = excluded.total_equity,
            revenue = excluded.revenue,
            operating_income = excluded.operating_income,
            net_income = excluded.net_income,
            debt_ratio = excluded.debt_ratio,
            current_ratio = excluded.current_ratio,
            equity_ratio = excluded.equity_ratio,
            operating_margin = excluded.operating_margin,
            net_margin = excluded.net_margin,
            par_value = excluded.par_value,
            eps = excluded.eps,
            cash_dividend_yield = excluded.cash_dividend_yield,
            cash_dividend_per_share = excluded.cash_dividend_per_share,
            cash_dividend_total = excluded.cash_dividend_total,
            cash_dividend_payout_ratio = excluded.cash_dividend_payout_ratio,
            updated_at = CURRENT_TIMESTAMP
    """, cleaned_rows)
    conn.commit()
    conn.close()
    return len(cleaned_rows)

def get_active_stocks_with_dart_code(db_path=DB_PATH) -> list:
    """
    Retrieves all active stocks that have a mapped DART corp_code.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT stock_code, stock_name, dart_corp_code FROM stocks 
        WHERE is_active = 1 AND dart_corp_code IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"stock_code": r[0], "stock_name": r[1], "dart_corp_code": r[2]} for r in rows]

def get_synced_financials_keys(bsns_year: int, db_path=DB_PATH) -> set:
    """
    Retrieves unique corp_codes already synced in company_financials for the given bsns_year.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT corp_code FROM company_financials 
        WHERE bsns_year = ?
    """, (bsns_year,))
    rows = cursor.fetchall()
    conn.close()
    return {r[0] for r in rows if r[0]}

# ==================== COIN/FUTURES CANDLESTICK HELPER FUNCTIONS ====================

def save_candlesticks(raw_candles, contract, interval, db_path=DB_PATH):
    """
    Saves or updates candlestick data in the candlesticks database table.
    Handles both dictionaries (with abbreviated or full names) and list/tuple inputs.
    """
    if not raw_candles:
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    rows = []
    for candle in raw_candles:
        if isinstance(candle, dict):
            t = candle.get('t') or candle.get('time') or candle.get('timestamp')
            o = candle.get('o') or candle.get('open')
            h = candle.get('h') or candle.get('high')
            l = candle.get('l') or candle.get('low')
            c = candle.get('c') or candle.get('close')
            v = candle.get('v') or candle.get('volume')
            s = candle.get('sum') or candle.get('turnover') or 0.0
        elif isinstance(candle, (list, tuple)) and len(candle) >= 6:
            t = candle[0]
            o = candle[1]
            h = candle[2]
            l = candle[3]
            c = candle[4]
            v = candle[5]
            s = candle[6] if len(candle) > 6 else 0.0
        else:
            continue
            
        if t is None:
            continue
            
        rows.append((
            contract,
            interval,
            int(t),
            float(o) if o is not None else 0.0,
            float(h) if h is not None else 0.0,
            float(l) if l is not None else 0.0,
            float(c) if c is not None else 0.0,
            float(v) if v is not None else 0.0,
            float(s) if s is not None else 0.0
        ))
        
    if rows:
        cursor.executemany("""
            INSERT OR REPLACE INTO candlesticks (contract, interval, t, o, h, l, c, v, sum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
    conn.close()

def get_stored_candlesticks(contract, interval, limit, db_path=DB_PATH):
    """
    Fetches the latest limit stored candlesticks sorted in ascending order of time.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t, o, h, l, c, v, sum FROM (
            SELECT t, o, h, l, c, v, sum FROM candlesticks
            WHERE contract = ? AND interval = ?
            ORDER BY t DESC LIMIT ?
        ) ORDER BY t ASC
    """, (contract, interval, limit))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "t": r["t"],
        "o": r["o"],
        "h": r["h"],
        "l": r["l"],
        "c": r["c"],
        "v": r["v"],
        "sum": r["sum"]
    } for r in rows]

def get_last_timestamp(contract, interval, db_path=DB_PATH):
    """
    Gets the maximum timestamp 't' for the given contract and interval, returning 0 if empty.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(t) FROM candlesticks
        WHERE contract = ? AND interval = ?
    """, (contract, interval))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] is not None:
        return int(row[0])
    return 0


# ==================== CFTC COT & MACRO HELPER FUNCTIONS ====================

def save_cftc_cot(rows: list, db_path=DB_PATH) -> int:
    """
    Saves or updates CFTC COT records in database.
    Each row should be a tuple/list: (trade_date, contract_code, contract_name, open_interest, noncommercial_long, noncommercial_short, commercial_long, commercial_short)
    """
    if not rows:
        return 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO cftc_cot (
            trade_date, contract_code, contract_name,
            open_interest, noncommercial_long, noncommercial_short,
            commercial_long, commercial_short
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    return len(rows)

def get_cftc_cot(contract_code: str, limit: int = 52, db_path=DB_PATH) -> list:
    """
    Retrieves COT positioning history sorted by date ascending.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT trade_date, contract_code, contract_name,
               open_interest, noncommercial_long, noncommercial_short,
               commercial_long, commercial_short
        FROM cftc_cot
        WHERE contract_code = ?
        ORDER BY trade_date DESC LIMIT ?
    """, (contract_code, limit))
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for r in reversed(rows):
        net_spec = r["noncommercial_long"] - r["noncommercial_short"]
        result.append({
            "date": r["trade_date"],
            "contractCode": r["contract_code"],
            "contractName": r["contract_name"],
            "openInterest": r["open_interest"],
            "noncommLong": r["noncommercial_long"],
            "noncommShort": r["noncommercial_short"],
            "commLong": r["commercial_long"],
            "commShort": r["commercial_short"],
            "netPosition": net_spec
        })
    return result

def save_macro_indicators(rows: list, db_path=DB_PATH) -> int:
    """
    Saves or updates macroeconomic indicator values.
    Each row should be a tuple/list: (trade_date, series_id, value)
    """
    if not rows:
        return 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO macro_indicators (trade_date, series_id, value)
        VALUES (?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    return len(rows)

def get_macro_indicators(series_ids: list, limit: int = 120, db_path=DB_PATH) -> dict:
    """
    Retrieves macroeconomic indicator values grouped by series_id.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    result = {}
    for sid in series_ids:
        cursor.execute("""
            SELECT trade_date, value FROM macro_indicators
            WHERE series_id = ?
            ORDER BY trade_date DESC LIMIT ?
        """, (sid, limit))
        rows = cursor.fetchall()
        result[sid] = [{"date": r["trade_date"], "value": r["value"]} for r in reversed(rows)]
        
    conn.close()
    return result

def save_macro_calendar(rows: list, db_path=DB_PATH) -> int:
    """
    Saves or updates macroeconomic calendar schedules.
    Each row should be a tuple: (event_date, event_time, country, event_name, impact, actual, forecast, previous)
    """
    if not rows:
        return 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO macro_calendar (
            event_date, event_time, country, event_name, impact, actual, forecast, previous
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    return len(rows)

def get_macro_calendar(start_date: str, end_date: str, db_path=DB_PATH) -> list:
    """
    Retrieves macroeconomic calendar events within a date range.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT event_date, event_time, country, event_name, impact, actual, forecast, previous
        FROM macro_calendar
        WHERE event_date >= ? AND event_date <= ?
        ORDER BY event_date ASC, event_time ASC
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

