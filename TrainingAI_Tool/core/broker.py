# File: core/broker.py
import datetime

class VirtualBroker:
    def __init__(self, initial_balance=10000):
        self.balance = initial_balance  # Số dư ban đầu (ví dụ $10,000)
        self.position = None            # Chỉ giữ 1 lệnh tại 1 thời điểm cho đơn giản
        self.trade_history = []         # Lưu lịch sử giao dịch

    def execute_trade(self, signal, current_price, time):
        """
        signal: 'BUY' (Long), 'SELL' (Short), 'CLOSE' (Đóng lệnh)
        """
        # 1. Logic ĐÓNG lệnh cũ nếu có tín hiệu ngược chiều hoặc tín hiệu đóng
        if self.position:
            p = self.position
            # Nếu đang Long mà gặp báo Sell -> Đóng Long
            if (p['type'] == 'LONG' and signal == 'SELL') or signal == 'CLOSE':
                self._close_position(current_price, time)
            
            # Nếu đang Short mà gặp báo Buy -> Đóng Short
            elif (p['type'] == 'SHORT' and signal == 'BUY') or signal == 'CLOSE':
                self._close_position(current_price, time)

        # 2. Logic MỞ lệnh mới (chỉ mở khi chưa có lệnh nào)
        if self.position is None and signal in ['BUY', 'SELL']:
            self._open_position(signal, current_price, time)

    def _open_position(self, signal, price, time):
        # Quy ước: BUY -> LONG, SELL -> SHORT
        pos_type = 'LONG' if signal == 'BUY' else 'SHORT'
        
        self.position = {
            "type": pos_type,
            "entry_price": price,
            "entry_time": time,
            "volume": 1 # Giả sử đánh 1 lot/unit standard
        }
        print(f"OPEN {pos_type} at {price}")

    def _close_position(self, current_price, time):
        p = self.position
        profit = 0
        
        # Tính toán lời lỗ
        if p['type'] == 'LONG':
            profit = (current_price - p['entry_price']) * p['volume']
        else: # SHORT
            profit = (p['entry_price'] - current_price) * p['volume']
            
        # Cộng vào tài khoản
        self.balance += profit
        
        # Lưu lịch sử
        trade_record = {
            "type": p['type'],
            "entry": p['entry_price'],
            "exit": current_price,
            "profit": round(profit, 2),
            "time_exit": time
        }
        self.trade_history.append(trade_record)
        
        print(f"CLOSE {p['type']} at {current_price} | P/L: {profit:.2f}")
        self.position = None # Reset vị thế

    def get_status(self, current_price):
        """Trả về trạng thái hiện tại để hiển thị Web"""
        floating_pl = 0 # Lời lỗ thả nổi (chưa chốt)
        
        if self.position:
            if self.position['type'] == 'LONG':
                floating_pl = (current_price - self.position['entry_price']) * self.position['volume']
            else:
                floating_pl = (self.position['entry_price'] - current_price) * self.position['volume']

        return {
            "balance": round(self.balance, 2),
            "equity": round(self.balance + floating_pl, 2), # Tài sản thực tế
            "open_position": self.position,
            "floating_pl": round(floating_pl, 2),
            "history_count": len(self.trade_history)
        }