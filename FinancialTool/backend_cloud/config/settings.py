# Cấu hình Hậu tố (Suffix) theo sàn giao dịch:
# - Exness Standard: "m" (VD: EURUSDm)
# - Exness Pro: "" (Không có suffix)
# - Oanda: ".sml" hoặc ".pro"
SYMBOL_SUFFIX = ".sml" 

# Danh sách mã gốc muốn giao dịch
_BASE_WATCHLIST = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]

# Tự động tạo WATCHLIST dựa trên hậu tố của sàn
# Lưu ý: Một số mã như BTCUSD có thể không có suffix tùy sàn, bạn có thể chỉnh sửa logic list comprehension nếu cần
WATCHLIST = [f"{s}{SYMBOL_SUFFIX}" if s != "BTCUSD" else s for s in _BASE_WATCHLIST]

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