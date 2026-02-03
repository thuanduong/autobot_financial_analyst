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

    @staticmethod
    def analyze_history(df):
        if df is None or len(df) < 200: return []
        
        markers = []
        
        # 1. Tính toán chỉ báo
        close = df['close']
        high = df['high']
        low = df['low']
        
        # EMA 200 (Xu hướng dài)
        ema_200 = ta.trend.ema_indicator(close, window=200)
        # EMA 50 (Xu hướng trung hạn - Thêm cái này để xác nhận lực)
        ema_50 = ta.trend.ema_indicator(close, window=50)
        
        rsi = ta.momentum.rsi(close, window=14)
        atr = ta.volatility.average_true_range(high, low, close, window=14)

        # Convert sang numpy array
        times = df['time'].values
        close_arr = close.values
        high_arr = high.values
        low_arr = low.values
        ema200_arr = ema_200.values
        ema50_arr = ema_50.values
        rsi_arr = rsi.values
        atr_arr = atr.values

        # 2. Duyệt nến
        for i in range(200, len(df) - 5):
            
            # Xử lý Time an toàn
            raw_t = times[i]
            ts = 0
            try:
                if isinstance(raw_t, (int, float)):
                    if raw_t > 1000000000000: ts = int(raw_t // 10**9)
                    else: ts = int(raw_t)
                elif hasattr(raw_t, 'timestamp'): ts = int(raw_t.timestamp())
                else: ts = int(pd.to_datetime(raw_t).timestamp())
            except: continue

            signal_type = None

            # --- CHIẾN THUẬT NÂNG CẤP (EMA CROSS + RSI PULLBACK) ---
            # Chỉ đánh khi 2 đường EMA đồng thuận -> Lực trend mạnh
            
            # BUY: Giá > EMA 200 VÀ EMA 50 > EMA 200 (Uptrend mạnh)
            is_uptrend = close_arr[i] > ema200_arr[i] and ema50_arr[i] > ema200_arr[i]
            
            # SELL: Giá < EMA 200 VÀ EMA 50 < EMA 200 (Downtrend mạnh)
            is_downtrend = close_arr[i] < ema200_arr[i] and ema50_arr[i] < ema200_arr[i]

            if is_uptrend:
                # RSI về vùng 45 là Múc (Nới lỏng hơn để bắt nhịp chỉnh)
                if rsi_arr[i] < 45 and rsi_arr[i-1] >= 45:
                    signal_type = "BUY"
            
            elif is_downtrend:
                # RSI lên vùng 55 là Sút
                if rsi_arr[i] > 55 and rsi_arr[i-1] <= 55:
                    signal_type = "SELL"
            
            if not signal_type: continue

            # --- LOGIC BACKTEST (TỐI ƯU CHO VÀNG) ---
            entry_price = close_arr[i]
            current_atr = atr_arr[i]
            
            # ĐẶC TRỊ VÀNG:
            # SL rộng ra (2.5 ATR) để tránh quét râu
            # TP ngắn lại (1.5 ATR) để ăn chắc (Winrate cao hơn R:R)
            sl_dist = current_atr * 2.5
            tp_dist = current_atr * 1.5
            
            sl_price = entry_price - sl_dist if signal_type == "BUY" else entry_price + sl_dist
            tp_price = entry_price + tp_dist if signal_type == "BUY" else entry_price - tp_dist
            
            outcome = "RUNNING"
            
            # Tăng thời gian kiểm tra lên 60 nến (khoảng 5 tiếng với M5)
            # Để giảm bớt các lệnh RUNNING
            for j in range(1, 60):
                if i + j >= len(df): break
                next_high = high_arr[i+j]
                next_low = low_arr[i+j]
                
                if signal_type == "BUY":
                    if next_low <= sl_price: outcome = "LOSS"; break # Chạm SL trước
                    if next_high >= tp_price: outcome = "WIN"; break # Chạm TP sau
                else: 
                    if next_high >= sl_price: outcome = "LOSS"; break
                    if next_low <= tp_price: outcome = "WIN"; break

            # Màu sắc Marker
            marker_color = "#8b949e" # Mặc định xám (Running)
            if outcome == "WIN": marker_color = "#2ea043" # Xanh
            elif outcome == "LOSS": marker_color = "#da3633" # Đỏ

            # Chỉ vẽ nếu WIN hoặc LOSS (hoặc vẽ hết nếu muốn debug)
            # Ở đây vẽ hết để bạn thấy cả lệnh Running
            marker_text = f"{signal_type} {outcome}"
            
            markers.append({
                "time": ts,
                "position": "belowBar" if signal_type == "BUY" else "aboveBar",
                "color": marker_color,
                "shape": "arrowUp" if signal_type == "BUY" else "arrowDown",
                "text": marker_text,
                "size": 1
            })
            
        return markers