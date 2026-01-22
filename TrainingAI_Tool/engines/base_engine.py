from abc import ABC, abstractmethod
import pandas as pd

class BaseDataEngine(ABC):
    def __init__(self, symbol, timeframe):
        self.symbol = symbol
        self.timeframe = timeframe

    @abstractmethod
    def sync(self) -> pd.DataFrame:
        """Hàm này bắt buộc phải trả về DataFrame chuẩn"""
        pass