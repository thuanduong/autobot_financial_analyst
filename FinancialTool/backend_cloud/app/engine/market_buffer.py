import pandas as pd
from typing import Dict

class MarketDataBuffer:
    def __init__(self, max_size: int = 300):
        # Lưu trữ DataFrame theo format: { "XAUUSD.sml_M5": df, "EURUSD.sml_H1": df }
        self.buffers: Dict[str, pd.DataFrame] = {}
        self.max_size = max_size 

    def init_buffer(self, symbol: str, timeframe: str, df_history: pd.DataFrame):
        """Đổ dữ liệu từ lúc khởi động vào RAM"""
        key = f"{symbol}_{timeframe}"
        if df_history is None or df_history.empty: return
        
        # Chỉ giữ lại đúng số lượng max_size để khỏi tràn RAM
        df = df_history.sort_values('time').tail(self.max_size).reset_index(drop=True)
        self.buffers[key] = df
        print(f"🧠 RAM Cache nạp thành công {key}: {len(df)} nến.")

    def update_from_df(self, symbol: str, timeframe: str, df_new: pd.DataFrame):
        """
        Trộn 5 nến mới lấy từ MT5 vào Buffer hiện tại.
        Sử dụng kỹ thuật drop_duplicates cực kỳ an toàn và siêu tốc.
        """
        key = f"{symbol}_{timeframe}"
        if key not in self.buffers or df_new is None or df_new.empty: 
            return
            
        df_ram = self.buffers[key]
        
        # 1. Nối df cũ và df mới lại với nhau
        combined = pd.concat([df_ram, df_new])
        
        # 2. Xóa các dòng trùng lặp thời gian, giữ lại dòng CƯỚI CÙNG (keep='last')
        # Vì dòng cuối cùng chính là dữ liệu mới nhất (giá đang chạy) từ df_new
        combined = combined.drop_duplicates(subset=['time'], keep='last')
        
        # 3. Cắt gọt lại đúng size 300
        combined = combined.sort_values('time').tail(self.max_size).reset_index(drop=True)
        
        self.buffers[key] = combined

    def get_dataframe(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Trích xuất dữ liệu cho Technical Engine"""
        key = f"{symbol}_{timeframe}"
        return self.buffers.get(key, pd.DataFrame())

# Singleton dùng chung cho toàn dự án
market_buffer = MarketDataBuffer(max_size=300)