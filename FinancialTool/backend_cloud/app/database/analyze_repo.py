# database/analyze_repo.py
import os
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend_cloud.config.settings import ANALYZE_DB_PATH
from backend_cloud.app.database.analyze_models import AnalyzeBase, StrategyConfig

ANALYZE_DATABASE_URL = f"sqlite:///{ANALYZE_DB_PATH}"


class AnalyzeRepo:
    def __init__(self, db_path=ANALYZE_DATABASE_URL):
        os.makedirs("database", exist_ok=True)
        self.db_path = db_path
        self.analyze_engine = create_engine(
            ANALYZE_DATABASE_URL, 
            connect_args={"check_same_thread": False} # Cần thiết cho SQLite trong FastAPI
        )            
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.analyze_engine)
        self.init_analyze_db()

    def get_analyze_db(self):
        """Dependency injection để dùng trong các API Routes của FastAPI"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def AnalyzeSessionLocal(self):
        return self.SessionLocal()

    def init_analyze_db(self):
        AnalyzeBase.metadata.create_all(bind=self.analyze_engine)
        
        db = self.SessionLocal()
        try:
            # Kiểm tra xem đã có chiến thuật nào trong DB chưa
            existing = db.query(StrategyConfig).filter(StrategyConfig.strategy_id == "TREND_MOMENTUM_V1").first()
            if not existing:
                # Seed data: Đưa cấu hình chuẩn của bạn vào DB
                default_strategy = StrategyConfig(
                    strategy_id="TREND_MOMENTUM_V1",
                    name="Trend & Momentum V1",
                    description="Kết hợp EMA200, MACD theo xu hướng và RSI, Bollinger Bands bắt đảo chiều.",
                    is_active=True,
                    parameters={
                        "rsi_window": 14,
                        "rsi_oversold": 30,
                        "rsi_overbought": 70,
                        "macd_fast": 12,
                        "macd_slow": 26,
                        "macd_signal": 9,
                        "atr_window": 14,
                        "sl_atr_multiplier": 1.5,
                        "tp_atr_multiplier": 3.0
                    }
                )
                db.add(default_strategy)
                db.commit()
                print("✅ Đã khởi tạo Database Phân tích (analyze.db) và cấu hình TREND_MOMENTUM_V1.")
            
            # Seed data: Volatility Breakout
            existing_vol = db.query(StrategyConfig).filter(StrategyConfig.strategy_id == "VOLATILITY_BREAKOUT_V1").first()
            if not existing_vol:
                vol_strategy = StrategyConfig(
                    strategy_id="VOLATILITY_BREAKOUT_V1",
                    name="Volatility Breakout",
                    description="Chiến thuật đánh theo đà phá vỡ Bollinger Bands kết hợp Volume đột biến.",
                    is_active=True,
                    parameters={"period": 20, "std_dev": 2.0, "volume_ma_period": 20}
                )
                db.add(vol_strategy)
                db.commit()
                print("✅ Đã khởi tạo cấu hình VOLATILITY_BREAKOUT_V1.")
            
            # Seed data: Price Action
            existing_pa = db.query(StrategyConfig).filter(StrategyConfig.strategy_id == "PRICE_ACTION_V1").first()
            if not existing_pa:
                pa_strategy = StrategyConfig(
                    strategy_id="PRICE_ACTION_V1",
                    name="Price Action Support/Resistance",
                    description="Tìm kiếm Pin Bar và Engulfing tại các vùng hỗ trợ/kháng cự quan trọng.",
                    is_active=True,
                    parameters={"lookback": 20, "zone_tolerance": 0.15}
                )
                db.add(pa_strategy)
                db.commit()
                print("✅ Đã khởi tạo cấu hình PRICE_ACTION_V1.")

            # Seed data: VWAP Reversion (NEW)
            existing_vwap = db.query(StrategyConfig).filter(StrategyConfig.strategy_id == "VWAP_REVERSION_V1").first()
            if not existing_vwap:
                vwap_strategy = StrategyConfig(
                    strategy_id="VWAP_REVERSION_V1",
                    name="VWAP Mean Reversion",
                    description="Bắt đỉnh đáy khi giá lệch quá xa đường giá bình quân gia quyền khối lượng (VWAP).",
                    is_active=True,
                    parameters={"period": 100, "std_dev_multiplier": 2.5}
                )
                db.add(vwap_strategy)
                db.commit()
                print("✅ Đã khởi tạo cấu hình VWAP_REVERSION_V1.")

            # Seed data: MTF Confluence
            existing_mtf = db.query(StrategyConfig).filter(StrategyConfig.strategy_id == "MTF_CONFLUENCE_V1").first()
            if not existing_mtf:
                mtf_strategy = StrategyConfig(
                    strategy_id="MTF_CONFLUENCE_V1",
                    name="MTF Confluence (H4-H1-M15)",
                    description="Chiến thuật hợp lưu đa khung: Macro Trend, Medium EMA và Micro RSI Oversold/Overbought.",
                    is_active=True,
                    parameters={"ema_medium": 50, "rsi_period": 14, "rsi_overbought": 70, "rsi_oversold": 30}
                )
                db.add(mtf_strategy)
                db.commit()
                print("✅ Đã khởi tạo cấu hình MTF_CONFLUENCE_V1.")
        finally:
            db.close()