import MetaTrader5 as mt5
import pandas as pd

class MT5Feed:
    """
    Class này chỉ dùng để LẤY DỮ LIỆU.
    Tuyệt đối không có hàm order_send ở đây.
    """
    def __init__(self):
        self.connected = False
        self.tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4
        }

    def connect(self):
        if not mt5.initialize():
            print("❌ MT5 Init Failed")
            return False
        self.connected = True
        return True

    def get_price(self, symbol):
        if not self.connected: self.connect()
        
        # Đảm bảo symbol có trong Market Watch
        if not mt5.symbol_select(symbol, True):
            return None

        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return tick.last
        return None

    def get_candles(self, symbol, timeframe="M5", n=100):
        """Lấy nến để phân tích kỹ thuật"""
        if not self.connected: self.connect()
        
        mt5_tf = self.tf_map.get(timeframe, mt5.TIMEFRAME_M5)
        
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, n)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_candles_range(self, symbol, timeframe, time_from, time_to):
        """Lấy nến từ thời điểm A đến thời điểm B"""
        # Convert string timeframe sang constant MT5 (M1, M5...)
        mt5_tf = self.tf_map.get(timeframe, mt5.TIMEFRAME_M5)
        
        # Gọi MT5 lấy range
        rates = mt5.copy_rates_range(symbol, mt5_tf, time_from, time_to)
        
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
            
        # Convert sang DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

mt5_feed = MT5Feed() # Singleton