# database/analyze_models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Tạo Base riêng cho Database Phân tích (analyze_data)
AnalyzeBase = declarative_base()

class StrategyConfig(AnalyzeBase):
    """
    Bảng lưu trữ bộ thông số (Parameters) của các chiến thuật.
    Manager sẽ đọc bảng này mỗi giờ để cập nhật luật chơi.
    """
    __tablename__ = "strategy_configs"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, unique=True, index=True, nullable=False) # VD: TREND_MOMENTUM_V1
    name = Column(String, nullable=False)                                 # Tên hiển thị: "Trend & Momentum V1"
    description = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Lưu mọi cấu hình linh hoạt vào đây. VD: {"rsi_window": 14, "rsi_oversold": 30, "atr_multi": 2.5}
    parameters = Column(JSON, nullable=False, default={})
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SignalHistory(AnalyzeBase):
    """
    Bảng lưu trữ mọi tín hiệu BUY/SELL/NEUTRAL được sinh ra từ các chiến thuật.
    Frontend sẽ query bảng này để vẽ mũi tên lên Chart.
    """
    __tablename__ = "signal_history"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, index=True, nullable=False) # Liên kết mềm tới StrategyConfig
    symbol = Column(String, index=True, nullable=False)      # VD: XAUUSD.sml
    timeframe = Column(String, index=True, nullable=False)   # VD: M5, H1
    
    # Cực kỳ quan trọng: Index timestamp để query vẽ Chart siêu tốc
    timestamp = Column(Integer, index=True, nullable=False)  
    
    # --- PHẦN CORE (CHUẨN HÓA BẮT BUỘC) ---
    timestamp = Column(Integer)              # Thời gian bóp cò (Unix)
    signal = Column(String)                  # "BUY" hoặc "SELL"
    score = Column(Float)
    entry_price = Column(Float)
    suggested_sl = Column(Float)             # Mức giá Cắt lỗ
    suggested_tp = Column(Float)             # Mức giá Chốt lời
    reason = Column(String)                                  # Lý do ngắn gọn
    # --- PHẦN METADATA (TỰ DO) ---
    # Lưu các chỉ báo thô của từng chiến thuật. VD: {"rsi": 28.5, "macd": 0.05}
    metadata_details = Column(JSON, default={})
    
   # THÔNG TIN ĐÓNG LỆNH (CLOSE TRADE) - CÁC TRƯỜNG MỚI CHÍNH
    outcome = Column(String, default="PENDING") # "PENDING", "WIN", "LOSS", "CANCELLED"
    close_price = Column(Float, nullable=True)  # Giá lúc chốt lệnh
    close_time = Column(Integer, nullable=True) # Thời gian chốt lệnh
    realized_pnl = Column(Float, nullable=True) # Số point/pip lời lỗ thực tế

    # Tạo Composite Index để tối ưu hóa việc lấy dữ liệu vẽ Chart cho một mã cụ thể
    __table_args__ = (
        Index('ix_signal_chart_query', 'symbol', 'timeframe', 'timestamp'),
    )