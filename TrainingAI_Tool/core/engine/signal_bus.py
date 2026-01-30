from database.repository import TradeRepo
from core.user.portfolio import PortfolioManager
from core.data_provider.mt5_provider import MT5Provider

class SignalBus:
    def __init__(self):
        self.repo = TradeRepo()
        self.mt5 = MT5Provider()

    async def process_signal(self, signal):
        """
        Signal: {'symbol': 'XAUUSD', 'action': 'BUY', 'score': 85}
        """
        symbol = signal['symbol']
        action = signal['action']
        price = self.mt5.get_price(symbol)
        
        if price == 0: return

        # Lấy danh sách user
        users = self.repo.get_all_users()
        for user in users:
            username = user['username']
            # Chỉ vào lệnh cho Bot Hệ Thống hoặc User bật Auto
            if username == "system_bot" or user['is_auto']:
                pm = PortfolioManager(username)
                
                # Logic đơn giản: Có tín hiệu là đóng lệnh cũ -> mở lệnh mới
                # pm.close_position(symbol, price) 
                pm.open_position(symbol, action, price)