import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class PriceActionPinbarStrategy(BaseStrategy):
    def __init__(self, config=None):
        super().__init__(name="PRICE_ACTION_V1", config=config)
        self.lookback = self.config.get("lookback", 20)
        self.zone_tolerance_pct = self.config.get("zone_tolerance", 0.15)

    def analyze(self, df: pd.DataFrame, macro_trend: str = "NEUTRAL") -> dict:
        if df is None or len(df) < self.lookback + 5: return None

        h_slice = df['high'].iloc[-self.lookback-2:-2]
        l_slice = df['low'].iloc[-self.lookback-2:-2]
        
        recent_high = h_slice.max()
        recent_low = l_slice.min()

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        curr_body = abs(curr['close'] - curr['open'])
        curr_lower_wick = min(curr['open'], curr['close']) - curr['low']
        curr_upper_wick = curr['high'] - max(curr['open'], curr['close'])
        candle_range = max(curr['high'] - curr['low'], 0.0001)
        safe_body = max(curr_body, 0.0001)

        # Logic Patterns
        bullish_pinbar = (curr_lower_wick > 2 * safe_body) and (curr_upper_wick < safe_body) and (curr_lower_wick > 0.5 * candle_range)
        bearish_pinbar = (curr_upper_wick > 2 * safe_body) and (curr_lower_wick < safe_body) and (curr_upper_wick > 0.5 * candle_range)
        
        bullish_engulfing = (prev['close'] < prev['open']) and (curr['close'] > curr['open']) and \
                           (curr['close'] > prev['open']) and (curr['open'] < prev['close'])
        bearish_engulfing = (prev['close'] > prev['open']) and (curr['close'] < curr['open']) and \
                           (curr['close'] < prev['open']) and (curr['open'] > prev['close'])

        # Zone check
        zone_tolerance = (recent_high - recent_low) * self.zone_tolerance_pct
        near_support = curr['low'] <= (recent_low + zone_tolerance)
        near_resistance = curr['high'] >= (recent_high - zone_tolerance)

        signal = "NEUTRAL"
        score = 50
        reason = []
        sl, tp = 0.0, 0.0

        if (bullish_pinbar or bullish_engulfing) and near_support:
            if macro_trend != "DOWNTREND":
                signal = "BUY"
                score = 88
                pat = "PinBar" if bullish_pinbar else "Engulfing"
                reason.append(f"{pat} at Support ({recent_low:.2f})")
                sl = min(curr['low'], recent_low)
                tp = curr['close'] + (curr['close'] - sl) * 2.0

        elif (bearish_pinbar or bearish_engulfing) and near_resistance:
            if macro_trend != "UPTREND":
                signal = "SELL"
                score = 88
                pat = "PinBar" if bearish_pinbar else "Engulfing"
                reason.append(f"{pat} at Resistance ({recent_high:.2f})")
                sl = max(curr['high'], recent_high)
                tp = curr['close'] - (sl - curr['close']) * 2.0

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
        if df is None or len(df) < self.lookback + 10: return []
        
        markers = []
        # Vector hóa dữ liệu để tăng tốc
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        times = df['time'].values

        for i in range(self.lookback + 2, len(df) - 5):
            # Lấy vùng support/resistance trong quá khứ
            h_slice = highs[i-self.lookback-1 : i-1]
            l_slice = lows[i-self.lookback-1 : i-1]
            r_high = np.max(h_slice)
            r_low = np.min(l_slice)
            
            c_o, c_h, c_l, c_c = opens[i], highs[i], lows[i], closes[i]
            p_o, p_c = opens[i-1], closes[i-1]

            # Tính toán nến
            body = abs(c_c - c_o)
            l_wick = min(c_o, c_c) - c_l
            u_wick = c_h - max(c_o, c_c)
            c_range = max(c_h - c_l, 0.0001)
            s_body = max(body, 0.0001)

            # Logic
            is_bull_pin = (l_wick > 2 * s_body) and (u_wick < s_body) and (l_wick > 0.5 * c_range)
            is_bear_pin = (u_wick > 2 * s_body) and (l_wick < s_body) and (u_wick > 0.5 * c_range)
            is_bull_eng = (p_c < p_o) and (c_c > c_o) and (c_c > p_o) and (c_o < p_c)
            is_bear_eng = (p_c > p_o) and (c_c < c_o) and (c_c < p_o) and (c_o > p_c)

            z_tol = (r_high - r_low) * self.zone_tolerance_pct
            
            sig = None
            if (is_bull_pin or is_bull_eng) and c_l <= (r_low + z_tol):
                sig = "BUY"
            elif (is_bear_pin or is_bear_eng) and c_h >= (r_high - z_tol):
                sig = "SELL"

            if not sig: continue

            # Kết quả giả lập
            sl = r_low if sig == "BUY" else r_high
            tp = c_c + (c_c - sl)*2 if sig == "BUY" else c_c - (sl - c_c)*2
            outcome = "RUNNING"
            for j in range(1, 30):
                if i+j >= len(df): break
                if sig == "BUY":
                    if lows[i+j] <= sl: outcome = "LOSS"; break
                    if highs[i+j] >= tp: outcome = "WIN"; break
                else:
                    if highs[i+j] >= sl: outcome = "LOSS"; break
                    if lows[i+j] <= tp: outcome = "WIN"; break

            raw_t = times[i]
            ts = int(raw_t.timestamp()) if hasattr(raw_t, 'timestamp') else int(raw_t)
            if ts > 1000000000000: ts //= 1000

            markers.append({
                "time": ts,
                "position": "belowBar" if sig == "BUY" else "aboveBar",
                "shape": "arrowUp" if sig == "BUY" else "arrowDown",
                "result": outcome,
                "strategy_id": self.name
            })

        return markers