import sqlite3
import pandas as pd

class DBManager:
    def __init__(self, db_name="database.db"):
        self.db_name = db_name
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                time TEXT,
                symbol TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (time, symbol)
            )
        ''')
        conn.commit()
        conn.close()

    def save_candles(self, df, symbol):
        """Lưu DataFrame vào SQLite"""
        if df.empty: return

        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        data_to_insert = []
        for _, row in df.iterrows():
            # Chắc chắn time là string ISO chuẩn
            t_str = str(row['time']) if isinstance(row['time'], str) else row['time'].strftime('%Y-%m-%dT%H:%M:%S')
            
            data_to_insert.append((
                t_str, symbol, 
                row['open'], row['high'], row['low'], row['close'], row['volume']
            ))

        c.executemany('''
            INSERT OR REPLACE INTO candles (time, symbol, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
        
        conn.commit()
        conn.close()
        # print(f"[DB] Đã lưu {len(df)} dòng cho {symbol}")

    def load_recent(self, symbol, limit=300):
        """Lấy dữ liệu để phân tích"""
        conn = sqlite3.connect(self.db_name)
        query = f"SELECT * FROM candles WHERE symbol = '{symbol}' ORDER BY time DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df = df.sort_values(by='time').reset_index(drop=True)
            
        return df