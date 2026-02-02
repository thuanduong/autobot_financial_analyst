import os

MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe" 

MT5_LOGIN = 7037254
MT5_PASSWORD = "854804v3@Zero"
MT5_SERVER = "OANDA_Global-Live-1"

WATCHLIST = [
    "XAUUSD.sml",  # Vàng
    "EURUSD.sml",  # Euro
    "GBPUSD.sml",  # Bảng Anh
    "USDJPY.sml",  # Yên Nhật
    "BTCUSD"   # Bitcoinz
]

TIMEFRAMES = {
    "Macro": "H1",  # Khung xác định xu hướng
    "Micro": ["M5", "M15", "H1", "H4"] # Các khung hiển thị trên Radar
}

DB_PATH = "database/trade_data.db"