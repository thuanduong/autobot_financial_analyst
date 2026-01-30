# core/engine/technical.py
import pandas as pd
import ta

class TechnicalAnalyzer:
    @staticmethod
    def analyze(df):
        """
        Input: DataFrame (OHLCV)
        Output: Dict chứa các chỉ số và Recommendation
        """
        if df is None or len(df) < 50: return None

        close = df['close']
        high = df['high']
        low = df['low']

        # 1. RSI
        rsi = ta.momentum.rsi(close, window=14)
        curr_rsi = rsi.iloc[-1]

        # 2. Bollinger Bands (Để bắt đỉnh đáy)
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        bb_h = bb.bollinger_hband().iloc[-1]
        bb_l = bb.bollinger_lband().iloc[-1]

        # 3. MACD (Để xác định xu hướng)
        macd = ta.trend.MACD(close)
        macd_line = macd.macd().iloc[-1]
        signal_line = macd.macd_signal().iloc[-1]

        # 4. ATR (Để tính Stoploss/TakeProfit tối ưu)
        atr = ta.volatility.AverageTrueRange(high, low, close, window=14)
        curr_atr = atr.average_true_range().iloc[-1]

        # --- LOGIC DỰ ĐOÁN (RECOMMENDATION) ---
        signal = "NEUTRAL"
        score = 50
        reason = []

        # Logic RSI + Bollinger (Reversal)
        if curr_rsi < 30 and close.iloc[-1] <= bb_l:
            signal = "STRONG BUY"
            score = 90
            reason.append("Oversold + Chạm Band dưới")
        elif curr_rsi < 35:
            signal = "BUY"
            score = 75
            reason.append("RSI thấp")
        
        elif curr_rsi > 70 and close.iloc[-1] >= bb_h:
            signal = "STRONG SELL"
            score = 90
            reason.append("Overbought + Chạm Band trên")
        elif curr_rsi > 65:
            signal = "SELL"
            score = 75
            reason.append("RSI cao")

        # Logic MACD (Trend)
        if macd_line > signal_line: 
            score += 5 # Xu hướng tăng ủng hộ
        else:
            score -= 5

        return {
            "rsi": round(curr_rsi, 2),
            "macd": round(macd_line, 5),
            "atr": round(curr_atr, 4),
            "signal": signal,
            "score": min(100, max(0, score)), # Kẹp trong 0-100
            "reason": ", ".join(reason),
            "suggested_sl": round(curr_atr * 1.5, 4), # Gợi ý SL = 1.5 ATR
            "suggested_tp": round(curr_atr * 3.0, 4)  # Gợi ý TP = 3.0 ATR
        }