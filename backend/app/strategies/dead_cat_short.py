import pandas as pd
import numpy as np
from app.strategies.base import BaseStrategy

class DeadCatShortStrategy(BaseStrategy):
    def __init__(self, long_period=120, short_period=20, rsi_period=14, rsi_overbought=60,
                 atr_period=14, stop_atr_mult=2.0, take_atr_mult=3.0):
        super().__init__(name=f"DeadCatShort_{long_period}_{short_period}")
        self.long_period = long_period
        self.short_period = short_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.atr_period = atr_period
        self.stop_atr_mult = stop_atr_mult
        self.take_atr_mult = take_atr_mult
        self.min_required_bars = max(self.long_period + 5, self.rsi_period + 5, self.atr_period + 5, 30)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates indicators for Dead Cat Bounce short strategy:
        - MA Long (e.g. 120 SMA)
        - MA Short (e.g. 20 SMA)
        - RSI (e.g. 14 RSI)
        - ATR (e.g. 14 ATR for Stop Loss and Take Profit)
        """
        # Ensure numeric types
        df['c'] = pd.to_numeric(df['c'])
        df['h'] = pd.to_numeric(df['h'])
        df['l'] = pd.to_numeric(df['l'])
        df['v'] = pd.to_numeric(df['v'])

        # 1. Long-term trend indicator (120-day SMA)
        df['ma_long'] = df['c'].rolling(window=self.long_period).mean()

        # 2. Short-term trend indicator (20-day SMA)
        df['ma_short'] = df['c'].rolling(window=self.short_period).mean()

        # 3. RSI(14)
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0.0)).ewm(alpha=1/self.rsi_period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/self.rsi_period, adjust=False).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))

        # 4. Wilder's ATR(14)
        df['prev_c'] = df['c'].shift(1)
        df['tr1'] = df['h'] - df['l']
        df['tr2'] = (df['h'] - df['prev_c']).abs()
        df['tr3'] = (df['l'] - df['prev_c']).abs()
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].ewm(alpha=1/self.atr_period, adjust=False).mean()

        # Cleanup temp columns
        temp_cols = ['prev_c', 'tr1', 'tr2', 'tr3', 'tr']
        df = df.drop(columns=[col for col in temp_cols if col in df.columns], errors='ignore')

        return df

    def check_signal(self, df: pd.DataFrame) -> str:
        """
        Generates Short entry or Exit signal based on conditions:
        - ENTRY SHORT:
            1. Long-term downtrend (c < ma_long)
            2. Had a short-term bounce (RSI peaked over rsi_overbought or price crossed above ma_short within last 5 bars)
            3. Price crosses down below ma_short OR RSI crosses down below rsi_overbought.
        - EXIT SHORT:
            1. RSI enters oversold area (rsi <= 35) to lock profits early or avoid deep bounces.
        """
        if len(df) < self.min_required_bars:
            return "NONE"

        # Check last few rows
        curr_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        c = curr_row['c']
        prev_c = prev_row['c']
        ma_long = curr_row['ma_long']
        ma_short = curr_row['ma_short']
        prev_ma_short = prev_row['ma_short']
        rsi = curr_row['rsi']
        prev_rsi = prev_row['rsi']

        # 1. Long-term downtrend filter
        is_downtrend = c < ma_long

        # 2. Check if we had a short-term bounce recently (lookback: index -5 to -2)
        has_recent_bounce = False
        lookback_range = range(2, 6) # index -2 to -5
        for i in lookback_range:
            row = df.iloc[-i]
            if row['c'] >= row['ma_short'] or row['rsi'] >= self.rsi_overbought:
                has_recent_bounce = True
                break

        if is_downtrend and has_recent_bounce:
            # Entry condition 1: Cross down ma_short
            cross_down_ma = (prev_c >= prev_ma_short) and (c < ma_short)
            # Entry condition 2: RSI crosses down below rsi_overbought
            cross_down_rsi = (prev_rsi >= self.rsi_overbought) and (rsi < self.rsi_overbought)

            if cross_down_ma or cross_down_rsi:
                return "SHORT"

        # Exit condition: RSI reaches oversold level (e.g. 35)
        if rsi <= 35:
            return "EXIT"

        return "NONE"

    def get_stop_loss_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        curr_row = df.iloc[-1]
        atr = curr_row['atr'] if 'atr' in curr_row else entry_price * 0.02
        if pos_type == "SHORT":
            return entry_price + (self.stop_atr_mult * atr)
        else:
            return entry_price - (self.stop_atr_mult * atr) # For safety

    def get_take_profit_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        curr_row = df.iloc[-1]
        atr = curr_row['atr'] if 'atr' in curr_row else entry_price * 0.05
        if pos_type == "SHORT":
            return entry_price - (self.take_atr_mult * atr)
        else:
            return entry_price + (self.take_atr_mult * atr) # For safety
