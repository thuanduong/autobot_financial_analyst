from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, DateTime, Enum, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from backend_cloud.app.database.base import Base

# --- ENUMS (Các hằng số trạng thái) ---
class OrderType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LIQUIDATED = "LIQUIDATED" # Cháy tài khoản

# --- BẢNG TRUNG GIAN (Many-to-Many) ---
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

# --- MODULE 1: AUTH & PHÂN QUYỀN ---

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # VD: "Admin", "Free", "Pro"
    
    # Quan hệ
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", back_populates="role")

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # VD: "trade", "view_vip_chart"
    
    # Quan hệ
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Foreign Key
    role_id = Column(Integer, ForeignKey("roles.id"))
    
    # Quan hệ
    role = relationship("Role", back_populates="users")
    wallet = relationship("VirtualWallet", back_populates="user", uselist=False) # 1-1
    orders = relationship("Order", back_populates="user")
    symbols = relationship("SymbolConfig", back_populates="user")

# --- MODULE 2: PAPER TRADING ENGINE ---

class VirtualWallet(Base):
    __tablename__ = "virtual_wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Numeric(precision, scale): Ví dụ lưu tới 10 tỷ đô, 2 số thập phân
    balance = Column(Numeric(15, 2), default=10000.00) # Số dư thực tế
    equity = Column(Numeric(15, 2), default=10000.00)  # Số dư + Lãi/Lỗ tạm tính
    
    # Quan hệ
    user = relationship("User", back_populates="wallet")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    symbol = Column(String, index=True, nullable=False) # VD: XAUUSD.sml
    order_type = Column(Enum(OrderType), nullable=False)
    volume = Column(Numeric(10, 2), nullable=False)     # Số Lot (VD: 0.1)
    
    open_price = Column(Numeric(15, 5), nullable=False) # Giá mở
    close_price = Column(Numeric(15, 5), nullable=True) # Giá đóng (Null nếu lệnh đang mở)
    
    status = Column(Enum(OrderStatus), default=OrderStatus.OPEN)
    
    open_time = Column(DateTime, default=datetime.now(timezone.utc))
    close_time = Column(DateTime, nullable=True)
    
    profit_loss = Column(Numeric(15, 2), default=0.00)  # Tiền lãi/lỗ (USD)
    
    # Quan hệ
    user = relationship("User", back_populates="orders")

class UserOrder(Base):
    __tablename__ = "user_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)      # KHÓA PHÂN BIỆT: User A, User B...
    mt5_ticket = Column(Integer, index=True)   # Mã ticket trả về từ MT5 để đối chiếu
    
    symbol = Column(String, index=True, nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)                # "BUY" hoặc "SELL"
    volume = Column(Numeric(10, 2), nullable=False)
    
    open_price = Column(Numeric(15, 5), nullable=False) 
    open_time = Column(DateTime, default=datetime.now(timezone.utc))
    
    # KHI ĐÓNG LỆNH MỚI ĐIỀN CÁC TRƯỜNG NÀY
    close_price = Column(Numeric(15, 5), nullable=True)
    close_time = Column(DateTime, nullable=True)
    profit_loss = Column(Numeric(15, 2), default=0.00)         
    status = Column(Enum(OrderStatus), default=OrderStatus.OPEN)    # "OPEN" hoặc "CLOSED"

class UserAlert(Base):
    __tablename__ = "user_alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    symbol = Column(String, index=True, nullable=False) # Mã giao dịch, ví dụ: XAUUSD.sml
    indicator = Column(String, nullable=False)          # Tên chỉ báo: PRICE, RSI, MACD
    condition = Column(String, nullable=False)          # Điều kiện: GREATER_THAN, LESS_THAN
    value = Column(Numeric(15, 5), nullable=False)      # Mốc giá trị: 2050.5 hoặc 30.0
    is_active = Column(Boolean, default=True)           # Bật/Tắt báo thức
    
    user = relationship("User", backref="alerts")

class SymbolConfig(Base):
    __tablename__ = "symbols_config"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Nên để nullable=False

    # Đã bỏ unique=True ở đây
    symbol = Column(String, index=True, nullable=False) 
    contract_size = Column(Numeric(10, 2), nullable=False)          
    base_leverage = Column(Integer, default=500)                    
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="symbols")

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uix_user_symbol'),
    )