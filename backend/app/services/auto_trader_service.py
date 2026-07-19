import asyncio
import sqlite3
import pandas as pd
import numpy as np
import os
import sys
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

from app.core.config import Config
from app.clients.kis_client import KISClient
from app.db.db import DB_PATH, get_closed_market_dates
from app.pipelines.krx_daily_price_pipeline import sync_krx_daily_prices
from app.strategies.step1_market_leader_strategy import detect_step1_advanced_signals
from app.services.telegram_service import (
    send_telegram_message,
    notify_buy_executed,
    notify_trailing_stop_raised,
    notify_sell_executed
)

class KISAutoTrader:
    """
    Real & Paper Trading Auto-Trader Engine for Market Leader 5-Slot Strategy.
    """
    def __init__(self):
        self.is_active = True
        self.max_slots = 5
        self.slot_size = 2000000.0 # 200만 원 고정 투자
        self.pending_buy_candidates = [] # Queue of stocks to buy tomorrow morning
        self.active_positions = {}       # Dict of open positions: stock_code -> pos_info
        self.last_sync_date = ""

    def is_market_open_day(self, target_date: Optional[date] = None) -> bool:
        """
        Check if today is a valid trading day (Exclude Saturday, Sunday, and KRX Holidays).
        """
        dt = target_date or date.today()
        # Saturday: 5, Sunday: 6
        if dt.weekday() in (5, 6):
            return False
        
        date_str = dt.strftime("%Y%m%d")
        try:
            closed_dates = get_closed_market_dates()
            if date_str in closed_dates:
                return False
        except Exception:
            pass
        return True

    def run_daily_market_close_pipeline(self):
        """
        Executed at 15:35 & 15:45 every trading day:
        1. Fetch today's KRX daily price data
        2. Detect Step 0 & Step 1 Leader Candidates for Tomorrow
        3. Send Telegram Briefing
        """
        today_str = datetime.now().strftime("%Y%m%d")
        if self.last_sync_date == today_str:
            return

        print(f"[AutoTrader 15:35] Running daily price sync for {today_str}...")
        try:
            sync_krx_daily_prices(today_str)
            print(f"[AutoTrader 15:35] KRX price sync completed for {today_str}.")
        except Exception as e:
            print(f"[AutoTrader Error] Daily price sync failed: {e}")
            send_telegram_message(f"<b>[⚠️ 데이터 동기화 경고]</b>\n{today_str} 당일 주가 수집 실패: {e}")

        print(f"[AutoTrader 15:45] Screening Step 1 Leader Candidates for tomorrow...")
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT * FROM daily_prices WHERE market IN ('KOSPI', 'KOSDAQ')", conn)
            conn.close()

            res = detect_step1_advanced_signals(
                df,
                min_trading_value=10e10,    # 1,000억 이상
                min_relative_return=3.0,
                min_volume_ratio=1.5,
                max_dryup_ratio=0.35,
                require_ma_alignment=True
            )

            trades = res.get("trades", [])
            # Filter candidates where base_date_t is recent
            recent_candidates = [t for t in trades if t["base_date_t"] == today_str or t["entry_date"] >= today_str]

            self.pending_buy_candidates = recent_candidates[:3]
            self.last_sync_date = today_str

            # Briefing to Telegram
            if self.pending_buy_candidates:
                candidate_names = ", ".join([f"{c['stock_name']}({c['stock_code']})" for c in self.pending_buy_candidates])
                send_telegram_message(
                    f"<b>[📋 15:45 익일 매수 후보 포착 완료]</b>\n\n"
                    f"• <b>내일 09:00 매수 예정 종목</b>: {candidate_names}\n"
                    f"• <b>검증 기준</b>: 거래대금 1,000억+ & 정배열 & 거래량 35% 감소 지지\n"
                    f"💡 <i>09:00:10 시초가 잔여 5슬롯 한도 내에서 KIS 자동 매수가 실행됩니다.</i>"
                )
            else:
                send_telegram_message(f"<b>[📋 15:45 익일 매수 후보 브리핑]</b>\n오늘 기준 조건에 완전 합격한 신규 주도주가 없어 내일은 기존 포지션 관리에 집중합니다.")

        except Exception as e:
            print(f"[AutoTrader Error] 15:45 Screening failed: {e}")
            send_telegram_message(f"<b>[⚠️ 스크리닝 경고]</b> 15:45 주도주 분석 중 예외 발생: {e}")

    def execute_morning_buy_orders(self):
        """
        Executed at 09:00:10 on Trading Days:
        Checks available 5-slots and places KIS Buy Orders for candidates.
        """
        if not self.pending_buy_candidates:
            return

        is_paper = Config.KIS_IS_PAPER
        mode_label = "모의투자" if is_paper else "실전투자"
        print(f"[AutoTrader 09:00:10] Executing Morning Buy Orders ({mode_label})...")

        try:
            client = KISClient(is_paper=is_paper)
            
            # Fetch balance to check available cash & slots
            bal = client.get_account_balance()
            deposit = float(bal.get("deposit", 0))
            current_holdings = bal.get("holdings", [])
            
            used_slots = len(current_holdings)
            available_slots = max(0, self.max_slots - used_slots)

            if available_slots <= 0:
                send_telegram_message(f"<b>[ℹ️ 09:00 매수 보류]</b> 현재 보유 포지션이 5개 슬롯 한도에 도달하여 신규 매수를 건너뜁니다.")
                return

            if deposit < self.slot_size:
                send_telegram_message(f"<b>[⚠️ 09:00 매수 보류]</b> 예수금 잔고({int(deposit):,}원)가 최소 1회 매수금(200만 원)보다 부족합니다.")
                return

            candidates_to_buy = self.pending_buy_candidates[:available_slots]

            for cand in candidates_to_buy:
                code = cand["stock_code"]
                name = cand["stock_name"]
                
                # Check if already in holdings
                already_held = any(h.get("stock_code") == code for h in current_holdings)
                if already_held:
                    continue

                try:
                    # Place Market Price Buy Order (ORD_DVSN: "01")
                    # Estimate quantity = 2,000,000 / entry_price
                    est_price = float(cand.get("entry_price", 10000))
                    qty = max(1, int(self.slot_size / est_price)) if est_price > 0 else 1

                    res = client.order_cash(
                        stock_code=code,
                        qty=qty,
                        price=0,
                        side="BUY",
                        order_type="01" # 시장가
                    )

                    # Record active position
                    self.active_positions[code] = {
                        "name": name,
                        "code": code,
                        "qty": qty,
                        "entry_price": est_price,
                        "highest_price": est_price,
                        "current_stop_price": est_price * 0.96, # -4% 손절
                        "trailing_raised": False,
                        "is_paper": is_paper
                    }

                    # Send Telegram Alert
                    notify_buy_executed(name, code, qty, est_price, is_paper=is_paper)
                    time.sleep(1) # Gap between orders

                except Exception as oe:
                    print(f"[AutoTrader Order Error] Buy failed for {name}({code}): {oe}")
                    send_telegram_message(f"<b>[❌ KIS 매수 주문 실패]</b> {name}({code}): {oe}")

            # Clear queue after morning execution
            self.pending_buy_candidates = []

        except Exception as e:
            print(f"[AutoTrader Morning Error]: {e}")
            send_telegram_message(f"<b>[⚠️ 09:00 매수 예외]</b>: {e}")

    def monitor_intraday_trailing_stops(self):
        """
        Executed every 5 seconds during Market Hours (09:01 ~ 15:20):
        1. Fetch current price of open positions
        2. Raise stop to breakeven if gain >= +3.0%
        3. Execute Trailing Stop Sell if price drops -1.5% from peak
        4. Execute Stop Loss (-4.0%) or Target Take-Profit (+5.0%)
        """
        if not self.active_positions:
            return

        is_paper = Config.KIS_IS_PAPER
        try:
            client = KISClient(is_paper=is_paper)
            bal = client.get_account_balance()
            holdings = bal.get("holdings", [])

            for h in holdings:
                code = str(h.get("stock_code", "")).zfill(6)
                name = str(h.get("stock_name", ""))
                current_price = float(h.get("current_price", 0))
                entry_price = float(h.get("avg_buy_price", 0))
                qty = int(h.get("qty", 0))

                if current_price <= 0 or entry_price <= 0 or qty <= 0:
                    continue

                if code not in self.active_positions:
                    self.active_positions[code] = {
                        "name": name,
                        "code": code,
                        "qty": qty,
                        "entry_price": entry_price,
                        "highest_price": max(current_price, entry_price),
                        "current_stop_price": entry_price * 0.96,
                        "trailing_raised": False,
                        "is_paper": is_paper
                    }

                pos = self.active_positions[code]
                
                # Update highest price reached
                if current_price > pos["highest_price"]:
                    pos["highest_price"] = current_price

                highest_gain_pct = ((pos["highest_price"] - entry_price) / entry_price) * 100.0
                current_gain_pct = ((current_price - entry_price) / entry_price) * 100.0

                # 1. Trailing Stop Rule: Raise stop to breakeven if gain >= +3.0%
                if highest_gain_pct >= 3.0 and not pos["trailing_raised"]:
                    pos["current_stop_price"] = entry_price * 1.002 # Breakeven
                    pos["trailing_raised"] = True
                    notify_trailing_stop_raised(name, code, current_gain_pct, entry_price)

                # Dynamic Trailing Stop Peak drop (-1.5%)
                if pos["trailing_raised"]:
                    peak_stop = pos["highest_price"] * 0.985
                    if peak_stop > pos["current_stop_price"]:
                        pos["current_stop_price"] = peak_stop

                # 2. Check Exit Conditions
                is_stop_triggered = current_price <= pos["current_stop_price"]
                is_target_triggered = current_price >= entry_price * 1.05

                if is_stop_triggered or is_target_triggered:
                    reason = "트레일링 스톱 이익 확정" if pos["trailing_raised"] else ("목표가 익절 (+5%)" if is_target_triggered else "손절가 이탈 (-4%)")
                    
                    try:
                        # Execute Market Sell Order
                        client.order_cash(
                            stock_code=code,
                            qty=qty,
                            price=0,
                            side="SELL",
                            order_type="01" # 시장가
                        )

                        pnl_krw = (current_price - entry_price) * qty
                        notify_sell_executed(name, code, qty, current_price, current_gain_pct, pnl_krw, reason, is_paper=is_paper)
                        
                        del self.active_positions[code]
                        time.sleep(1)

                    except Exception as se:
                        print(f"[AutoTrader Sell Error] {name}({code}): {se}")
                        send_telegram_message(f"<b>[❌ KIS 매도 실패]</b> {name}({code}): {se}")

        except Exception as e:
            print(f"[AutoTrader Intraday Error]: {e}")

# Global Instance
auto_trader = KISAutoTrader()

async def auto_trader_background_loop():
    """
    Main Background Async Loop for Auto-Trader Engine.
    """
    print("[AutoTrader Engine] KIS Market Leader 5-Slot Auto-Trader Loop Started.")
    morning_executed_today = ""

    while True:
        try:
            await asyncio.sleep(5)
            now = datetime.now()

            # Skip if trader is paused
            if not auto_trader.is_active:
                await asyncio.sleep(10)
                continue

            # Check market open day
            if not auto_trader.is_market_open_day(now.date()):
                await asyncio.sleep(60)
                continue

            cur_time_str = now.strftime("%H:%M")
            cur_date_str = now.strftime("%Y%m%d")

            # A. Morning 09:00:10 Buy Execution
            if cur_time_str == "09:00" and morning_executed_today != cur_date_str:
                await asyncio.sleep(5) # Wait 5 sec past 09:00
                auto_trader.execute_morning_buy_orders()
                morning_executed_today = cur_date_str

            # B. Intraday Trailing Stop & Exit Monitoring (09:01 ~ 15:20)
            if "09:01" <= cur_time_str <= "15:20":
                auto_trader.monitor_intraday_trailing_stops()

            # C. Market Close Daily Price Sync & Screening (15:35 ~ 15:45)
            if cur_time_str == "15:35":
                auto_trader.run_daily_market_close_pipeline()

        except Exception as e:
            print(f"[AutoTrader Engine Critical Exception]: {e}")
            send_telegram_message(f"<b>[⚠️ 자동 매매 엔진 예외 발생]</b>\n{e}\n<i>3초 후 재시도합니다.</i>")
            await asyncio.sleep(3)
