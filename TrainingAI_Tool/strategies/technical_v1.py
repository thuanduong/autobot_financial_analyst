# strategies/technical_v1.py
from .base_strategy import BaseStrategy
import ta
import pandas as pd

class TechnicalStrategyV1(BaseStrategy):
    def analyze(self, df_main, df_trend):
        """
        df_main: Dữ liệu khung nhỏ (để tìm điểm vào lệnh)
        df_trend: Dữ liệu khung lớn (để lọc xu hướng)
        """
        if df_main.empty or df_trend.empty: return {}
        
        df = df_main.copy()
        df_t = df_trend.copy()
        
        # 1. PHÂN TÍCH KHUNG LỚN (TREND FILTER)
        # Tính EMA 200 trên khung H4q
        df_t['EMA_200'] = ta.trend.ema_indicator(df_t['close'], window=200, fillna=True)
        last_trend = df_t.iloc[-1]
        
        # Xác định xu hướng chủ đạo
        major_trend = "SIDEWAY"
        if last_trend['close'] > last_trend['EMA_200']: major_trend = "UP"
        elif last_trend['close'] < last_trend['EMA_200']: major_trend = "DOWN"

        # 2. PHÂN TÍCH KHUNG NHỎ (ENTRY SIGNAL)
        # Tính RSI & Bollinger Bands
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BB_Low'] = bb.bollinger_lband()
        df['BB_High'] = bb.bollinger_hband()
        
        # --- [QUAN TRỌNG] TÍNH ATR ĐỂ SET SL/TP ĐỘNG ---
        # ATR đo lường "độ rung lắc" trung bình của nến
        df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        
        last = df.iloc[-1]
        atr_value = last['ATR']
        
        # 3. LOGIC KẾT HỢP (CONFLUENCE)
        signal = "HOLD"
        reason = f"Trend H4 đang {major_trend}. Chờ điểm vào..."
        sl_price = 0
        tp_price = 0
        
        # --- KỊCH BẢN LONG ---
        # Chỉ Long khi Trend H4 là UP (Bơi thuận dòng)
        if major_trend == "UP":
            if last['close'] <= last['BB_Low'] and last['RSI'] < 30:
                signal = "BUY"
                # Dynamic SL/TP:
                # SL cách giá vào 2 lần ATR (Đủ rộng để không bị quét Stop Hunt)
                sl_price = last['close'] - (2.0 * atr_value)
                # TP gấp 2 lần rủi ro (Risk:Reward = 1:2)
                tp_price = last['close'] + (4.0 * atr_value)
                
                reason = f"Trend H4 Tăng + M15 Quá bán. ATR={atr_value:.2f}"

        # --- KỊCH BẢN SHORT ---
        # Chỉ Short khi Trend H4 là DOWN
        elif major_trend == "DOWN":
            if last['close'] >= last['BB_High'] and last['RSI'] > 70:
                signal = "SELL"
                sl_price = last['close'] + (2.0 * atr_value)
                tp_price = last['close'] - (4.0 * atr_value)
                
                reason = f"Trend H4 Giảm + M15 Quá mua. ATR={atr_value:.2f}"
        
        # Nếu ngược trend -> Bỏ qua
        elif (major_trend == "UP" and last['RSI'] > 70) or (major_trend == "DOWN" and last['RSI'] < 30):
             reason = f"Bỏ qua tín hiệu vì ngược Trend H4 ({major_trend})"

        return {
            "signal": signal,
            "trend": major_trend, # Trả về Trend khung lớn
            "entry_price": last['close'],
            "sl_price": round(sl_price, 2), # Giá cắt lỗ cụ thể
            "tp_price": round(tp_price, 2), # Giá chốt lời cụ thể
            "atr": round(atr_value, 2),
            "reason": reason,
            "candle_count": len(df)
        }