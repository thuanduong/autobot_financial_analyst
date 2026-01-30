from database.repository import TradeRepo
from datetime import datetime

class PortfolioManager:
    def __init__(self, username):
        self.username = username
        self.repo = TradeRepo()
        self.user_data = self.repo.get_user(username)

    def open_position(self, symbol, side, price, leverage=100):
        user = self.repo.get_user(self.username)
        if not user: return

        # 1. Tính toán Volume theo Risk
        balance = user['balance']
        risk_money = balance * user['risk_pct'] # Ví dụ 1000 * 1% = 10$
        
        # Giả định: Đánh sao cho Margin = Risk Money (Cách an toàn)
        # Margin = (Price * Vol) / Leverage => Vol = (Margin * Lev) / Price
        vol = (risk_money * leverage) / price if price > 0 else 0.01
        vol = round(vol, 2)
        if vol < 0.01: vol = 0.01

        # 2. Lưu lệnh
        order_data = {
            "username": self.username,
            "symbol": symbol,
            "type": side,
            "entry": price,
            "vol": vol,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.repo.create_order(order_data)
        print(f"🚀 {self.username} OPEN {side} {symbol} | Vol: {vol}")

    def close_position(self, symbol, current_price):
        open_order = self.repo.get_open_order(self.username, symbol)
        if not open_order:
            print(f"⚠️ Không có lệnh mở nào cho {symbol}")
            return False
        entry = open_order['entry_price']
        vol = open_order['volume']
        side = open_order['type']

        pnl = 0.0
        if side == 'BUY':
            pnl = (current_price - entry) * vol
        else:
            pnl = (entry - current_price) * vol
        pnl = round(pnl, 2)

        close_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.repo.close_order(self.username, symbol, current_price, pnl, close_time)
        return True