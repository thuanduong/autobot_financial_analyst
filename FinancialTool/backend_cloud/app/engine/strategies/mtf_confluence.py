import pandas as pd
import numpy as np
import ta
from .base_strategy import BaseStrategy

class MTFConfluenceStrategy(BaseStrategy):
    def __init__(self, config=None):
        super().__init__(name="MTF_CONFLUENCE_V1", config=config)
        # EMA để xác định xu hướng trung hạn tại khung hiện tại
        self.ema_medium_period = self.config.get("ema_medium", 50)
        # RSI để tìm điểm kiệt sức (Oversold/Overbought)
        self.rsi_period = self.config.get("rsi_period", 14)
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)
        # ATR để đặt SL/TP động theo biến động thị trường
        self.atr_period = self.config.get("atr_period", 14)
        self.risk_reward = self.config.get("risk_reward", 2.0)

    def analyze(self, df: pd.DataFrame, macro_trend: str = "NEUTRAL") -> dict:
        """
        Chiến thuật hợp lưu:
        1. Macro Trend (từ khung cao hơn, do Scanner cung cấp)
        2. Medium Trend (EMA trên khung hiện tại)
        3. Micro Entry (RSI trên khung hiện tại)
        """
        if df is None or len(df) < max(self.ema_medium_period, self.rsi_period, self.atr_period) + 5:
            return None

        # 1. Tính toán chỉ báo sử dụng thư viện 'ta' (Vectorized)
        close_ser = df['close']
        ema_medium = ta.trend.ema_indicator(close_ser, window=self.ema_medium_period)
        rsi = ta.momentum.rsi(close_ser, window=self.rsi_period)
        atr = ta.volatility.average_true_range(df['high'], df['low'], close_ser, window=self.atr_period)

        curr_close = close_ser.iloc[-1]
        curr_ema = ema_medium.iloc[-1]
        curr_rsi = rsi.iloc[-1]
        curr_atr = atr.iloc[-1]
        
        # 2. Điều kiện hợp lưu trung hạn
        medium_uptrend = curr_close > curr_ema
        medium_downtrend = curr_close < curr_ema
        
        # 3. Điều kiện kích nổ (Micro)
        micro_oversold = curr_rsi < self.rsi_oversold
        micro_overbought = curr_rsi > self.rsi_overbought

        signal = "NEUTRAL"
        score = 0
        reason = []
        sl, tp = 0.0, 0.0

        # 🟢 LỆNH BUY: Macro Tăng + Giá trên EMA + RSI Quá bán
        if macro_trend == "UPTREND" and medium_uptrend and micro_oversold:
            signal = "BUY"
            score = 95
            reason.append(f"Hợp lưu ĐA KHUNG (TĂNG): Macro Consensus, Price > EMA{self.ema_medium_period}, RSI OS ({curr_rsi:.1f})")
            # SL động: Entry - 2 lần ATR
            sl = curr_close - (curr_atr * 2.0)
            tp = curr_close + (curr_close - sl) * self.risk_reward

        # 🔴 LỆNH SELL: Macro Giảm + Giá dưới EMA + RSI Quá mua
        elif macro_trend == "DOWNTREND" and medium_downtrend and micro_overbought:
            signal = "SELL"
            score = 95
            reason.append(f"Hợp lưu ĐA KHUNG (GIẢM): Macro Consensus, Price < EMA{self.ema_medium_period}, RSI OB ({curr_rsi:.1f})")
            sl = curr_close + (curr_atr * 2.0)
            tp = curr_close - (sl - curr_close) * self.risk_reward

        if signal == "NEUTRAL": return None

        return {
            "strategy": self.name,
            "signal": signal,
            "score": min(100, score),
            "reason": ", ".join(reason),
            "suggested_sl": round(sl, 2) if sl else None,
            "suggested_tp": round(tp, 2) if tp else None,
            "macro_trend": macro_trend
        }

    def analyze_history(self, df: pd.DataFrame) -> list:
        if df is None or len(df) < 200: return []
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        times = df['time'].values

        # Tính toán toàn bộ Series để dùng trong vòng lặp (Performance optimization)
        ema = ta.trend.ema_indicator(df['close'], window=self.ema_medium_period).values
        rsi = ta.momentum.rsi(df['close'], window=self.rsi_period).values
        atr = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=self.atr_period).values
        ema_macro = ta.trend.ema_indicator(df['close'], window=200).values # Giả lập Macro trend bằng EMA200

        markers = []
        for i in range(200, len(df) - 5):
            if np.isnan(ema[i]) or np.isnan(rsi[i]) or np.isnan(ema_macro[i]): continue

            macro_up = close[i] > ema_macro[i]
            is_buy = macro_up and (close[i] > ema[i]) and (rsi[i] < self.rsi_oversold)
            is_sell = (not macro_up) and (close[i] < ema[i]) and (rsi[i] > self.rsi_overbought)
            
            sig = "BUY" if is_buy else ("SELL" if is_sell else None)
            if not sig: continue

            # Logic kiểm tra WIN/LOSS trong lịch sử
            sl = close[i] - (atr[i] * 2.0) if sig == "BUY" else close[i] + (atr[i] * 2.0)
            tp = close[i] + (close[i] - sl) * self.risk_reward if sig == "BUY" else close[i] - (sl - close[i]) * self.risk_reward
            
            outcome = "RUNNING"
            for j in range(1, 50):
                if i + j >= len(df): break
                if sig == "BUY":
                    if low[i + j] <= sl: outcome = "LOSS"; break
                    if high[i + j] >= tp: outcome = "WIN"; break
                else:
                    if high[i + j] >= sl: outcome = "LOSS"; break
                    if low[i + j] <= tp: outcome = "WIN"; break

            ts = times[i]
            if hasattr(ts, 'timestamp'): ts = int(ts.timestamp())
            
            markers.append({
                "time": ts,
                "position": "belowBar" if sig == "BUY" else "aboveBar",
                "shape": "arrowUp" if sig == "BUY" else "arrowDown",
                "result": outcome,
                "strategy_id": self.name
            })

        return markers