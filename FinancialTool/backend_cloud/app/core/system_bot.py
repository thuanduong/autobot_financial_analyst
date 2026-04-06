from datetime import datetime
from .virtual_broker import VirtualBroker
from backend_cloud.app.database.repository import TradeRepo

class SystemBot:
    """
    Đại diện cho 1 con Bot cụ thể.
    Ví dụ: 
    - Bot đánh Vàng (Risk 1%)
    - Bot đánh Forex (Risk 2%)
    """
    def __init__(self, repo: TradeRepo, broker: VirtualBroker, bot_id: str, risk_percent: float = 0.01, initial_balance: float = 1000.0):
        self.broker = broker
        self.repo = repo
        self.bot_id = bot_id
        self.risk_percent = risk_percent # Mức rủi ro riêng cho từng bot
        self.initial_balance = initial_balance
        
        # 1. Tạo User Bot trong DB nếu chưa có
        user = self.repo.get_user(self.bot_id)
        if not user:
            print(f"🤖 Initializing New Bot: {self.bot_id}")
            self.repo.create_user(self.bot_id)
            self.repo.update_balance(self.bot_id, self.initial_balance - 10000.0) # Hack để set về đúng 1000
            # Lưu ý: Hàm create_user mặc định 10000, ta cần update lại nếu muốn 1000
            # Hoặc sửa hàm create_user nhận balance

    def check_reset(self):
        """Reset tiền hàng tuần hoặc khi cháy"""
        user = self.repo.get_user(self.bot_id)
        if user and user.balance < (self.initial_balance * 0.1): # Còn dưới 10% thì reset
            print(f"♻️ {self.bot_id} Reset Balance to {self.initial_balance}$")
            # Logic update balance trực tiếp trong DB (cần hàm set_balance trong repo)
            # Ở đây dùng tạm logic cộng bù
            diff = self.initial_balance - user.balance
            self.repo.update_balance(self.bot_id, diff)

    def on_signal(self, signal):
        """
        Xử lý tín hiệu vào lệnh
        """
        # Filter: Có thể thêm logic bot này chỉ đánh cặp nào đó
        # if "XAU" not in signal['symbol'] and "GOLD" in self.bot_id: return

        user = self.repo.get_user(self.bot_id)
        if not user: return

        # 1. Quản lý vốn theo Risk của riêng Bot này
        risk_amount = user.balance * self.risk_percent
        sl_distance = abs(signal['price'] - signal['sl'])
        
        if sl_distance == 0: return 
        
        contract_size = 100 if "XAU" in signal['symbol'] else 100000
        
        # Công thức Volume
        volume = risk_amount / (sl_distance * contract_size)
        
        # Làm tròn (Min 0.01)
        volume = max(0.01, round(volume, 2))

        # 2. Vào lệnh
        self.broker.open_paper_order(
            user_id=self.bot_id,
            symbol=signal['symbol'],
            side=signal['action'],
            volume=volume,
            sl=signal['sl'],
            tp=signal.get('tp', 0),
            source="AUTO" # Đánh dấu là Bot
        )