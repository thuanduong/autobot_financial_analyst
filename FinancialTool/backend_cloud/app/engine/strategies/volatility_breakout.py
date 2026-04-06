import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class VolatilityBreakoutStrategy(BaseStrategy):
    def __init__(self, config=None):
        super().__init__(name="VOLATILITY_BREAKOUT_V1", config=config)
        self.period = self.config.get("period", 20)
        self.std_dev = self.config.get("std_dev", 2.0)
        self.vol_period = self.config.get("volume_ma_period", 20)

    def analyze(self, df: pd.DataFrame, macro_trend: str = "NEUTRAL") -> dict:
        if df is None or len(df) < self.period + 5: return None

        # Sử dụng biến cục bộ để tránh modify DataFrame gốc (Shared Buffer)
        close = df['close']
        tick_volume = df['tick_volume']

        # 1. Bollinger Bands
        sma = close.rolling(window=self.period).mean()
        std = close.rolling(window=self.period).std()
        upper_band = sma + (self.std_dev * std)
        lower_band = sma - (self.std_dev * std)

        # 2. Volume SMA
        vol_sma = tick_volume.rolling(window=self.vol_period).mean()

        # Lấy giá trị hiện tại
        curr_close = close.iloc[-1]
        curr_vol = tick_volume.iloc[-1]
        curr_upper = upper_band.iloc[-1]
        curr_lower = lower_band.iloc[-1]
        curr_vol_sma = vol_sma.iloc[-1]
        curr_sma = sma.iloc[-1]

        # Lấy giá trị nến trước
        prev_close = close.iloc[-2]
        prev_upper = upper_band.iloc[-2]
        prev_lower = lower_band.iloc[-2]

        # 3. Logic Conditions
        buy_breakout = curr_close > curr_upper
        sell_breakout = curr_close < curr_lower
        volume_surge = curr_vol > (curr_vol_sma * 1.5)
        prev_contained = (prev_close <= prev_upper) and (prev_close >= prev_lower)

        signal = "NEUTRAL"
        score = 50
        reason = []
        sl, tp = 0.0, 0.0

        if buy_breakout and volume_surge and prev_contained:
            if macro_trend != "DOWNTREND":
                signal = "BUY"
                score = 85
                reason.append("Breakout Upper Band + Vol Surge")
                sl = curr_sma
                tp = curr_close + (curr_close - sl) * 2.0
        elif sell_breakout and volume_surge and prev_contained:
            if macro_trend != "UPTREND":
                signal = "SELL"
                score = 85
                reason.append("Breakout Lower Band + Vol Surge")
                sl = curr_sma
                tp = curr_close - (sl - curr_close) * 2.0

        if signal == "NEUTRAL": return None
        
        return {
            "strategy": self.name,
            "signal": signal,
            "score": score,
            "reason": ", ".join(reason),
            "suggested_sl": round(sl, 2) if sl else None,
            "suggested_tp": round(tp, 2) if tp else None,
            "macro_trend": macro_trend
        }

    def analyze_history(self, df: pd.DataFrame) -> list:
        if df is None or len(df) < 100: return []
        
        markers = []
        close = df['close']; high = df['high']; low = df['low']; tick_volume = df['tick_volume']
        times = df['time'].values
        
        sma = close.rolling(window=self.period).mean()
        std = close.rolling(window=self.period).std()
        upper = sma + (self.std_dev * std)
        lower = sma - (self.std_dev * std)
        vol_sma = tick_volume.rolling(window=self.vol_period).mean()

        # Convert to numpy for speed
        c_arr = close.values; h_arr = high.values; l_arr = low.values
        v_arr = tick_volume.values; u_arr = upper.values; l_band_arr = lower.values
        vsma_arr = vol_sma.values; sma_arr = sma.values

        for i in range(self.period + 1, len(df) - 5):
            # Timestamp handling
            raw_t = times[i]
            ts = int(raw_t.timestamp()) if hasattr(raw_t, 'timestamp') else int(raw_t)
            if ts > 1000000000000: ts = ts // 1000

            # Logic check
            if np.isnan(u_arr[i]) or np.isnan(vsma_arr[i]): continue
            
            is_buy = (c_arr[i] > u_arr[i]) and (v_arr[i] > vsma_arr[i] * 1.5) and \
                     (c_arr[i-1] <= u_arr[i-1] and c_arr[i-1] >= l_band_arr[i-1])
                     
            is_sell = (c_arr[i] < l_band_arr[i]) and (v_arr[i] > vsma_arr[i] * 1.5) and \
                      (c_arr[i-1] <= u_arr[i-1] and c_arr[i-1] >= l_band_arr[i-1])

            sig = "BUY" if is_buy else ("SELL" if is_sell else None)
            if not sig: continue

            # Simulation (Quick check 60 candles)
            entry = c_arr[i]; sl = sma_arr[i]
            tp = entry + (entry - sl)*2 if sig == "BUY" else entry - (sl - entry)*2
            outcome = "RUNNING"
            
            for j in range(1, 60):
                if i+j >= len(df): break
                if sig == "BUY":
                    if l_arr[i+j] <= sl: outcome = "LOSS"; break
                    if h_arr[i+j] >= tp: outcome = "WIN"; break
                else:
                    if h_arr[i+j] >= sl: outcome = "LOSS"; break
                    if l_arr[i+j] <= tp: outcome = "WIN"; break

            markers.append({
                "time": ts,
                "position": "belowBar" if sig == "BUY" else "aboveBar",
                "shape": "arrowUp" if sig == "BUY" else "arrowDown",
                "result": outcome,
                "size": 1,
                "strategy_id": self.name
            })
            
        return markers