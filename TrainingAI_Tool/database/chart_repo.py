import sqlite3
import pandas as pd
import os

DB_PATH = "database/chart_data.db"

class ChartRepo:
    def __init__(self):
        os.makedirs("database", exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol TEXT,
                time INTEGER,
                open REAL, high REAL, low REAL, close REAL,
                tick_volume INTEGER,
                PRIMARY KEY (symbol, time)
            )
        """)
        self.conn.commit()

    def save_bulk_data(self, symbol, df):
        if df is None or df.empty: return
        data = []
        for _, row in df.iterrows():
            # Xử lý time an toàn khi lưu
            ts = row['time']
            if hasattr(ts, 'timestamp'): ts = int(ts.timestamp())
            else: ts = int(ts)
                
            data.append((symbol, ts, row['open'], row['high'], row['low'], row['close'], 0))

        with self.conn:
            self.conn.executemany("INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)", data)

    def get_history(self, symbol, limit=500):
        query = "SELECT time, open, high, low, close FROM ohlcv WHERE symbol=? ORDER BY time ASC LIMIT ?"
        return pd.read_sql_query(query, self.conn, params=(symbol, limit))