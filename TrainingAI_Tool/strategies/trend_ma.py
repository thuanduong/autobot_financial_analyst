from .base_strategy import BaseStrategy
import ta

class TrendFollowingStrategy(BaseStrategy):
    def analyze(self, df):
        if df.empty: return {}
        df = df.copy()
        
        # Tính chỉ báo
        df['EMA_Fast'] = ta.trend.ema_indicator(df['close'], window=50)
        df['EMA_Slow'] = ta.trend.ema_indicator(df['close'], window=200)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = "HOLD"
        reason = "Chờ tín hiệu giao cắt..."
        
        # Golden Cross (Cắt lên)
        if prev['EMA_Fast'] < prev['EMA_Slow'] and last['EMA_Fast'] > last['EMA_Slow']:
            signal = "BUY"
            reason = "Golden Cross: EMA 50 cắt LÊN trên EMA 200 (Bắt đầu xu hướng Tăng)"
            
        # Death Cross (Cắt xuống)
        elif prev['EMA_Fast'] > prev['EMA_Slow'] and last['EMA_Fast'] < last['EMA_Slow']:
            signal = "SELL"
            reason = "Death Cross: EMA 50 cắt XUỐNG dưới EMA 200 (Bắt đầu xu hướng Giảm)"

        # Xác định Trend hiện tại
        trend_str = "TĂNG" if last['EMA_Fast'] > last['EMA_Slow'] else "GIẢM"

        return {
            "signal": signal,
            "trend": trend_str,
            "price": last['close'],
            "reason": reason,
            "candle_count": len(df)
        }