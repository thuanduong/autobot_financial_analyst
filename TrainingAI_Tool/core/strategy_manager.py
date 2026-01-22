# core/strategy_manager.py
from strategies.technical_v1 import TechnicalStrategyV1
from strategies.trend_ma import TrendFollowingStrategy
from strategies.momentum_macd import MACDStrategy

class StrategyManager:
    def __init__(self):
        self.strategies = {
            "RSI_Reversion": TechnicalStrategyV1(),
            "MA_Trend": TrendFollowingStrategy(),
            "MACD_Momentum": MACDStrategy()
        }

    def analyze_all(self, df_main, df_trend):
        results = {}
        signals = {}
        
        # Log hiển thị rõ đang dùng dữ liệu gì
        print(f"\n--- 🔍 MTF ANALYZE: Main({len(df_main)}) + Trend({len(df_trend)}) ---")
        
        for name, strat in self.strategies.items():
            # Truyền cả 2 DataFrame vào chiến thuật
            # Lưu ý: Các chiến thuật khác (MA, MACD) cũng cần sửa hàm analyze để nhận 2 tham số
            # hoặc dùng **kwargs để tránh lỗi.
            try:
                res = strat.analyze(df_main, df_trend) 
            except TypeError:
                # Fallback cho các chiến thuật cũ chưa nâng cấp
                res = strat.analyze(df_main) 

            results[name] = res
            
            # Gói tín hiệu gửi đi bao gồm cả SL/TP đã tính toán
            signals[name] = {
                "action": res.get('signal', 'HOLD'),
                "sl": res.get('sl_price', 0),
                "tp": res.get('tp_price', 0)
            }
            
            if res.get('signal') in ['BUY', 'SELL']:
                print(f"🔔 [{name}]: {res.get('signal')} | SL: {res.get('sl_price')} | TP: {res.get('tp_price')}")
                print(f"   ➤ Lý do: {res.get('reason')}")

        return results, signals