import pandas as pd
import ta
from .base_strategy import BaseStrategy

class TrendMomentumStrategy(BaseStrategy):
    def __init__(self, config=None):
        # Đặt tên cho chiến thuật cũ của bạn
        super().__init__(name="TREND_MOMENTUM_V1", config=config)
        self.rsi_window = self.config.get("rsi_window", 14)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.sl_multiplier = self.config.get("sl_atr_multiplier", 1.5)
        self.tp_multiplier = self.config.get("tp_atr_multiplier", 3.0)


    def analyze(self, df: pd.DataFrame, macro_trend: str = "NEUTRAL") -> dict:
        if df is None or len(df) < 50: return None

        close = df['close']
        high = df['high']
        low = df['low']

        curr_rsi = ta.momentum.rsi(close, window=self.rsi_window).iloc[-1]
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        bb_h = bb.bollinger_hband().iloc[-1]
        bb_l = bb.bollinger_lband().iloc[-1]
        curr_atr = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
        
        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        sig_val = macd.macd_signal().iloc[-1]

        signal = "NEUTRAL"
        score = 50
        reason = []

        if curr_rsi < self.rsi_oversold and close.iloc[-1] <= bb_l:
            if macro_trend != "DOWNTREND": 
                signal = "BUY"
                score += 30
                reason.append("RSI Oversold")
        elif curr_rsi > self.rsi_overbought and close.iloc[-1] >= bb_h:
            if macro_trend != "UPTREND":
                signal = "SELL"
                score -= 30
                reason.append("RSI Overbought")

        if macd_val > sig_val and macro_trend == "UPTREND":
            signal = "STRONG BUY"
            score += 20
            reason.append("MACD Cross + Trend Ủng hộ")
        if macd_val < sig_val and macro_trend == "DOWNTREND":
            signal = "STRONG SELL"
            score -= 20
            reason.append("MACD Cross + Trend Ủng hộ")

        entry = close.iloc[-1]
        sl, tp = 0, 0
        if "BUY" in signal:
            sl = entry - (curr_atr * self.sl_multiplier)
            tp = entry + (curr_atr * self.tp_multiplier) 
        elif "SELL" in signal:
            sl = entry + (curr_atr * self.sl_multiplier)
            tp = entry - (curr_atr * self.tp_multiplier)

        return {
            "strategy": self.name, # Đánh dấu tín hiệu này từ chiến thuật nào
            "rsi": round(curr_rsi, 2),
            "macd": round(macd_val, 5),
            "atr": round(curr_atr, 4),
            "signal": signal,
            "macro_trend": macro_trend,
            "score": min(100, max(0, score)),
            "suggested_sl": round(sl, 2),
            "suggested_tp": round(tp, 2),
            "reason": ", ".join(reason) if reason else "Chờ tín hiệu..."
        }

    def analyze_history(self, df: pd.DataFrame) -> list:
        if df is None or len(df) < 200: return []
        
        markers = []
        close, high, low = df['close'], df['high'], df['low']
        
        ema_200 = ta.trend.ema_indicator(close, window=200)
        ema_50 = ta.trend.ema_indicator(close, window=50)
        rsi = ta.momentum.rsi(close, window=14)
        atr = ta.volatility.average_true_range(high, low, close, window=14)

        times, close_arr, high_arr, low_arr = df['time'].values, close.values, high.values, low.values
        ema200_arr, ema50_arr, rsi_arr, atr_arr = ema_200.values, ema_50.values, rsi.values, atr.values

        for i in range(200, len(df) - 5):
            raw_t = times[i]
            ts = 0
            try:
                if isinstance(raw_t, (int, float)):
                    ts = int(raw_t // 10**9) if raw_t > 1000000000000 else int(raw_t)
                elif hasattr(raw_t, 'timestamp'): ts = int(raw_t.timestamp())
                else: ts = int(pd.to_datetime(raw_t).timestamp())
            except: continue

            signal_type = None
            is_uptrend = close_arr[i] > ema200_arr[i] and ema50_arr[i] > ema200_arr[i]
            is_downtrend = close_arr[i] < ema200_arr[i] and ema50_arr[i] < ema200_arr[i]

            if is_uptrend and rsi_arr[i] < 45 and rsi_arr[i-1] >= 45:
                signal_type = "BUY"
            elif is_downtrend and rsi_arr[i] > 55 and rsi_arr[i-1] <= 55:
                signal_type = "SELL"
            
            if not signal_type: continue

            entry_price, current_atr = close_arr[i], atr_arr[i]
            sl_dist, tp_dist = current_atr * 2.5, current_atr * 1.5
            
            sl_price = entry_price - sl_dist if signal_type == "BUY" else entry_price + sl_dist
            tp_price = entry_price + tp_dist if signal_type == "BUY" else entry_price - tp_dist
            
            outcome = "RUNNING"
            for j in range(1, 60):
                if i + j >= len(df): break
                next_high, next_low = high_arr[i+j], low_arr[i+j]
                
                if signal_type == "BUY":
                    if next_low <= sl_price: outcome = "LOSS"; break
                    if next_high >= tp_price: outcome = "WIN"; break
                else: 
                    if next_high >= sl_price: outcome = "LOSS"; break
                    if next_low <= tp_price: outcome = "WIN"; break

            markers.append({
                "time": ts,
                "position": "belowBar" if signal_type == "BUY" else "aboveBar",
                "shape": "arrowUp" if signal_type == "BUY" else "arrowDown",
                "result": outcome,
                "size": 1
            })
            
        return markers