import MetaTrader5 as mt5
import pandas as pd
import ta
import time
from config.settings import MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

class MT5Provider:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5Provider, cls).__new__(cls)
            cls._instance.connected = False
        return cls._instance

    def connect(self):
        if self.connected: return True
        print("🔌 Đang kết nối MT5...")
        
        # Tự động bật App nếu chưa chạy
        if not mt5.initialize(path=MT5_PATH):
            print("⚠️ MT5 chưa bật, đang thử khởi động lại...")
            if not mt5.initialize(path=MT5_PATH):
                print(f"❌ Lỗi Fatal: {mt5.last_error()}")
                return False
        
        # Login để đảm bảo data chuẩn
        if mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
            print(f"✅ Đã Login Account {MT5_LOGIN}")
            self.connected = True
            return True
        return False

    def get_data(self, symbol, n=100):
        if not self.connected: self.connect()
        
        selected = mt5.symbol_select(symbol, True)
        if not selected:
            print(f"⚠️ Không tìm thấy mã '{symbol}' trên sàn OANDA. Hãy kiểm tra lại tên.")
            return None
        
        # Lấy nến M15
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, n)
        if rates is None or len(rates) == 0:
            err = mt5.last_error()
            print(f"❌ Lỗi lấy data {symbol}: {err}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Tính chỉ báo bằng thư viện 'ta'
        try:
            df['RSI'] = ta.momentum.rsi(df['close'], window=14, fillna=True)
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['BBU'] = bb.bollinger_hband()
            df['BBL'] = bb.bollinger_lband()
        except: pass
        
        return df

    def get_price(self, symbol):
        tick = mt5.symbol_info_tick(symbol)
        return tick.last if tick else 0.0