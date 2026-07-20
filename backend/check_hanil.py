import sqlite3
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.db.db import DB_PATH
from app.strategies.step1_market_leader_strategy import screen_step1_entry_candidates

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM daily_prices WHERE stock_name LIKE '%한일사료%' OR stock_code = '005860'", conn)
conn.close()

print(f"한일사료 DB 레코드 수: {len(df)}")
if not df.empty:
    print(df.tail(10)[["trade_date", "stock_name", "stock_code", "open_price", "high_price", "low_price", "close_price", "volume", "trading_value", "change_rate"]])

# Run screener
conn = sqlite3.connect(DB_PATH)
all_df = pd.read_sql_query("SELECT * FROM daily_prices", conn)
conn.close()

res = screen_step1_entry_candidates(all_df)
print("\n--- [Step 1 스크리닝 결과 상위 종목] ---")
if not res.empty:
    print(res[["stock_name", "stock_code", "close_price", "change_rate", "trading_value", "volume_spike_ratio", "relative_return", "dryup_ratio", "status_label"]].head(10))

    hanil_res = res[res["stock_name"].str.contains("한일사료") | (res["stock_code"] == "005860")]
    print("\n--- [한일사료 스크리닝 결과] ---")
    print(hanil_res)
