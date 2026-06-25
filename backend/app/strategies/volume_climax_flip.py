from app.strategies.volume_climax import VolumeClimaxStrategy
import pandas as pd

class VolumeClimaxFlipStrategy(VolumeClimaxStrategy):
    def __init__(self, bb_period=30, bb_std=2.0,
                 volume_climax_factor=3.0,
                 atr_period=14,
                 stop_atr_mult=3.0):
        # We call the parent init with take_atr_mult=0.0 to disable TP
        # We set use_opposite_exit=False to avoid exiting on opposite BB touch
        super().__init__(
            bb_period=bb_period,
            bb_std=bb_std,
            volume_climax_factor=volume_climax_factor,
            use_opposite_exit=False,
            atr_period=atr_period,
            stop_atr_mult=stop_atr_mult,
            take_atr_mult=0.0
        )
        self.name = f"VolumeClimaxFlip_{bb_period}_{bb_std}"

    def get_take_profit_price(self, df: pd.DataFrame, entry_price: float, pos_type: str) -> float:
        """
        Force disable take profit target. Position will only exit on stop loss
        or opposite signal flip.
        """
        return 0.0
