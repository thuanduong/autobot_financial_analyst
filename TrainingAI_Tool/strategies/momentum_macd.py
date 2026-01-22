from .base_strategy import BaseStrategy
import ta

class MACDStrategy(BaseStrategy):
    def analyze(self, df):
        if df.empty: return {}
        df = df.copy()
        
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['Signal'] = macd.macd_signal()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = "HOLD"
        reason = "Histogram chưa đảo chiều..."
        
        # Cắt lên
        if prev['MACD'] < prev['Signal'] and last['MACD'] > last['Signal']:
            signal = "BUY"
            reason = "Động lượng Tăng: MACD cắt lên đường Signal"
        
        # Cắt xuống
        elif prev['MACD'] > prev['Signal'] and last['MACD'] < last['Signal']:
            signal = "SELL"
            reason = "Động lượng Giảm: MACD cắt xuống đường Signal"
            
        trend_str = "MẠNH" if last['MACD'] > 0 else "YẾU"

        return {
            "signal": signal,
            "trend": trend_str,
            "price": last['close'],
            "reason": reason,
            "candle_count": len(df)
        }