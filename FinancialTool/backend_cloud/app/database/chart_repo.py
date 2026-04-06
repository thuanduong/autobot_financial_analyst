import sqlite3
import pandas as pd
import os
import numpy as np
from backend_cloud.config.settings import TRADE_DB_PATH

class ChartRepo:
    def __init__(self, db_path=TRADE_DB_PATH):
        os.makedirs("database", exist_ok=True)
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

    def save_bulk_data(self, symbol, df, timeframe="M5", max_records=25000):
        """
        Lưu dữ liệu vào DB và tự động xóa các nến cũ nếu vượt quá giới hạn.
        :param max_records: Số lượng nến tối đa giữ lại cho mỗi cặp/khung
        """
        if df is None or df.empty: return
        
        try:
            data = df.copy()
            if pd.api.types.is_object_dtype(data['time']) or pd.api.types.is_string_dtype(data['time']):
                data['time'] = pd.to_datetime(data['time'], errors='coerce')

            if pd.api.types.is_datetime64_any_dtype(data['time']):
                raw_ns = data['time'].astype('int64')
                data['time'] = np.where(raw_ns < 1e12, raw_ns, raw_ns // 10**9)
            else:
                raw_num = data['time'].astype('int64')
                data['time'] = np.where(raw_num > 1e12, raw_num // 1000, raw_num)

            data['symbol'] = symbol
            data['timeframe'] = timeframe
            
            if 'tick_volume' in data.columns:
                data = data.rename(columns={'tick_volume': 'volume'})
            elif 'volume' not in data.columns:
                data['volume'] = 0

            cols = ['symbol', 'timeframe', 'time', 'open', 'high', 'low', 'close', 'volume']
            records = data[cols].values.tolist()

            insert_query = '''
                INSERT OR REPLACE INTO ohlcv (symbol, timeframe, time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            cleanup_query = '''
                DELETE FROM ohlcv 
                WHERE symbol = ? AND timeframe = ? 
                  AND time < (
                    SELECT time 
                    FROM ohlcv 
                    WHERE symbol = ? AND timeframe = ? 
                    ORDER BY time DESC 
                    LIMIT 1 OFFSET ?
                  )
            '''

            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(insert_query, records)
                
                if max_records > 0:
                    conn.execute(cleanup_query, (symbol, timeframe, symbol, timeframe, max_records))
                
        except Exception as e:
            print(f"❌ DB Save & Cleanup Error: {e}")

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
        
    # --- 1. Hàm lấy nến mới nhất (Initial Load) ---
    def get_recent_candles(self, symbol, timeframe, limit=500):
        """Lấy N nến mới nhất để vẽ Chart lúc đầu"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Lấy DESC để lấy cái mới nhất trước, sau đó đảo ngược
                query = '''SELECT time, open, high, low, close, volume 
                           FROM ohlcv WHERE symbol=? AND timeframe=? 
                           ORDER BY time DESC LIMIT ?'''
                cursor = conn.execute(query, (symbol, timeframe, limit))
                rows = cursor.fetchall()
            print(f'DB history {len(rows)}')
            # Đảo ngược lại để trả về [Cũ -> Mới]
            return [{
                "time": row[0], "open": row[1], "high": row[2], 
                "low": row[3], "close": row[4], "value": row[5]
            } for row in reversed(rows)]
        except Exception as e:
            print(f"DB Read Error (Recent): {e}")
            return []

    # --- 2. Hàm lấy nến theo khoảng thời gian (Lazy Load / History) ---
    def get_candles_in_range(self, symbol, timeframe, from_time, to_time):
        """Lấy nến trong khoảng [from_time, to_time] để fill lỗ hổng hoặc scroll"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''SELECT time, open, high, low, close, volume 
                           FROM ohlcv 
                           WHERE symbol=? AND timeframe=? 
                           AND time >= ? AND time <= ? 
                           ORDER BY time ASC'''
                cursor = conn.execute(query, (symbol, timeframe, from_time, to_time))
                rows = cursor.fetchall()

            return [{
                "time": row[0], "open": row[1], "high": row[2], 
                "low": row[3], "close": row[4], "value": row[5]
            } for row in rows]
        except Exception as e:
            print(f"DB Read Error (Range): {e}")
            return []