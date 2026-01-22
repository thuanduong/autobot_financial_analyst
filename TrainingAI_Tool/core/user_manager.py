# core/user_manager.py
import sqlite3
import os
import json

class UserManager:
    def __init__(self, db_path="database/users.db"):
        # Tạo thư mục database nếu chưa có
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        conn = self._get_conn()
        cur = conn.cursor()
        
        # 1. Bảng Users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT, -- Lưu plaintext cho demo (Thực tế nên hash)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Bảng Portfolio State (Lưu trạng thái từng chiến thuật của từng user)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                username TEXT,
                strategy TEXT,
                balance REAL,
                leverage REAL,
                bet_amount REAL,
                history TEXT, -- Lưu JSON lịch sử lệnh
                PRIMARY KEY (username, strategy)
            )
        """)
        
        # 3. Bảng Global Config (Lưu Vốn chung của User)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_globals (
                username TEXT PRIMARY KEY,
                global_capital REAL DEFAULT 10000
            )
        """)

        conn.commit()
        conn.close()

    # --- USER AUTH ---
    def login(self, username, password):
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return row[0] == password # Trả về True nếu pass đúng
        else:
            # Nếu user chưa tồn tại -> Tự động đăng ký luôn (Cho tiện demo)
            self.register(username, password)
            return True

    def register(self, username, password):
        conn = self._get_conn()
        result = False
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.execute("INSERT INTO user_globals (username, global_capital) VALUES (?, ?)", (username, 10000))
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            pass # Đã tồn tại
        finally:
            conn.close()
        return result

    # --- PORTFOLIO DATA ---
    def get_user_capital(self, username):
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT global_capital FROM user_globals WHERE username=?", (username,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 10000

    def update_user_capital(self, username, capital):
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO user_globals (username, global_capital) VALUES (?, ?)", (username, capital))
        conn.commit()
        conn.close()

    def load_strategy_state(self, username, strategy_name):
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT balance, leverage, bet_amount, history FROM portfolios WHERE username=? AND strategy=?", (username, strategy_name))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                "balance": row[0],
                "leverage": row[1],
                "bet_amount": row[2],
                "history": json.loads(row[3]) if row[3] else []
            }
        return None # Chưa có dữ liệu

    def save_strategy_state(self, username, strategy_name, balance, leverage, bet_amount, history):
        conn = self._get_conn()
        hist_json = json.dumps(history)
        conn.execute("""
            INSERT OR REPLACE INTO portfolios (username, strategy, balance, leverage, bet_amount, history)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, strategy_name, balance, leverage, bet_amount, hist_json))
        conn.commit()
        conn.close()

    def reset_user_data(self, username):
        """Xóa sạch dữ liệu của user để chơi lại từ đầu"""
        conn = self._get_conn()
        # Reset vốn chung
        conn.execute("INSERT OR REPLACE INTO user_globals (username, global_capital) VALUES (?, 10000)", (username,))
        # Xóa portfolio
        conn.execute("DELETE FROM portfolios WHERE username=?", (username,))
        conn.commit()
        conn.close()