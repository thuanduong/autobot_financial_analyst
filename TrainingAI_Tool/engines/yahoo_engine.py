from .base_engine import BaseDataEngine
from database.db_manager import DBManager
import yfinance as yf
import pandas as pd

class YahooEngine(BaseDataEngine):
    def __init__(self, symbol, timeframe):
        super().__init__(symbol, timeframe)
        self.db = DBManager()

    def sync(self):
        try:
            # 1. Tải dữ liệu
            # Lưu ý: period="5d" cho khung thời gian ngắn (15m)
            df = yf.download(
                tickers=self.symbol, 
                period="5d", 
                interval=self.timeframe, 
                progress=False
            )
            
            if df.empty: 
                print(f"⚠️ Yahoo trả về rỗng cho mã {self.symbol}")
                return pd.DataFrame()

            # --- KHẮC PHỤC LỖI MULTI-INDEX (QUAN TRỌNG) ---
            # Nếu cột là dạng MultiIndex (vd: ('Close', 'GC=F')), ta chỉ lấy tầng đầu tiên ('Close')
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 2. Reset Index để đưa cột Date/Datetime ra ngoài
            df = df.reset_index()
            
            # 3. Chuẩn hóa tên cột
            # Ép kiểu thành string trước khi lower() để tránh lỗi tuple
            df.columns = [str(c).lower() for c in df.columns] 
            
            # Xử lý trường hợp tên cột ngày tháng khác nhau
            if 'datetime' in df.columns: 
                df = df.rename(columns={'datetime': 'time'})
            elif 'date' in df.columns: 
                df = df.rename(columns={'date': 'time'})
            
            # 4. Đảm bảo đủ các cột cần thiết, nếu thiếu điền 0
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns: 
                    df[col] = 0.0

            # 5. Lưu vào Database
            # print(f"-> [Yahoo] Tải được {len(df)} nến cho {self.symbol}")
            self.db.save_candles(df, self.symbol)

            # 6. Trả về dữ liệu từ DB (để đảm bảo format chuẩn nhất)
            return self.db.load_recent(self.symbol, limit=200)

        except Exception as e:
            print(f"❌ Lỗi YahooEngine: {e}")
            # In ra lỗi chi tiết để debug nếu cần
            import traceback
            traceback.print_exc()
            return pd.DataFrame()