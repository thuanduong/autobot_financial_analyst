from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> dict:
        """Nhận DataFrame -> Trả về JSON kết quả"""
        pass