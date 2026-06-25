import pandas as pd
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, name="BaseStrategy"):
        self.name = name

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a DataFrame containing candlestick data (with columns: o, h, l, c, v, t)
        and adds technical indicator columns.
        """
        pass

    @abstractmethod
    def check_signal(self, df: pd.DataFrame) -> str:
        """
        Analyzes the last bars of the DataFrame and returns a signal.
        Possible return values:
        - "LONG": Go long / Buy
        - "SHORT": Go short / Sell
        - "EXIT": Close current position
        - "NONE": Do nothing / Hold
        """
        pass
