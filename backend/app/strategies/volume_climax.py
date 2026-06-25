import pandas as pd
import numpy as np
from app.strategies.base import BaseStrategy
from app.core.config import Config

class VolumeClimaxStrategy(BaseStrategy):
    def __init__(self, bb_period=30, bb_std=2.0,
                 volume_climax_factor=3.0,
                 use_opposite_exit=False,
                 atr_period=14,
                 stop_atr_mult=1.5,
                 take_atr_mult=3.0):
        super().__init__(name=f"VolumeClimax_{bb_period}_{bb_std}")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.volume_climax_factor = volume_climax_factor
        self.use_opposite_exit = use_opposite_exit
        self.atr_period = atr_period
        self.stop_atr_mult = stop_atr_mult
        self.take_atr_mult = take_atr_mult
        self.long_period = max(self.bb_period + 5, self.atr_period + 5, 30)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Bollinger Bands, Volume Indicators, and Wilder's ATR.
        """
        # Ensure prices and volume are numeric
        df['c'] = pd.to_numeric(df['c'])
        df['h'] = pd.to_numeric(df['h'])
        df['l'] = pd.to_numeric(df['l'])
        df['v'] = pd.to_numeric(df['v'])
        
        # 1. Bollinger Bands (30, 2.0)
        df['bb_middle'] = df['c'].rolling(window=self.bb_period).mean()
        df['bb_std'] = df['c'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * self.bb_std)

        # 2. Volume Indicators
        df['vol_ma'] = df['v'].rolling(window=20).mean()
        df['vol_ratio'] = df['v'] / df['vol_ma']
        
        # 3. Wilder's ATR(14) for dynamic TP/SL
        df['prev_c'] = df['c'].shift(1)
        df['tr1'] = df['h'] - df['l']
        df['tr2'] = (df['h'] - df['prev_c']).abs()
        df['tr3'] = (df['l'] - df['prev_c']).abs()
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].ewm(alpha=1/self.atr_period, adjust=False).mean()

        # Cleanup temporary columns
        temp_cols = ['prev_c', 'tr1', 'tr2', 'tr3', 'tr']
        df = df.drop(columns=[col for col in temp_cols if col in df.columns])
        
        return df

    def check_signal(self, df: pd.DataFrame) -> str:
        """
        Analyzes current candlestick and volume indicators to generate signals:
        - BUY/LONG (Volume Climax Rebound): price drops below lower BB and rebounds back, with volume spike.
        - SELL/SHORT (Volume Climax Rebound): price spikes above upper BB and drops back, with volume spike.
        - EXIT: price touches the opposite Bollinger Band (Upper BB for long, Lower BB for short).
        """
        if len(df) < self.long_period:
            return "NONE"

        curr_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        c = curr_row['c']
        prev_c = prev_row['c']

        bb_upper = curr_row['bb_upper']
        bb_lower = curr_row['bb_lower']
        
        prev_bb_upper = prev_row['bb_upper']
        prev_bb_lower = prev_row['bb_lower']

        vol_ratio = curr_row['vol_ratio'] if 'vol_ratio' in curr_row else 1.0
        prev_vol_ratio = prev_row['vol_ratio'] if 'vol_ratio' in prev_row else 1.0

        # Climax check: current or previous candle has a volume spike
        has_climax = (vol_ratio >= self.volume_climax_factor) or (prev_vol_ratio >= self.volume_climax_factor)

        # 1. Entry Signals
        # BUY / LONG: Price dips below Lower BB and breaks back above it, with volume climax
        if prev_c <= prev_bb_lower and c > bb_lower and has_climax:
            return "LONG"
        # SELL / SHORT: Price spikes above Upper BB and breaks back below it, with volume climax
        elif prev_c >= prev_bb_upper and c < bb_upper and has_climax:
            return "SHORT"

        # 2. Exit Signals (Opposite Band Touch)
        # If price reaches the opposite band, we return EXIT if enabled.
        if self.use_opposite_exit:
            if c >= bb_upper:
                return "EXIT"
            elif c <= bb_lower:
                return "EXIT"

        return "NONE"

    def get_stop_loss_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        curr_row = df.iloc[-1]
        atr = curr_row['atr'] if 'atr' in curr_row else entry_price * 0.02
        if pos_type == "LONG":
            return entry_price - (self.stop_atr_mult * atr)
        else:
            return entry_price + (self.stop_atr_mult * atr)

    def get_take_profit_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        curr_row = df.iloc[-1]
        atr = curr_row['atr'] if 'atr' in curr_row else entry_price * 0.05
        if pos_type == "LONG":
            return entry_price + (self.take_atr_mult * atr)
        else:
            return entry_price - (self.take_atr_mult * atr)
