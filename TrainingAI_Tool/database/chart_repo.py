import sqlite3
import pandas as pd
import os

DB_PATH = "database/chart_data.db"

class ChartRepo:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        # Tạo bảng nếu chưa có
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS ohlcv (
                            symbol TEXT,
                            timeframe TEXT, 
                            time INTEGER,
                            open REAL, high REAL, low REAL, close REAL, volume REAL,
                            PRIMARY KEY (symbol, timeframe, time)
                        )''')

    def save_bulk_data(self, symbol, df, timeframe="M5"):
        if df is None or df.empty: return
        
        # 1. Chuẩn bị DataFrame sạch sẽ
        data = df.copy()
        data['symbol'] = symbol
        data['timeframe'] = timeframe
        
        # Xử lý volume
        if 'tick_volume' in data.columns:
            data = data.rename(columns={'tick_volume': 'volume'})
        elif 'volume' not in data.columns:
            data['volume'] = 0
            
        # Xử lý Time (về dạng số nguyên Unix Timestamp)
        if not pd.api.types.is_integer_dtype(data['time']):
            # Kiểm tra nếu là datetime object thì convert, nếu string/số thì ép kiểu
            try:
                data['time'] = data['time'].astype('int64') // 10**9
            except:
                # Fallback cho trường hợp time là object datetime
                data['time'] = pd.to_datetime(data['time']).astype('int64') // 10**9

        # Chỉ giữ lại các cột cần thiết theo đúng thứ tự
        cols = ['symbol', 'timeframe', 'time', 'open', 'high', 'low', 'close', 'volume']
        
        # 2. Chuyển DataFrame thành List các Tuples (Để nạp vào SQL)
        # records sẽ là dạng: [('XAUUSD', 'M5', 170000, 2000, 2001, ...), (...)]
        records = data[cols].values.tolist()
        
        # 3. Thực thi SQL trực tiếp (Không dùng pd.to_sql nữa để tránh lỗi cú pháp ẩn)
        query = '''
            INSERT OR REPLACE INTO ohlcv (symbol, timeframe, time, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(query, records)
                # Tự động commit nhờ 'with'
        except Exception as e:
            print(f"❌ DB Save Error: {e}")

    def get_history(self, symbol, limit=500, timeframe="M5"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT time, open, high, low, close, volume 
                    FROM ohlcv 
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY time DESC 
                    LIMIT ?
                '''
                df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
            
            if df.empty: return pd.DataFrame()
            
            # Đổi tên volume -> tick_volume để trả về cho App
            return df.rename(columns={'volume': 'tick_volume'}).sort_values('time')
            
        except Exception as e:
            print(f"❌ DB Read Error: {e}")
            return pd.DataFrame()