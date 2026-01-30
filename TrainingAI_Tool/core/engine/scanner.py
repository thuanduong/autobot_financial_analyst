import asyncio
from core.data_provider.mt5_provider import MT5Provider
from config.settings import WATCHLIST
from database.chart_repo import ChartRepo

class MarketScanner:
    def __init__(self, bus):
        self.mt5 = MT5Provider()
        self.bus = bus
        self.latest_scan = {} 
        self.chart_repo = ChartRepo()

    async def run(self):
        print("📡 Radar bắt đầu quét...")
        while True:
            await self.scan()
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