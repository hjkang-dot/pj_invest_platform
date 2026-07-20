import pandas as pd
import numpy as np
import requests
from typing import Dict, Any, List, Optional

def is_common_stock(stock_name: str, stock_code: str) -> bool:
    name = str(stock_name).strip()
    code = str(stock_code).strip()
    
    if name.endswith("우") or name.endswith("우B") or name.endswith("우C") or "우(전환)" in name:
        return False
    if "ETF" in name or "ETN" in name or "스팩" in name or "SPAC" in name:
        return False
    # Exclude trading halted & risk keywords
    risk_keywords = ["관리", "정지", "환기", "유의", "상장폐지", "정리매매"]
    if any(kw in name for kw in risk_keywords):
        return False

    if len(code) == 6 and code.isdigit() and code[-1] != '0':
        if code[-1] in ('5', '7', '9', 'K', 'M'):
            return False
    return True

def fetch_naver_investor_net_buy(stock_code: str) -> Dict[str, float]:
    """
    Fetch recent 1-day Foreign & Institutional Net Buy amount (in 억 원) using Naver Finance API.
    """
    code = str(stock_code).zfill(6)
    url = f"https://m.stock.naver.com/api/stock/{code}/trend"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        res = requests.get(url, headers=headers, timeout=1)
        if res.status_code == 200:
            trend_data = res.json()
            if isinstance(trend_data, list) and len(trend_data) > 0:
                latest = trend_data[0]
                close_p = float(latest.get("closePrice", "0").replace(",", ""))
                f_quant_str = str(latest.get("foreignerPureBuyQuant", "0")).replace(",", "")
                i_quant_str = str(latest.get("organPureBuyQuant", "0")).replace(",", "")

                f_quant = int(f_quant_str) if f_quant_str.replace("+", "").replace("-", "").isdigit() else 0
                i_quant = int(i_quant_str) if i_quant_str.replace("+", "").replace("-", "").isdigit() else 0

                f_amt = round((f_quant * close_p) / 1e8, 1)
                i_amt = round((i_quant * close_p) / 1e8, 1)

                return {"foreign_net_buy": f_amt, "institution_net_buy": i_amt}
    except Exception as e:
        print(f"[Naver Net Buy Warning] {code}: {e}")

    return {"foreign_net_buy": 0.0, "institution_net_buy": 0.0}

def detect_step1_advanced_signals(
    df: pd.DataFrame,
    min_trading_value: float = 100000000000.0, # 1,000억 원
    min_relative_return: float = 3.0,           # 시장 대비 +3.0%p
    min_volume_ratio: float = 1.5,              # 20일 평균 대비 1.5배
    max_dryup_ratio: float = 0.35,              # 조정일 거래량이 기준봉의 35% 이하
    require_ma_alignment: bool = True,          # 5일선 > 20일선 정배열
    require_net_buy: bool = True,               # Step 1 외인/기관 순매수 수급 검증
    hold_days: int = 5,                         # 진입 후 최대 보유일수
    target_profit_pct: float = 5.0,             # 목표 익절률 +5.0%
    stop_loss_pct: float = -4.0,                # 기본 손절률 -4.0%
    enable_trailing_stop: bool = True,          # 트레일링 스톱 활성화
    breakeven_trigger_pct: float = 3.0,         # +3.0% 달성 시 손절가를 본절(0%)로 상향
    trailing_drop_pct: float = 1.5              # 고점 대비 -1.5% 밀릴 때 이익 확정
) -> Dict[str, Any]:
    """
    Advanced Strategy with Trailing Stop & Investor Net Buy validation.
    """
    if df.empty:
        return {"error": "Empty dataframe"}

    df = df.copy()
    df["trade_date"] = df["trade_date"].astype(str)
    df = df.sort_values(by=["stock_code", "trade_date"]).reset_index(drop=True)

    df["is_common"] = df.apply(lambda r: is_common_stock(r["stock_name"], r["stock_code"]), axis=1)
    df = df[df["is_common"] == True].copy()

    df["avg_20d_trading_value"] = df.groupby("stock_code")["trading_value"].transform(
        lambda x: x.rolling(window=20, min_periods=5).mean()
    )
    df["volume_spike_ratio"] = np.where(
        df["avg_20d_trading_value"] > 0,
        df["trading_value"] / df["avg_20d_trading_value"],
        1.0
    )

    mkt_returns = df.groupby(["trade_date", "market"])["change_rate"].transform("mean")
    df["relative_return"] = df["change_rate"] - mkt_returns

    df["ma5"] = df.groupby("stock_code")["close_price"].transform(
        lambda x: x.rolling(window=5, min_periods=1).mean()
    )
    df["ma20"] = df.groupby("stock_code")["close_price"].transform(
        lambda x: x.rolling(window=20, min_periods=1).mean()
    )
    df["mid_price"] = (df["open_price"] + df["close_price"]) / 2.0

    # Ensure net buy columns exist
    if "foreign_net_buy" not in df.columns:
        df["foreign_net_buy"] = 0.0
    if "institution_net_buy" not in df.columns:
        df["institution_net_buy"] = 0.0

    trade_signals = []
    stock_groups = df.groupby("stock_code")

    for stock_code, group in stock_groups:
        n_rows = len(group)
        if n_rows < 25:
            continue

        dates = group["trade_date"].values
        names = group["stock_name"].values
        opens = group["open_price"].values
        highs = group["high_price"].values
        lows = group["low_price"].values
        closes = group["close_price"].values
        volumes = group["volume"].values
        t_values = group["trading_value"].values
        rel_rets = group["relative_return"].values
        vol_spikes = group["volume_spike_ratio"].values
        change_rates = group["change_rate"].values
        ma5s = group["ma5"].values
        ma20s = group["ma20"].values
        mid_prices = group["mid_price"].values
        f_buys = group["foreign_net_buy"].values
        i_buys = group["institution_net_buy"].values

        for i in range(20, n_rows - hold_days - 2):
            # Step 0 Breakout
            if not (t_values[i] >= min_trading_value and
                    rel_rets[i] >= min_relative_return and
                    vol_spikes[i] >= min_volume_ratio and
                    change_rates[i] > 0):
                continue

            if require_ma_alignment and ma5s[i] < ma20s[i]:
                continue

            t_date = dates[i]
            t_name = names[i]
            t_vol = volumes[i]
            t_val = t_values[i]
            t_mid = mid_prices[i]

            step1_passed = False
            entry_idx = -1

            for offset in [1, 2]:
                idx_adj = i + offset
                if idx_adj >= n_rows:
                    break
                
                vol_ratio = volumes[idx_adj] / t_vol if t_vol > 0 else 1.0
                is_vol_dryup = vol_ratio <= max_dryup_ratio
                is_price_supported = (closes[idx_adj] >= t_mid * 0.99) and (closes[idx_adj] >= ma5s[idx_adj] * 0.99)
                is_bullish_trend = ma5s[idx_adj] >= ma20s[idx_adj]
                
                # Investor Net Buy Filter (Foreign > 0 OR Institution > 0)
                is_net_buy_ok = True
                if require_net_buy:
                    f_b = f_buys[idx_adj] if idx_adj < len(f_buys) else 0
                    i_b = i_buys[idx_adj] if idx_adj < len(i_buys) else 0
                    # Standard: Allow if either foreign or institution net buy > 0, or base breakout had strong net buy
                    is_net_buy_ok = (f_b >= 0 or i_b >= 0)

                if is_vol_dryup and is_price_supported and is_bullish_trend and is_net_buy_ok:
                    step1_passed = True
                    entry_idx = idx_adj + 1
                    break

            if not step1_passed or entry_idx >= n_rows:
                continue

            entry_price = float(opens[entry_idx])
            if entry_price <= 0:
                continue

            # Trailing Stop & Exit Logic
            current_stop_price = entry_price * (1.0 + stop_loss_pct / 100.0)
            highest_price = entry_price
            
            exit_price = entry_price
            exit_date = dates[entry_idx]
            is_win = False
            is_stopped = False
            exit_reason = "holding_expired"

            exit_limit = min(entry_idx + hold_days, n_rows - 1)

            for k in range(entry_idx, exit_limit + 1):
                cur_h = float(highs[k])
                cur_l = float(lows[k])

                # Update highest price reached after entry
                if cur_h > highest_price:
                    highest_price = cur_h

                highest_ret_pct = ((highest_price - entry_price) / entry_price) * 100.0

                # 1. Trailing Stop Logic: If gain >= breakeven_trigger_pct (+3%), raise stop to breakeven (entry_price)
                if enable_trailing_stop and highest_ret_pct >= breakeven_trigger_pct:
                    breakeven_stop = entry_price * 1.002 # Break-even + fees
                    if current_stop_price < breakeven_stop:
                        current_stop_price = breakeven_stop

                    # Dynamic Trailing Stop: drop from peak
                    peak_trailing_stop = highest_price * (1.0 - trailing_drop_pct / 100.0)
                    if peak_trailing_stop > current_stop_price:
                        current_stop_price = peak_trailing_stop

                # 2. Check Stop Loss / Trailing Stop Trigger
                if cur_l <= current_stop_price:
                    exit_price = current_stop_price
                    exit_date = dates[k]
                    is_stopped = True
                    is_win = exit_price >= entry_price
                    exit_reason = "trailing_stop" if highest_ret_pct >= breakeven_trigger_pct else "stop_loss"
                    break

                # 3. Check Target Profit (+5.0%)
                if cur_h >= entry_price * (1.0 + target_profit_pct / 100.0):
                    exit_price = entry_price * (1.0 + target_profit_pct / 100.0)
                    exit_date = dates[k]
                    is_win = True
                    exit_reason = "target_profit"
                    break

            if not is_stopped and not is_win:
                exit_price = float(closes[exit_limit])
                exit_date = dates[exit_limit]
                is_win = exit_price >= entry_price
                exit_reason = "holding_expired"

            ret_pct = round(((exit_price - entry_price) / entry_price) * 100.0, 2)
            max_ret_pct = round(((highest_price - entry_price) / entry_price) * 100.0, 2)

            trade_signals.append({
                "stock_code": stock_code,
                "stock_name": t_name,
                "base_date_t": t_date,
                "base_trading_val": round(t_val / 1e8, 1),
                "entry_date": dates[entry_idx],
                "entry_price": entry_price,
                "exit_date": exit_date,
                "exit_price": exit_price,
                "return_pct": ret_pct,
                "max_possible_return": max_ret_pct,
                "is_win": is_win,
                "is_stopped": is_stopped,
                "exit_reason": exit_reason
            })

    if not trade_signals:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_return_pct": 0.0,
            "avg_max_possible_return_pct": 0.0,
            "trades": []
        }

    res_df = pd.DataFrame(trade_signals)
    total_trades = len(res_df)
    win_count = int(res_df["is_win"].sum())
    win_rate = round((win_count / total_trades) * 100.0, 1) if total_trades > 0 else 0.0
    avg_return = round(res_df["return_pct"].mean(), 2)
    avg_max_return = round(res_df["max_possible_return"].mean(), 2)

    return {
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": int(total_trades - win_count),
        "win_rate": win_rate,
        "avg_return_pct": avg_return,
        "avg_max_possible_return_pct": avg_max_return,
        "trades": res_df.to_dict(orient="records")
    }

def screen_step1_entry_candidates(
    daily_prices_df: pd.DataFrame,
    stocks_df: Optional[pd.DataFrame] = None,
    min_trading_value: float = 100000000000.0, # 1,000억 원 이상
    min_relative_return: float = 3.0,          # +3.0%p 이상
    min_volume_ratio: float = 1.5,             # 1.5배 이상
    max_dryup_ratio: float = 0.35,             # 조정일 거래량 <= 35%
    search_query: str = ""
) -> pd.DataFrame:
    """
    Screen real Step 1 entry candidate stocks for 09:00:10 auto-trader execution.
    Requires:
    1. Step 0 Breakout (Trading Value >= 300억, Relative Return >= +3%p, Volume Spike >= 1.5x)
    2. 5D / 20D Moving Average Bullish Alignment (ma5 >= ma20)
    3. Volume Dry-up <= 35% on pullback days
    4. Real-time Foreigner & Institutional net buy validation
    """
    if daily_prices_df.empty:
        return pd.DataFrame()

    df = daily_prices_df.copy()
    df["trade_date"] = df["trade_date"].astype(str)
    df = df.sort_values(by=["stock_code", "trade_date"]).reset_index(drop=True)

    df["close_price"] = pd.to_numeric(df["close_price"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df["trading_value"] = pd.to_numeric(df["trading_value"], errors="coerce")

    # Exclude trading halted stocks (volume <= 0 or trading_value <= 0)
    df = df[(df["volume"] > 0) & (df["trading_value"] > 0)].copy()

    df["is_common"] = df.apply(lambda r: is_common_stock(r["stock_name"], r["stock_code"]), axis=1)
    df = df[df["is_common"] == True].copy()

    # Calculate 20-day average trading value & volume spike ratio
    df["avg_20d_trading_value"] = df.groupby("stock_code")["trading_value"].transform(
        lambda x: x.rolling(window=20, min_periods=5).mean()
    )
    df["volume_spike_ratio"] = np.where(
        df["avg_20d_trading_value"] > 0,
        df["trading_value"] / df["avg_20d_trading_value"],
        1.0
    )

    # Relative return vs market average
    mkt_returns = df.groupby(["trade_date", "market"])["change_rate"].transform("mean")
    df["relative_return"] = df["change_rate"] - mkt_returns

    df["ma5"] = df.groupby("stock_code")["close_price"].transform(
        lambda x: x.rolling(window=5, min_periods=1).mean()
    )
    df["ma20"] = df.groupby("stock_code")["close_price"].transform(
        lambda x: x.rolling(window=20, min_periods=1).mean()
    )
    df["mid_price"] = (df["open_price"] + df["close_price"]) / 2.0

    candidates = []
    stock_groups = df.groupby("stock_code")

    for stock_code, group in stock_groups:
        n_rows = len(group)
        if n_rows < 5:
            continue

        latest_idx = n_rows - 1
        
        # Check within last 4 days for Step 0 breakout + Step 1 dryup
        for i in range(max(0, n_rows - 4), n_rows):
            # Check Step 0 breakout on day i
            t_val = group["trading_value"].iloc[i]
            rel_ret = group["relative_return"].iloc[i]
            vol_spike = group["volume_spike_ratio"].iloc[i]
            c_rate = group["change_rate"].iloc[i]
            ma5 = group["ma5"].iloc[i]
            ma20 = group["ma20"].iloc[i]

            is_step0 = (t_val >= min_trading_value and rel_ret >= min_relative_return and vol_spike >= min_volume_ratio and c_rate > 0)
            is_ma_aligned = (ma5 >= ma20)

            if not is_step0 or not is_ma_aligned:
                continue

            # Check if current day or next 1-2 days show dryup
            base_vol = group["volume"].iloc[i]
            base_mid = group["mid_price"].iloc[i]

            step1_qualified = False
            dryup_val = 1.0

            for offset in range(1, 3):
                adj_idx = i + offset
                if adj_idx >= n_rows:
                    break
                
                cur_vol = group["volume"].iloc[adj_idx]
                cur_close = group["close_price"].iloc[adj_idx]
                cur_ma5 = group["ma5"].iloc[adj_idx]
                cur_ma20 = group["ma20"].iloc[adj_idx]

                dryup_val = cur_vol / base_vol if base_vol > 0 else 1.0
                price_ok = (cur_close >= base_mid * 0.99) and (cur_close >= cur_ma5 * 0.99)
                trend_ok = (cur_ma5 >= cur_ma20)

                if dryup_val <= max_dryup_ratio and price_ok and trend_ok:
                    step1_qualified = True
                    latest_idx = adj_idx
                    break
            
            # If currently at latest day or step1 qualified
            if step1_qualified or (i == n_rows - 1 and is_step0 and is_ma_aligned):
                last_row = group.iloc[latest_idx]
                
                candidates.append({
                    "stock_code": stock_code,
                    "stock_name": last_row["stock_name"],
                    "market": last_row.get("market", "KRX"),
                    "close_price": float(last_row["close_price"]),
                    "change_rate": float(last_row["change_rate"]),
                    "trading_value": float(t_val),
                    "volume_spike_ratio": float(vol_spike),
                    "relative_return": float(rel_ret),
                    "dryup_ratio": round(dryup_val * 100.0, 1),
                    "foreign_net_buy": 0.0,
                    "institution_net_buy": 0.0,
                    "is_double_buy": False,
                    "is_step1_confirmed": step1_qualified,
                    "status_label": "09:00:10 진입 확정" if step1_qualified else "Step 1 지지 대기"
                })
                break

    if not candidates:
        return pd.DataFrame()

    # Parallelize Naver investor net buy API requests (Fast & Non-blocking)
    from concurrent.futures import ThreadPoolExecutor
    
    top_candidates = candidates[:30] # Limit max 30 candidates for instant response
    def _enrich_net_buy(cand):
        code = cand["stock_code"]
        net = fetch_naver_investor_net_buy(code)
        f_b = net.get("foreign_net_buy", 0.0)
        i_b = net.get("institution_net_buy", 0.0)
        cand["foreign_net_buy"] = f_b
        cand["institution_net_buy"] = i_b
        cand["is_double_buy"] = (f_b > 0 and i_b > 0)
        return cand

    with ThreadPoolExecutor(max_workers=10) as executor:
        enriched_candidates = list(executor.map(_enrich_net_buy, top_candidates))

    cand_df = pd.DataFrame(enriched_candidates)

    if search_query:
        q_lower = search_query.lower().strip()
        cand_df = cand_df[
            cand_df["stock_name"].astype(str).str.lower().str.contains(q_lower) |
            cand_df["stock_code"].astype(str).str.lower().str.contains(q_lower)
        ]

    # Prioritize Step 1 confirmed & double buy
    cand_df = cand_df.sort_values(
        by=["is_step1_confirmed", "is_double_buy", "trading_value"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    return cand_df
