import MetaTrader5 as mt5
import pandas as pd
import ta
import time
from config.settings import MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

class MT5Provider:
    _instance = None
    
    def __init__(self):
        self.connected = False
        self.TF_MAP = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }

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

    def get_data(self, symbol, n=100, timeframe="M5"):
        if not self.connected: 
            if not self.connect(): return None
        
        # 1. Đảm bảo Symbol đã được Select trong Market Watch (Rất quan trọng)
        selected = mt5.symbol_select(symbol, True)
        if not selected:
            print(f"⚠️ Không tìm thấy mã '{symbol}'. Hãy kiểm tra lại tên.")
            return None
        
        # 2. Lấy timeframe constant
        tf_constant = self.TF_MAP.get(timeframe, mt5.TIMEFRAME_M5)
        
        # 3. Lấy dữ liệu
        rates = mt5.copy_rates_from_pos(symbol, tf_constant, 0, n)
        
        if rates is None or len(rates) == 0:
            err = mt5.last_error()
            # Chỉ in lỗi nếu không phải là lỗi ngắt kết nối thông thường
            if err[0] != 1: 
                print(f"❌ Lỗi lấy data {symbol}: {err}")
            return None
        
        # 4. Chuyển sang DataFrame (CHỈ LẤY DỮ LIỆU THÔ)
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        if 'tick_volume' not in df.columns:
            # Nếu có real_volume thì dùng, không thì bằng 0
            if 'real_volume' in df.columns:
                df['tick_volume'] = df['real_volume']
            else:
                df['tick_volume'] = 0
                
        # Trả về các cột chuẩn để lưu vào DB và vẽ chart
        return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]

    def get_price(self, symbol):
        tick = mt5.symbol_info_tick(symbol)
        return tick.last if tick else 0.0