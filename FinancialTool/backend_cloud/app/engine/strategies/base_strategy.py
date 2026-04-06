from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def analyze(self, df: pd.DataFrame, macro_trend: str) -> dict:
        """Đánh giá nến hiện tại để tìm điểm vào lệnh (Live)"""
        pass

    @abstractmethod
    def analyze_history(self, df: pd.DataFrame) -> list:
        """Quét dữ liệu quá khứ để trả về danh sách Marker vẽ lên Chart"""
        pass