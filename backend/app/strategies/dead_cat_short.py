import pandas as pd
import numpy as np
from app.strategies.base import BaseStrategy

class DeadCatShortStrategy(BaseStrategy):
    """
    Over-extension Fade Short Strategy (Limit Order Fishing):
    1. Calculates an extreme upper band: Limit Price = Close + (atr_mult * ATR) (default: 3.0x ATR).
    2. Places a limit order at this price to catch sudden, high-wick spikes from market maker pumps.
    3. Safe Guard: Only activates the fishing grid when the asset is in a long-term downtrend (c < ma_long).
    4. Cleans up positions with a 3.75x Risk-Reward: Stop Loss = Entry + 8%, Take Profit = Entry - 30%.
    """
    def __init__(self, long_period=120, atr_period=14, stop_loss_pct=0.08, take_profit_pct=0.30):
        super().__init__(name=f"FadingShort_{long_period}")
        self.long_period = long_period
        self.atr_period = atr_period
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self.min_required_bars = max(self.long_period + 5, self.atr_period + 5, 30)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates indicators needed for fading strategy:
        - ma_long: 120-day SMA for trend filter
        - atr: Wilder's ATR(14)
        """
        # Ensure numeric types
        df['c'] = pd.to_numeric(df['c'])
        df['h'] = pd.to_numeric(df['h'])
        df['l'] = pd.to_numeric(df['l'])
        df['v'] = pd.to_numeric(df['v'])

        # 1. Long-term trend filter (120-day SMA)
        df['ma_long'] = df['c'].rolling(window=self.long_period).mean()

        # 2. Wilder's ATR(14)
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

    def get_limit_order_price(self, df: pd.DataFrame, atr_mult: float = 3.0) -> float:
        """
        Computes the target short limit price. 
        Only returns a positive limit price if the asset is in a downtrend.
        """
        if len(df) < self.min_required_bars:
            return 0.0

        curr_row = df.iloc[-1]
        c = curr_row['c']
        ma_long = curr_row['ma_long']
        atr = curr_row['atr'] if 'atr' in curr_row and pd.notna(curr_row['atr']) else c * 0.02

        # Safe Guard downtrend filter: only place 숏 limit order when under long MA
        is_downtrend = c < ma_long
        
        if is_downtrend:
            return c + (atr_mult * atr)
        
        return 0.0

    def check_signal(self, df: pd.DataFrame) -> str:
        # Not used since we check limit price triggering dynamically in the backtester loop
        return "NONE"

    def get_stop_loss_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        """
        Places a fixed stop loss at entry price + 8%.
        """
        if pos_type == "SHORT":
            return entry_price * (1.0 + self.stop_loss_pct)
        else:
            return entry_price * (1.0 - self.stop_loss_pct)

    def get_take_profit_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        """
        Places a take profit target 30% below the entry price.
        """
        if pos_type == "SHORT":
            return entry_price * (1.0 - self.take_profit_pct)
        else:
            return entry_price * (1.0 + self.take_profit_pct)
