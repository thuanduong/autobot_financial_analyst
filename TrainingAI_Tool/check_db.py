import sqlite3
import pandas as pd # Cần cài pandas: pip install pandas

# Kết nối DB
conn = sqlite3.connect("database/trade_data.db")

print("\n--- 5 LỆNH GẦN NHẤT ---")
df = pd.read_sql_query("SELECT id, username, symbol, type, status, pnl, close_time FROM orders ORDER BY id DESC LIMIT 5", conn)

# In ra bảng đẹp
print(df.to_string(index=False))

conn.close()