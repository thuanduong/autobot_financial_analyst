# core/data_service.py
from engines.yahoo_engine import YahooEngine
#from engines.mock_engine import MockEngine

class DataService:
    def __init__(self, symbol="GC=F", default_timeframe="15m", use_mock=False):
        self.symbol = symbol
        self.timeframe = default_timeframe
        self.use_mock = use_mock
        self.engine = self._create_engine()

    def _create_engine(self):
        """Khởi tạo engine dựa trên config hiện tại"""
        #if self.use_mock:
            #return MockEngine(self.symbol, self.timeframe)
        return YahooEngine(self.symbol, self.timeframe)

    def change_symbol(self, new_symbol):
        """Đổi mã giao dịch Runtime"""
        # 1. Kiểm tra sơ bộ (Đơn giản hóa)
        if not new_symbol: return False
        
        print(f"🔄 Đổi sang Symbol mới: {new_symbol}")
        self.symbol = new_symbol.upper() # Luôn viết hoa (vd: btc-usd -> BTC-USD)
        
        # 2. Khởi tạo lại Engine với mã mới
        self.engine = self._create_engine()
        
        # 3. Test thử xem mã có tồn tại không
        df = self.engine.sync()
        if df.empty:
            print("⚠️ Symbol không hợp lệ hoặc Yahoo lỗi!")
            return False        
        return True
    
    def change_timeframe(self, new_tf):
        """Đổi khung thời gian Runtime"""
        if new_tf not in ["1m", "5m", "15m", "30m", "1h", "1d"]:
            return False
        
        print(f"🔄 Switching Data to {new_tf}...")
        self.timeframe = new_tf
        # Tạo lại engine mới với timeframe mới
        self.engine = self._create_engine()
        return True

    def get_data(self):
        return self.engine.sync()