import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def is_common_stock(stock_name: str, stock_code: str) -> bool:
    """
    Check if stock is common stock (exclude priority shares, ETFs, ETNs, SPACs).
    """
    name = str(stock_name).strip()
    code = str(stock_code).strip()
    
    if name.endswith("우") or name.endswith("우B") or name.endswith("우C") or "우(전환)" in name:
        return False
    if "ETF" in name or "ETN" in name or "스팩" in name or "SPAC" in name:
        return False
    if len(code) == 6 and code.isdigit() and code[-1] != '0':
        if code[-1] in ('5', '7', '9', 'K', 'M'):
            return False
    return True

def screen_step0_market_leaders(
    daily_prices_df: pd.DataFrame,
    stocks_df: Optional[pd.DataFrame] = None,
    min_relative_return: float = 3.0,
    min_trading_value: float = 30000000000.0, # 300억 원
    min_volume_ratio: float = 1.5,
    search_query: str = ""
) -> pd.DataFrame:
    """
    Step 0 Strategy Screener:
    Finds market-leading outperforming stocks that meet:
    1. Relative Return vs Index >= +3.0%p
    2. Today Trading Value >= 300억 원 (30 Billion KRW)
    3. Volume/Value Spike Ratio >= 1.5x vs 20D Average
    4. Foreign/Institutional Net Buy flow
    """
    if daily_prices_df.empty:
        return pd.DataFrame()

    df = daily_prices_df.copy()

    # Filter KOSPI & KOSDAQ markets only
    df = df[df["market"].isin(["KOSPI", "KOSDAQ"])].copy()
    if df.empty:
        return pd.DataFrame()

    # Numeric conversion
    df["close_price"] = pd.to_numeric(df["close_price"], errors="coerce")
    df["change_rate"] = pd.to_numeric(df["change_rate"], errors="coerce")
    df["trading_value"] = pd.to_numeric(df["trading_value"], errors="coerce")

    # Filter common stocks
    df["is_common"] = df.apply(lambda r: is_common_stock(r["stock_name"], r["stock_code"]), axis=1)
    df = df[df["is_common"] == True]

    # Fetch REAL KOSPI and KOSDAQ index daily returns from Naver Index API
    import requests

    index_returns = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for mkt_name in ["KOSPI", "KOSDAQ"]:
        try:
            u = f"https://m.stock.naver.com/api/index/{mkt_name}/price?page=1&pageSize=30"
            r = requests.get(u, headers=headers, timeout=3)
            if r.status_code == 200:
                idx_list = r.json()
                if isinstance(idx_list, list):
                    for item in idx_list:
                        d_str = item.get("localTradedAt", "").replace("-", "")
                        r_val = float(item.get("fluctuationsRatio", "0").replace(",", ""))
                        index_returns[(d_str, mkt_name)] = r_val
        except Exception as e:
            print(f"[Naver Index Fetch Warning] {mkt_name}: {e}")

    # Fallback to mean change rate if index return not in index_returns
    mean_returns = df.groupby(["trade_date", "market"])["change_rate"].mean().to_dict()

    def get_index_return(row):
        key = (str(row["trade_date"]), str(row["market"]))
        if key in index_returns:
            return index_returns[key]
        return mean_returns.get(key, 0.0)

    df["market_change_rate"] = df.apply(get_index_return, axis=1)
    df["relative_return"] = df["change_rate"] - df["market_change_rate"]

    # Filter for the latest KRX trade date
    latest_krx_date = df["trade_date"].max()
    
    # Calculate 20-day rolling avg trading value for last 30 trade dates to speed up
    trade_dates = sorted(df["trade_date"].unique())
    recent_dates = trade_dates[-30:] if len(trade_dates) >= 30 else trade_dates
    recent_df = df[df["trade_date"].isin(recent_dates)].copy()

    recent_df = recent_df.sort_values(by=["stock_code", "trade_date"])
    recent_df["avg_20d_trading_value"] = recent_df.groupby("stock_code")["trading_value"].transform(
        lambda x: x.rolling(window=20, min_periods=1).mean()
    )
    recent_df["volume_spike_ratio"] = np.where(
        recent_df["avg_20d_trading_value"] > 0,
        recent_df["trading_value"] / recent_df["avg_20d_trading_value"],
        1.0
    )

    latest_df = recent_df[recent_df["trade_date"] == latest_krx_date].copy()

    # Apply Step 0 Candidate Criteria
    c1 = latest_df["relative_return"] >= min_relative_return
    c2 = latest_df["trading_value"] >= min_trading_value
    c3 = latest_df["volume_spike_ratio"] >= min_volume_ratio

    latest_df["is_candidate"] = c1 & c2 & c3

    # Check search_query filtering
    if search_query and search_query.strip():
        q_norm = search_query.strip().lower()
        matched_df = latest_df[
            latest_df["stock_code"].str.lower().str.contains(q_norm) | 
            latest_df["stock_name"].str.lower().str.contains(q_norm)
        ].copy()
        if not matched_df.empty:
            candidates_df = matched_df
        else:
            candidates_df = latest_df[latest_df["is_candidate"] == True].copy()
    else:
        candidates_df = latest_df[latest_df["is_candidate"] == True].copy()
        if candidates_df.empty:
            candidates_df = latest_df[(latest_df["relative_return"] >= 1.0) & (latest_df["trading_value"] >= 10000000000.0)].copy()
            if candidates_df.empty:
                candidates_df = latest_df.sort_values(by="trading_value", ascending=False).head(10).copy()

    # Fetch REAL Foreign & Institutional Net Buy indicators from Naver Finance API
    import requests

    foreign_buys = []
    inst_buys = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for _, row in candidates_df.iterrows():
        code = str(row["stock_code"]).zfill(6)
        close_p = float(row["close_price"])
        f_amt = 0.0
        i_amt = 0.0

        try:
            url = f"https://m.stock.naver.com/api/stock/{code}/trend"
            res = requests.get(url, headers=headers, timeout=3)
            if res.status_code == 200:
                trend_data = res.json()
                if isinstance(trend_data, list) and len(trend_data) > 0:
                    latest_trend = trend_data[0]
                    f_quant_str = str(latest_trend.get("foreignerPureBuyQuant", "0")).replace(",", "")
                    i_quant_str = str(latest_trend.get("organPureBuyQuant", "0")).replace(",", "")

                    f_quant = int(f_quant_str) if f_quant_str.replace("+", "").replace("-", "").isdigit() else 0
                    i_quant = int(i_quant_str) if i_quant_str.replace("+", "").replace("-", "").isdigit() else 0

                    # Convert net buy quantity to amount in 억 원
                    f_amt = round((f_quant * close_p) / 1e8, 1)
                    i_amt = round((i_quant * close_p) / 1e8, 1)
        except Exception as e:
            print(f"[Naver Trend Fetch Warning] {code}: {e}")

        foreign_buys.append(f_amt)
        inst_buys.append(i_amt)

    candidates_df["foreign_net_buy"] = foreign_buys
    candidates_df["institution_net_buy"] = inst_buys
    candidates_df["is_double_buy"] = (candidates_df["foreign_net_buy"] > 0) & (candidates_df["institution_net_buy"] > 0)

    status_labels = []
    for _, row in candidates_df.iterrows():
        is_cand = bool(row.get("is_candidate", False))
        tv = float(row.get("trading_value", 0))
        rel_ret = float(row.get("relative_return", 0))
        vol_ratio = float(row.get("volume_spike_ratio", 1.0))
        f_buy = float(row.get("foreign_net_buy", 0))
        i_buy = float(row.get("institution_net_buy", 0))

        if is_cand and (f_buy > 0 or i_buy > 0):
            status_labels.append("Step 0 통과")
        else:
            reasons = []
            if tv < min_trading_value:
                reasons.append(f"거래대금 미달({round(tv/1e8):,}억/300억)")
            if rel_ret < min_relative_return:
                reasons.append(f"초과수익 미달(+{rel_ret:.1f}%p/+3%p)")
            if vol_ratio < min_volume_ratio:
                reasons.append(f"급증배율 미달({vol_ratio:.1f}배/1.5배)")
            if f_buy <= 0 and i_buy <= 0:
                reasons.append("수급 순매수 미달")
            status_labels.append(" | ".join(reasons) if reasons else "조건 미달")

    candidates_df["status_label"] = status_labels

    # Sort candidates by trading value descending
    sorted_df = candidates_df.sort_values(by="trading_value", ascending=False)
    return sorted_df
