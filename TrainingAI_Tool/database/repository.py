import sqlite3
import os
from config.settings import DB_PATH

class TradeRepo:
    def __init__(self):
        os.makedirs("database", exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        
        # 1. Bảng Users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                balance REAL DEFAULT 1000,
                risk_pct REAL DEFAULT 0.01,
                is_auto BOOLEAN DEFAULT 0
            )
        """)
        
        # 2. Bảng Orders (CẬP NHẬT ĐẦY ĐỦ CỘT)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                symbol TEXT,
                type TEXT,
                entry_price REAL,
                volume REAL,
                status TEXT,        -- OPEN / CLOSED
                
                -- CÁC CỘT MỚI QUAN TRỌNG --
                pnl REAL DEFAULT 0,
                exit_price REAL DEFAULT 0, 
                close_time TEXT,
                ----------------------------
                
                open_time TEXT
            )
        """)
        self.conn.commit()
        
        # Tạo bot mặc định
        self.create_user("system_bot", 10000, 0.01, 1)

    def create_user(self, username, balance=1000, risk=0.01, auto=0):
        try:
            self.conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", 
                             (username, balance, risk, auto))
            self.conn.commit()
        except: pass

    def get_user(self, username):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        return cur.fetchone()

    def get_all_users(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users")
        return cur.fetchall()

    def create_order(self, data):
        with self.conn:
            self.conn.execute("""
                INSERT INTO orders (username, symbol, type, entry_price, volume, status, open_time)
                VALUES (?, ?, ?, ?, ?, 'OPEN', ?)
            """, (data['username'], data['symbol'], data['type'], data['entry'], data['vol'], data['time']))

    def close_order(self, username, symbol, exit_price, pnl, time):
        # Đóng lệnh OPEN mới nhất
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM orders WHERE username=? AND symbol=? AND status='OPEN' ORDER BY id DESC LIMIT 1", (username, symbol))
        row = cur.fetchone()
        if row:
            with self.conn:
                self.conn.execute("UPDATE orders SET status='CLOSED', pnl=?, close_time=? WHERE id=?", (pnl, time, row['id']))
                # Cộng tiền vào user
                self.conn.execute("UPDATE users SET balance = balance + ? WHERE username=?", (pnl, username))

    def get_user_orders(self, username):
        """Lấy danh sách lệnh của user, sắp xếp mới nhất lên đầu"""
        self.conn.row_factory = sqlite3.Row # Quan trọng: Trả về dạng Dict
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM orders 
            WHERE username = ? 
            ORDER BY id DESC
        """, (username,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    
    def get_open_order(self, username, symbol):
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM orders 
            WHERE username=? AND symbol=? AND status='OPEN'
            ORDER BY id DESC LIMIT 1
        """, (username, symbol))
        return cur.fetchone()
    
    def get_order_by_id(self, order_id):
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close_order_by_id(self, order_id, exit_price, pnl):
        from datetime import datetime
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # BƯỚC 1: Đọc thông tin username trước (Read Operation)
            cur = self.conn.cursor()
            cur.execute("SELECT username FROM orders WHERE id=?", (order_id,))
            row = cur.fetchone()
            
            if not row:
                print(f"❌ DB Error: Không tìm thấy lệnh ID {order_id}")
                return False

            # Lấy username an toàn
            username = row[0] if row else "system_bot"

            # BƯỚC 2: Thực hiện Update (Write Operation)
            # Dùng execute trực tiếp và commit ngay lập tức
            
            # 2.1 Update trạng thái lệnh
            self.conn.execute("""
                UPDATE orders 
                SET status='CLOSED', exit_price=?, pnl=?, close_time=? 
                WHERE id=?
            """, (float(exit_price), float(pnl), time_now, order_id))
            
            # 2.2 Cộng tiền user
            self.conn.execute("""
                UPDATE users 
                SET balance = balance + ? 
                WHERE username=?
            """, (float(pnl), username))
            
            # 2.3 CHỐT SỔ (Quan trọng nhất)
            self.conn.commit()
            
            print(f"✅ DB: Đã đóng lệnh #{order_id} cho {username}. PnL: {pnl}")
            return True
            
        except Exception as e:
            self.conn.rollback() # Hoàn tác nếu lỗi
            print(f"❌ Lỗi Fatal DB (Close): {e}")
            raise e

    def get_user_equity_stats(self, username):
        """Tính toán Balance, Equity và Floating PnL"""
        user = self.get_user(username)
        if not user: return None
        
        user = dict(user)
        balance = user['balance']
        
        # Lấy tất cả lệnh OPEN
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM orders WHERE username=? AND status='OPEN'", (username,))
        open_orders = [dict(row) for row in cur.fetchall()]
        
        floating_pnl = 0
        # Lưu ý: Ở đây ta không có giá Realtime của từng mã để tính chính xác
        # Ta tạm thời trả về PnL = 0 hoặc phải truyền giá vào.
        # Để đơn giản cho API Dashboard, ta chỉ trả về Balance trước.
        # Frontend sẽ phải tự tính PnL nếu muốn realtime, hoặc API phải gọi MT5.
        
        return {
            "balance": balance,
            "equity": balance + floating_pnl, # Tạm tính
            "open_orders_count": len(open_orders)
        }