import pandas as pd
import ta
from backend_cloud.app.database.analyze_repo import AnalyzeRepo
from backend_cloud.app.database.analyze_models import StrategyConfig
from backend_cloud.app.engine.strategies.trend_momentum import TrendMomentumStrategy
from backend_cloud.app.engine.strategies.volatility_breakout import VolatilityBreakoutStrategy
from backend_cloud.app.engine.strategies.price_action import PriceActionPinbarStrategy
from backend_cloud.app.engine.strategies.vwap_reversion import VWAPReversionStrategy
from backend_cloud.app.engine.strategies.mtf_confluence import MTFConfluenceStrategy

class TechnicalManager:
    def __init__(self):
        self.active_strategies = {}
        self.repo: AnalyzeRepo = None
    
    def init(self, repo: AnalyzeRepo):
        self.repo = repo
        self.reload_configs_from_db()

    def reload_configs_from_db(self):
        if not self.repo: return
        db = self.repo.AnalyzeSessionLocal()
        try:
            # Chỉ lấy những chiến thuật đang được bật (is_active = True)
            active_configs = db.query(StrategyConfig).filter(StrategyConfig.is_active == True).all()
            self.active_strategies.clear()
            
            for config_record in active_configs:
                if config_record.strategy_id == "TREND_MOMENTUM_V1":
                    # Truyền JSON parameters vào để khởi tạo Class
                    self.active_strategies[config_record.strategy_id] = TrendMomentumStrategy(
                        config=config_record.parameters 
                    )
                elif config_record.strategy_id == "VOLATILITY_BREAKOUT_V1":
                    self.active_strategies[config_record.strategy_id] = VolatilityBreakoutStrategy(
                        config=config_record.parameters
                    )
                elif config_record.strategy_id == "PRICE_ACTION_V1":
                    self.active_strategies[config_record.strategy_id] = PriceActionPinbarStrategy(
                        config=config_record.parameters
                    )
                elif config_record.strategy_id == "VWAP_REVERSION_V1":
                    self.active_strategies[config_record.strategy_id] = VWAPReversionStrategy(
                        config=config_record.parameters
                    )
                elif config_record.strategy_id == "MTF_CONFLUENCE_V1":
                    self.active_strategies[config_record.strategy_id] = MTFConfluenceStrategy(
                        config=config_record.parameters
                    )
                
            print(f"🔄 Đã nạp thành công {len(self.active_strategies)} chiến thuật từ Database.")
        finally:
            db.close()

    def get_trend(self, df: pd.DataFrame) -> str:
        """La bàn vĩ mô dùng chung cho toàn hệ thống"""
        if df is None or len(df) < 50: return "NEUTRAL"
        
        close = df['close']
        ema_200 = ta.trend.ema_indicator(close, window=200).iloc[-1]
        
        adx = ta.trend.ADXIndicator(df['high'], df['low'], close, window=14)
        curr_adx = adx.adx().iloc[-1]
        
        current_price = close.iloc[-1]
        trend = "SIDEWAY"
        
        if curr_adx > 25: 
            if current_price > ema_200: trend = "UPTREND" 
            else: trend = "DOWNTREND"
            
        return trend

    def evaluate_live(self, df: pd.DataFrame, macro_trend: str = "NEUTRAL") -> list:
        """Đánh giá nến hiện tại qua TẤT CẢ chiến thuật (Dùng cho Radar & Bot Live)"""
        results = []
        
        for name, strategy in self.active_strategies.items():
            try:
                res = strategy.analyze(df, macro_trend)
                if res:
                    res['strategy_name'] = strategy.name 
                    results.append(res)
            except Exception as e:
                print(f"Lỗi ở chiến thuật {name}: {e}")

        return results

    def run_backtest(self, df: pd.DataFrame, strategy_name: str = "LEGACY_V1") -> list:
        """Trả về markers cho Frontend (Dùng cho API Chart)"""
        if strategy_name in self.active_strategies:
            return self.active_strategies[strategy_name].analyze_history(df)
        return []

tech_engine = TechnicalManager()