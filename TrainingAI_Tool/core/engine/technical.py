# core/engine/technical.py
import pandas as pd
import ta

class TechnicalAnalyzer:
    
    @staticmethod
    def get_trend(df):
        """Phân tích xu hướng vĩ mô (Macro) - Dùng cho H1, H4"""
        if df is None or len(df) < 50: return "NEUTRAL"
        
        close = df['close']
        
        # 1. EMA 200 (Đường xu hướng dài hạn)
        ema_200 = ta.trend.ema_indicator(close, window=200).iloc[-1]
        
        # 2. ADX (Độ mạnh xu hướng)
        adx = ta.trend.ADXIndicator(df['high'], df['low'], close, window=14)
        curr_adx = adx.adx().iloc[-1]
        
        current_price = close.iloc[-1]
        
        trend = "SIDEWAY"
        if curr_adx > 25: # Trend đang mạnh
            if current_price > ema_200: trend = "UPTREMD"
            else: trend = "DOWNTREND"
            
        return trend

    @staticmethod
    def analyze(df, macro_trend="NEUTRAL"):
        """Phân tích điểm vào lệnh (Micro) - Dùng cho M1, M5"""
        if df is None or len(df) < 50: return None

        close = df['close']
        high = df['high']
        low = df['low']

        # --- CHỈ BÁO ---
        # RSI
        curr_rsi = ta.momentum.rsi(close, window=14).iloc[-1]
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        bb_h = bb.bollinger_hband().iloc[-1]
        bb_l = bb.bollinger_lband().iloc[-1]
        
        # ATR (Để tính Target $)
        curr_atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]

        # MACD
        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        sig_val = macd.macd_signal().iloc[-1]

        # --- LOGIC TÍN HIỆU (Kết hợp Macro Trend) ---
        signal = "NEUTRAL"
        score = 50
        reason = []

        # Logic 1: RSI quá bán/mua (Reversal)
        if curr_rsi < 30 and close.iloc[-1] <= bb_l:
            # Chỉ Buy nếu Trend lớn là Tăng hoặc Sideway (Không bắt dao rơi khi Downtrend mạnh)
            if macro_trend != "DOWNTREND": 
                signal = "BUY"
                score += 30
                reason.append("RSI Oversold")
        
        elif curr_rsi > 70 and close.iloc[-1] >= bb_h:
            # Chỉ Sell nếu Trend lớn là Giảm hoặc Sideway
            if macro_trend != "UPTREND":
                signal = "SELL"
                score -= 30
                reason.append("RSI Overbought")

        # Logic 2: MACD Crossover (Follow Trend)
        if macd_val > sig_val and macro_trend == "UPTREMD":
            signal = "STRONG BUY"
            score += 20
            reason.append("MACD Cross + Trend Ủng hộ")
            
        if macd_val < sig_val and macro_trend == "DOWNTREND":
            signal = "STRONG SELL"
            score -= 20
            reason.append("MACD Cross + Trend Ủng hộ")

        # --- TÍNH TOÁN TARGET (SL/TP) ---
        # Quy ước: Entry là giá đóng cửa nến hiện tại
        entry = close.iloc[-1]
        sl = 0
        tp = 0
        
        # SL/TP dựa trên ATR (Dynamic)
        if "BUY" in signal:
            sl = entry - (curr_atr * 1.5)
            tp = entry + (curr_atr * 3.0) # R:R = 1:2
        elif "SELL" in signal:
            sl = entry + (curr_atr * 1.5)
            tp = entry - (curr_atr * 3.0)

        return {
            "rsi": round(curr_rsi, 2),
            "macd": round(macd_val, 5),
            "atr": round(curr_atr, 4),
            "signal": signal,
            "macro_trend": macro_trend, # Trả về trend khung lớn để hiển thị
            "score": min(100, max(0, score)),
            "suggested_sl": round(sl, 2),
            "suggested_tp": round(tp, 2),
            "reason": ", ".join(reason) if reason else "Chờ tín hiệu..."
        }