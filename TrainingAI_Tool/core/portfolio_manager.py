# core/portfolio_manager.py
from pydantic import BaseModel
import pandas as pd
from core.user_manager import UserManager
import datetime

user_db = UserManager()

class SubAccount:
    """Tài khoản con cho từng chiến thuật"""
    def __init__(self, username, name, initial_capital=10000):
        self.name = name
        self.username = username
        self.initial_balance = initial_capital
        state = user_db.load_strategy_state(username, name)
        
        if state:
            self.balance = state['balance']
            self.leverage = state['leverage']
            self.bet_amount = state['bet_amount']
            self.history = state['history']
        else:
            # Mặc định nếu chưa có trong DB
            self.balance = initial_capital
            self.leverage = 100
            self.bet_amount = 50
            self.history = []
            
        self.position = None 
        self.logs = []

    def _save_to_db(self):
        """Lưu trạng thái hiện tại vào DB"""
        user_db.save_strategy_state(
            self.username, self.name, 
            self.balance, self.leverage, self.bet_amount, self.history
        )

    def add_log(self, message):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.insert(0, f"[{now}] {message}")
        if len(self.logs) > 20: self.logs.pop()

    def reset_capital(self, capital):
        self.balance = capital
        self.initial_balance = capital
        self.history = []
        self.position = None
        self._save_to_db() # Lưu ngay
        self.add_log(f"🔄 Reset Vốn: {capital}$")

    def update_config(self, leverage, bet_amount):
        self.leverage = leverage
        self.bet_amount = bet_amount
        self._save_to_db() # Lưu ngay

    def process_signal(self, signal_data, price, time, custom_margin=None):
        """
        Điều phối lệnh: Check SL/TP -> Check Close -> Check Open
        """
        # 1. Trích xuất dữ liệu
        action = "HOLD"
        new_sl = 0
        new_tp = 0
        
        if isinstance(signal_data, dict):
            action = signal_data.get('action')
            new_sl = signal_data.get('sl')
            new_tp = signal_data.get('tp')
        else:
            action = signal_data

        # Log tín hiệu nếu có biến động (trừ HOLD)
        if action != "HOLD":
            # Chỉ log nếu tín hiệu khác với trạng thái hiện tại
            # (Để tránh spam log mỗi khi refresh)
            pass 

        # 2. XỬ LÝ LỆNH ĐANG MỞ (Check SL/TP và Tín hiệu Đóng)
        if self.position:
            p = self.position
            set_sl = p.get('sl_price', 0)
            set_tp = p.get('tp_price', 0)
            
            # A. KIỂM TRA SL/TP CỨNG
            is_sl = False; is_tp = False

            if p['type'] == "LONG":
                if set_sl > 0 and price <= set_sl: is_sl = True
                if set_tp > 0 and price >= set_tp: is_tp = True
            else: # SHORT
                if set_sl > 0 and price >= set_sl: is_sl = True
                if set_tp > 0 and price <= set_tp: is_tp = True
            
            if is_sl:
                self._close(price, time, reason="STOP_LOSS ✂️")
                return # Đóng xong thì return ngay
            if is_tp:
                self._close(price, time, reason="TAKE_PROFIT 💰")
                return

            # B. KIỂM TRA TÍN HIỆU ĐÓNG/ĐẢO CHIỀU TỪ CHIẾN THUẬT
            should_close = False
            if action == "CLOSE": should_close = True
            elif p['type'] == "LONG" and action == "SELL": should_close = True
            elif p['type'] == "SHORT" and action == "BUY": should_close = True

            if should_close:
                self._close(price, time, reason="SIGNAL 🔔")

        # 3. MỞ LỆNH MỚI (Chỉ khi không còn vị thế)
        action = signal_data.get('action') if isinstance(signal_data, dict) else signal_data
        new_sl = signal_data.get('sl', 0) if isinstance(signal_data, dict) else 0
        new_tp = signal_data.get('tp', 0) if isinstance(signal_data, dict) else 0

        if self.position is None and action in ['BUY', 'SELL']:
            self._open(
                "LONG" if action == "BUY" else "SHORT", 
                price, time, new_sl, new_tp, 
                custom_margin=self.bet_amount # <--- DÙNG CẤU HÌNH RIÊNG
            )

    def _open(self, p_type, price, time, sl, tp, custom_margin=None):        
        required_margin = custom_margin if custom_margin else 100
        volume = (required_margin * self.leverage) / price

        if self.balance < required_margin:
            self.add_log(f"❌ Từ chối: Thiếu tiền ({required_margin}$)")
            return 

        self.position = {
            "type": p_type,
            "entry": price,
            "vol": volume,
            "margin": required_margin,
            "sl_price": sl,
            "tp_price": tp,
            "time": time
        }
        self._save_to_db()
        self.add_log(f"✅ OPEN {p_type} | Giá: {price:.2f} | Cược: {required_margin}$ (x{self.leverage})")

    def _close(self, price, time, reason="SIGNAL"):
        if not self.position: return

        p = self.position
        
        if p['type'] == "LONG":
            pnl = (price - p['entry']) * p['vol']
        else:
            pnl = (p['entry'] - price) * p['vol']
            
        self.balance += pnl
        
        # Log ra history
        self.history.append({
            "type": p['type'],
            "pnl": round(pnl, 2),
            "reason": reason,
            "exit_time": time,
            "balance_after": round(self.balance, 2)
        })
        self._save_to_db()
        self.add_log(f"Testing Log: {reason} | PnL: {pnl:.2f}$")
        self.position = None

    def get_equity(self, current_price):
        equity = self.balance
        pnl_float = 0
        margin_used = 0

        if self.position:
            entry = self.position['entry']
            if self.position['type'] == "LONG": 
                pnl_float = (current_price - entry) * self.position['vol']
            else: 
                pnl_float = (entry - current_price) * self.position['vol']
            
            equity += pnl_float
            margin_used = self.position['margin']

        return round(equity, 2), round(pnl_float, 2), round(margin_used, 2)


class PortfolioManager:
    """Quản lý chung tất cả các tài khoản chiến thuật"""
    def __init__(self, username):
        self.username = username
        self.global_capital = user_db.get_user_capital(username)
        self.accounts = {
            "RSI_Reversion": SubAccount(username, "RSI_Reversion", self.global_capital),
            "MA_Trend": SubAccount(username, "MA_Trend", self.global_capital),
            "MACD_Momentum": SubAccount(username, "MACD_Momentum", self.global_capital),
            "Manual_Trader": SubAccount(username, "Manual_Trader", self.global_capital)
        }

    def set_global_capital(self, capital):
        """Thiết lập vốn chung cho tất cả"""
        self.global_capital = capital
        user_db.update_user_capital(self.username, capital) # Lưu DB
        for acc in self.accounts.values():
            acc.reset_capital(capital)

    def set_strategy_config(self, name, leverage, bet_amount):
        """Thiết lập cấu hình riêng cho từng chiến thuật"""
        if name in self.accounts:
            self.accounts[name].update_config(leverage, bet_amount)

    def execute_all(self, signals_dict, price, time):
        for strategy_name, signal_data in signals_dict.items():
            if strategy_name in self.accounts:
                acc = self.accounts[strategy_name]
                
                # Log tín hiệu
                action = signal_data.get('action') if isinstance(signal_data, dict) else signal_data
                if action != "HOLD":
                     # Trích xuất thông tin
                    sl = signal_data.get('sl', 0) if isinstance(signal_data, dict) else 0
                    tp = signal_data.get('tp', 0) if isinstance(signal_data, dict) else 0
                    acc.add_log(f"Tín hiệu: {action} (SL:{sl} TP:{tp})")

                # Gọi xử lý (Không cần truyền bet_amount nữa vì nó tự có rồi)
                acc.process_signal(signal_data, price, time)

    def get_summary(self, current_price):
        summary = []
        best_pnl = -99999999
        best_strat = ""

        for name, acc in self.accounts.items():
            equity, _, margin = acc.get_equity(current_price)
            pnl_total = equity - acc.initial_balance
            
            entry_price = 0
            if acc.position:
                entry_price = acc.position['entry']

            if pnl_total > best_pnl:
                best_pnl = pnl_total
                best_strat = name

            summary.append({
                "name": name,
                "signal": "HOLD" if not acc.position else acc.position['type'],
                "entry_price": entry_price, 
                "equity": equity,
                "pnl_total": round(pnl_total, 2),
                "margin_used": margin,
                "logs": acc.logs,
                "leverage": acc.leverage,       # Gửi cấu hình hiện tại xuống Frontend
                "bet_amount": acc.bet_amount,   # Gửi cấu hình hiện tại xuống Frontend
                "is_best": False
            })

        for s in summary:
            if s["name"] == best_strat: s["is_best"] = True

        return summary