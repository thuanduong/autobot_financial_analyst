import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class VWAPReversionStrategy(BaseStrategy):
    def __init__(self, config=None):
        super().__init__(name="VWAP_REVERSION_V1", config=config)
        self.window = self.config.get("period", 100)
        self.std_multiplier = self.config.get("std_dev_multiplier", 2.5) # Độ lệch chuẩn 2.5 ôm trọn 98% dao động giá

    def analyze(self, df: pd.DataFrame, macro_trend: str = "NEUTRAL") -> dict:
        # Kiểm tra đủ nến
        if df is None or len(df) < self.window + 5: return None

        # Copy ra để tránh warning SettingWithCopy
        df = df.copy()

        # 1. TÍNH TOÁN TYPICAL PRICE (Giá điển hình)
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['vol_price'] = df['typical_price'] * df['tick_volume']

        # 2. TÍNH TOÁN ROLLING VWAP
        rolling_vol_price = df['vol_price'].rolling(window=self.window).sum()
        rolling_vol = df['tick_volume'].rolling(window=self.window).sum()
        df['vwap'] = rolling_vol_price / rolling_vol

        # 3. TÍNH TOÁN ĐỘ LỆCH CHUẨN (STANDARD DEVIATION)
        df['std_dev'] = df['typical_price'].rolling(window=self.window).std()

        # 4. TẠO DẢI BĂNG GIỚI HẠN (UPPER & LOWER BANDS)
        df['upper_band'] = df['vwap'] + (self.std_multiplier * df['std_dev'])
        df['lower_band'] = df['vwap'] - (self.std_multiplier * df['std_dev'])

        # Lấy nến hiện tại và nến liền trước
        current = df.iloc[-1]
        prev = df.iloc[-2]

        # Khởi tạo mặc định
        signal = "NEUTRAL"
        score = 0
        reason = ""
        sl = 0.0
        tp = 0.0

        curr_close = current['close']
        curr_open = current['open']
        prev_close = prev['close']
        prev_high = prev['high']
        prev_low = prev['low']
        prev_upper = prev['upper_band']
        prev_lower = prev['lower_band']

        # 5. LOGIC VÀO LỆNH (MEAN REVERSION)
        
        # BÁN (SELL) KHI GIÁ TĂNG QUÁ ĐÀ:
        # Điều kiện: Nến trước đâm thủng dải trên (quá xa VWAP), Nến nay là nến Đỏ (rút chân/đảo chiều)
        sell_condition = (prev_close > prev_upper or prev_high > prev_upper) and curr_close < curr_open
        
        # MUA (BUY) KHI GIÁ GIẢM QUÁ ĐÀ:
        # Điều kiện: Nến trước đâm thủng dải dưới (bán tháo), Nến nay là nến Xanh (rút chân/đảo chiều)
        buy_condition = (prev_close < prev_lower or prev_low < prev_lower) and curr_close > curr_open

        if buy_condition:
            # Lọc xu hướng: Nếu đang Downtrend mạnh thì hạn chế bắt đáy (Mean Reversion rủi ro cao)
            if macro_trend != "DOWNTREND":
                signal = "BUY"
                score = 80
                reason = f"Giá quá bán (Dev {self.std_multiplier}) + Nến xanh đảo chiều"
                # Cắt lỗ: Dưới râu nến thấp nhất của cụm đảo chiều
                sl = min(current['low'], prev_low)
                # Chốt lời: Kỳ vọng giá bị hút thẳng về lại đường VWAP trung bình
                tp = current['vwap'] 
        
        elif sell_condition:
            # Lọc xu hướng: Nếu đang Uptrend mạnh thì hạn chế chặn đầu xe lửa
            if macro_trend != "UPTREND":
                signal = "SELL"
                score = 80
                reason = f"Giá quá mua (Dev {self.std_multiplier}) + Nến đỏ đảo chiều"
                # Cắt lỗ: Trên đỉnh râu nến cao nhất
                sl = max(current['high'], prev_high)
                tp = current['vwap']

        if signal == "NEUTRAL": return None

        return {
            "strategy": self.name,
            "signal": signal,
            "score": score,
            "reason": reason,
            "suggested_sl": round(sl, 2),
            "suggested_tp": round(tp, 2),
            "macro_trend": macro_trend
        }

    def analyze_history(self, df: pd.DataFrame) -> list:
        if df is None or len(df) < self.window + 10: return []
        
        # Tính toán lại chỉ báo cho toàn bộ dataframe
        df = df.copy()
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['vol_price'] = df['typical_price'] * df['tick_volume']
        rolling_vol_price = df['vol_price'].rolling(window=self.window).sum()
        rolling_vol = df['tick_volume'].rolling(window=self.window).sum()
        df['vwap'] = rolling_vol_price / rolling_vol
        df['std_dev'] = df['typical_price'].rolling(window=self.window).std()
        df['upper_band'] = df['vwap'] + (self.std_multiplier * df['std_dev'])
        df['lower_band'] = df['vwap'] - (self.std_multiplier * df['std_dev'])

        markers = []
        times = df['time'].values
        close = df['close'].values; open_p = df['open'].values; high = df['high'].values; low = df['low'].values
        upper = df['upper_band'].values; lower = df['lower_band'].values; vwap = df['vwap'].values

        # Quét quá khứ
        for i in range(self.window + 1, len(df) - 5):
            if np.isnan(upper[i]) or np.isnan(vwap[i]): continue

            ts = int(times[i].timestamp()) if hasattr(times[i], 'timestamp') else int(times[i])
            if ts > 1000000000000: ts = ts // 1000

            # Logic tương tự hàm analyze
            buy_sig = (close[i-1] < lower[i-1] or low[i-1] < lower[i-1]) and close[i] > open_p[i]
            sell_sig = (close[i-1] > upper[i-1] or high[i-1] > upper[i-1]) and close[i] < open_p[i]

            sig_type = "BUY" if buy_sig else ("SELL" if sell_sig else None)
            if not sig_type: continue

            outcome = "RUNNING" # Giả lập kết quả nhanh (để hiển thị màu mũi tên)
            # Logic check WIN/LOSS đơn giản: Chạm VWAP là WIN
            target = vwap[i]
            for j in range(1, 60):
                if i+j >= len(df): break
                if (sig_type == "BUY" and high[i+j] >= target) or (sig_type == "SELL" and low[i+j] <= target):
                    outcome = "WIN"; break
            
            markers.append({
                "time": ts,
                "position": "belowBar" if sig_type == "BUY" else "aboveBar",
                "shape": "arrowUp" if sig_type == "BUY" else "arrowDown",
                "result": outcome,
                "size": 1,
                "strategy_id": self.name
            })
        
        return markers