import os

# 1. Xác định Broker đang chạy (mặc định là exness nếu không có tham số)
ACTIVE_BROKER = os.getenv("TRADING_BROKER", "exness").lower()

# 2. Định nghĩa cấu hình chi tiết cho từng Broker
BROKER_CONFIGS = {
    "exness": {
        "suffix": "m",  # Exness Standard
        "watchlist": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
    },
    "oanda": {
        "suffix": ".sml", 
        "watchlist": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
    }
}

# Lấy cấu hình dựa trên broker được chọn
config = BROKER_CONFIGS.get(ACTIVE_BROKER, BROKER_CONFIGS["exness"])

SYMBOL_SUFFIX = config["suffix"]
_BASE_WATCHLIST = config["watchlist"]

WATCHLIST = [f"{s}{SYMBOL_SUFFIX}" if s not in ["BTCUSD", "ETHUSD"] else s for s in _BASE_WATCHLIST]

TIMEFRAMES = {
    "Micro": ["M1", "M5", "M15"], 
    "Watch": ["M1", "M5", "M15", "H1", "H4"],
    "Pairing": {
        "M1": "M15",  # Đánh M1 thì nhìn Trend M15
        "M5": "H1",   # Đánh M5 thì nhìn Trend H1
        "M15": "H4"   # Đánh M15 thì nhìn Trend H4
    },
    "Multi": {
        "M1": ["M5", "M15"],  # Đánh M1 thì nhìn Trend M15
        "M5": ["M15", "H1"],   # Đánh M5 thì nhìn Trend H1
        "M15": ["H1", "H4"],   # Đánh M15 thì nhìn Trend H4
    }
}
MAX_CANDLES_CONFIG = {
    "M1": 40000,
    "M5": 10000,
    "M15": 10000,
    "H1": 3000,
    "H4": 3000,
    "D1": 1500
}

TRADE_DB_PATH = "database/trade_data.db"
BASE_DB_PATH = "database/core_data.db"
ANALYZE_DB_PATH = "database/analyze_data.db"