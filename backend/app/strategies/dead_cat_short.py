import pandas as pd
import numpy as np
from app.strategies.base import BaseStrategy

class DeadCatShortStrategy(BaseStrategy):
    """
    Late Confirmation Pump & Dump Short Strategy:
    1. Detects a pump (+30% from local min to local max) within a lookback window (e.g. 20 bars).
    2. Verifies that the peak of the pump was accompanied by volume distribution (e.g. >= 4x of normal volume).
    3. Triggers SHORT when the coin enters the "oblivion/bleeding phase":
       - Volume has dried up completely (Dying Volume: <= 10% of peak volume).
       - Price has broken down significantly (Breakdown: >= 30% drop from peak).
       - Price is still above the pump starting point (local_min).
    4. Places a fixed, ultra-tight stop loss at entry_price + 8% to limit drawdown from short squeezes.
    5. Sets a high take profit target at entry_price - 45% to harvest the bleeding, yielding a 1:5.6 Risk-Reward ratio.
    """
    def __init__(self, long_period=120, pump_lookback=20, pump_threshold=0.30,
                 vol_climax_factor=4.0, vol_die_ratio=0.10, breakdown_threshold=0.30,
                 stop_loss_pct=0.08, take_profit_pct=0.45):
        super().__init__(name=f"LatePumpDumpShort_{pump_lookback}")
        self.long_period = long_period
        self.pump_lookback = pump_lookback
        self.pump_threshold = pump_threshold
        self.vol_climax_factor = vol_climax_factor
        self.vol_die_ratio = vol_die_ratio
        self.breakdown_threshold = breakdown_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self.min_required_bars = max(self.long_period + 5, self.pump_lookback + 10, 35)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates baseline indicators:
        - vol_ma_30: normal average trading volume
        - ma_long: 120-day SMA for trend filter
        """
        # Ensure numeric types
        df['c'] = pd.to_numeric(df['c'])
        df['h'] = pd.to_numeric(df['h'])
        df['l'] = pd.to_numeric(df['l'])
        df['v'] = pd.to_numeric(df['v'])

        # Baseline volume (30-period simple moving average)
        df['vol_ma_30'] = df['v'].rolling(window=30).mean()
        
        # Long-term trend filter (120-day SMA)
        df['ma_long'] = df['c'].rolling(window=self.long_period).mean()

        return df

    def check_signal(self, df: pd.DataFrame) -> str:
        """
        Scans the recent lookback window for the end of a Pump & Dump cycle.
        """
        if len(df) < self.min_required_bars:
            return "NONE"

        # Fetch current slice of lookback
        recent_slice = df.iloc[-self.pump_lookback:]
        
        # Calculate local extremes
        local_min = recent_slice['l'].min()
        local_max = recent_slice['h'].max()
        
        if local_min <= 0:
            return "NONE"
            
        # 1. Check if a qualified pump occurred (+30% or higher)
        pump_pct = (local_max - local_min) / local_min
        if pump_pct < self.pump_threshold:
            return "NONE"
            
        # Find the peak price index inside the lookback slice
        max_idx = recent_slice['h'].idxmax()
        peak_row = df.loc[max_idx]
        
        peak_vol = peak_row['v']
        peak_price = peak_row['h']
        
        # 2. Check if the peak had distribution volume (>= 4x of baseline volume at that time)
        vol_baseline = peak_row['vol_ma_30'] if 'vol_ma_30' in peak_row and pd.notna(peak_row['vol_ma_30']) else 1.0
        if vol_baseline <= 0:
            vol_baseline = 1.0
            
        has_distribution = peak_vol >= (vol_baseline * self.vol_climax_factor)
        if not has_distribution:
            return "NONE"
            
        # 3. Analyze post-peak candles (from the peak index to current row)
        curr_row = df.iloc[-1]
        c_price = curr_row['c']
        c_vol = curr_row['v']
        
        # Current index in dataframe
        curr_idx = df.index[-1]
        
        # Ensure current index is strictly after the peak index (we only short the descent)
        if curr_idx <= max_idx:
            return "NONE"
            
        # Check if volume has dried up completely (Dying Volume: <= 10% of peak volume)
        volume_died = c_vol <= (peak_vol * self.vol_die_ratio)
        
        # Check if price has broken down significantly (Breakdown: >= 30% drop from peak price)
        price_drop = (peak_price - c_price) / peak_price
        price_broken = price_drop >= self.breakdown_threshold
        
        # Guard: Do not short if price has already bled past the local minimum (pump starting point)
        too_far_gone = c_price <= local_min
        
        if volume_died and price_broken and not too_far_gone:
            return "SHORT"

        return "NONE"

    def get_stop_loss_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        """
        Places a fixed, ultra-tight stop loss at entry price + 8%.
        """
        if pos_type == "SHORT":
            return entry_price * (1.0 + self.stop_loss_pct)
        else:
            return entry_price * (1.0 - self.stop_loss_pct)

    def get_take_profit_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        """
        Places a high take profit target 45% below the entry price.
        """
        if pos_type == "SHORT":
            return entry_price * (1.0 - self.take_profit_pct)
        else:
            return entry_price * (1.0 + self.take_profit_pct)
