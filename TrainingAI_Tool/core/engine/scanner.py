import asyncio
import pandas as pd
from core.data_provider.mt5_provider import MT5Provider
from config.settings import WATCHLIST, TIMEFRAMES
from database.chart_repo import ChartRepo
from core.engine.technical import TechnicalAnalyzer
import datetime

class MarketScanner:
    def __init__(self, bus):
        self.mt5 = MT5Provider()
        self.chart_repo = ChartRepo()

        self.bus = bus
        self.latest_scan = {tf: {} for tf in TIMEFRAMES["Micro"]}
        self.is_running = False
        self.market_status = "LOADING"

    def check_market_status(self):
        """Kiểm tra xem có phải cuối tuần không"""
        today = datetime.datetime.now().weekday()
        # 5 = Thứ 7, 6 = Chủ Nhật
        if today >= 5:
            self.market_status = "CLOSED (Weekend)"
            return False
        self.market_status = "OPEN"
        return True
    
    async def run(self):
        if not self.check_market_status():
            print("💤 Market Closed (Weekend). Scanner sleeping...")
            return
        print("📡 Radar bắt đầu quét...")
        selfis_running = False
        
        while True:
            #await self.scan()
            await self.scan_smart()
            await asyncio.sleep(5) # Quét mỗi 5 giây

    async def scan(self):
        if not self.mt5.connect(): return
        current_scan_results = {}
        for symbol in WATCHLIST:
            df = self.mt5.get_data(symbol, n=200)
            if df is None: 
                # print(f"⚠️ Không lấy được nến cho {symbol}")
                continue
            self.chart_repo.save_bulk_data(symbol, df)
            
            last = df.iloc[-1]
            rsi = last['RSI']
            price = last['close']
            
            signal = "NEUTRAL"
            score = 50

            # Logic Demo
            if rsi < 35: 
                signal = "BUY"; score = 80
            elif rsi > 60:
                signal = "SELL"; score = 80

            # Lưu cache
            current_scan_results[symbol] = {
                "symbol": symbol,
                "price": price,
                "signal": signal,
                "score": score,
                "rsi": round(rsi, 2)
            }

            # Bắn tín hiệu nếu điểm cao
            if score >= 80:
                await self.bus.process_signal({
                    "symbol": symbol, "action": signal, "score": score
                })
        self.latest_scan = current_scan_results

    async def scan_smart(self):
        if not self.mt5.connect(): 
            print("⚠️ MT5 Disconnected")
            return

        # 1. Quét Macro Trend trước (H1) cho tất cả cặp
        macro_trends = {}
        for symbol in WATCHLIST:
            df_macro = self.mt5.get_data(symbol, timeframe=TIMEFRAMES["Macro"], n=250)
            macro_trends[symbol] = TechnicalAnalyzer.get_trend(df_macro)

        # 2. Quét chi tiết từng khung Micro
        for tf in TIMEFRAMES["Micro"]:
            temp_results = {}
            for symbol in WATCHLIST:
                try:
                    df = self.mt5.get_data(symbol, timeframe=tf, n=100)
                    if df is None: continue

                    # Lưu DB 
                    if tf == "M5": self.chart_repo.save_bulk_data(symbol, df)

                    current_macro = macro_trends.get(symbol, "NEUTRAL")

                    # Phân tích
                    analysis = TechnicalAnalyzer.analyze(df, current_macro)
                    
                    if analysis:
                        temp_results[symbol] = {
                            "symbol": symbol,
                            "price": df['close'].iloc[-1],
                            **analysis
                        }
                except Exception as e:
                    print(f"Error {symbol} {tf}: {e}")
            
            self.latest_scan[tf] = temp_results