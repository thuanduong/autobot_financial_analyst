import asyncio
import pandas as pd
import time
from datetime import datetime
from backend_cloud.app.services.mt5_feed import mt5_feed
from backend_cloud.config.settings import WATCHLIST, TIMEFRAMES, MAX_CANDLES_CONFIG
from backend_cloud.app.api.websocket import ws_manager
from backend_cloud.app.database.chart_repo import ChartRepo 
from backend_cloud.app.core.utils import clean_symbol_for_client, resolve_broker_symbol
from backend_cloud.app.engine.market_buffer import market_buffer
from backend_cloud.app.engine.technical_manager import tech_engine
from backend_cloud.app.database.analyze_repo import AnalyzeRepo
from backend_cloud.app.engine.bot_manager import bot_engine
from backend_cloud.app.services.news_feed import news_service

class MarketScanner:
    def __init__(self, char_repo: ChartRepo, analyze_repo: AnalyzeRepo):
        self.symbols = WATCHLIST
        self.timeframes = TIMEFRAMES.get("Watch", ["M1", "M5", "H1", "H4"])
        self.repo = char_repo
        self.analyze_repo = analyze_repo
        self.is_running = False
        self.market_status = "LOADING"
        self.radar_matrix = {} # { symbol: { tf: [analysis_results] } }
        self.last_tick_scan = {}
        self.broadcast_queue = asyncio.Queue()
        bot_engine.setAnalyzeRepo(analyze_repo=analyze_repo)

    def _update_last_candle_time(self, symbol, tf, df_new):
        if df_new is None or df_new.empty: 
            return
            
        last_candle_time = df_new.iloc[-1]['time']
        
        if symbol not in self.last_tick_scan:
            self.last_tick_scan[symbol] = {}
            
        self.last_tick_scan[symbol][tf] = last_candle_time

    def _get_n_fetch(self, symbol, tf, max_n):
        if symbol in self.last_tick_scan and tf in self.last_tick_scan[symbol]:
            return 5
        return max_n
    
    async def run_loop(self):
        print("🚀 Market Scanner Started (Pandas/Raw SQL Engine)...")
        if not self.check_market_status():
            print("💤 Market Closed (Weekend). Scanner sleeping...")
            return
        print("📡 Radar bắt đầu quét...")
        self.is_running = True
        
        await self.initial_backfill()
        bot_engine.sync_pending_orders()
        
        news_service.fetch_calendar()
        
        asyncio.create_task(self.broadcast_worker())

        while self.is_running:
            await self.run()
            await self.analyze()
            self._prune_stale_radar() # Dọn dẹp các tín hiệu cũ trong RAM
            await asyncio.sleep(0.5)
            
    def check_market_status(self):
        """Kiểm tra xem có phải cuối tuần không"""
        today = datetime.now().weekday()
        # 5 = Thứ 7, 6 = Chủ Nhật
        if today >= 5:
            self.market_status = "CLOSED (Weekend)"
            return False
        self.market_status = "OPEN"
        return True

    async def initial_backfill(self):
        # Kết nối MT5 trong một thread riêng để tránh block startup
        connected = await asyncio.to_thread(mt5_feed.connect)
        if not connected:
            print("❌ Scanner: Không thể kết nối MT5 để Backfill")
            return
            
        print("🔄 Đang tải dữ liệu lịch sử...")
        
        for tf in TIMEFRAMES["Watch"]:
            limit = MAX_CANDLES_CONFIG.get(tf, 5000)
            for symbol in WATCHLIST:
                try:
                    df = await asyncio.to_thread(mt5_feed.get_candles, symbol, timeframe=tf, n=limit)
                    if df is not None and not df.empty:
                        # Đưa việc lưu DB vào thread riêng
                        await asyncio.to_thread(self.repo.save_bulk_data, symbol, df, timeframe=tf, max_records=limit)
                        
                        # Đánh dấu đã scan xong
                        self._update_last_candle_time(symbol, tf, df)
                        
                        # Buffer cũng cần thread-safe nếu dữ liệu lớn
                        await asyncio.to_thread(market_buffer.init_buffer, symbol, tf, df)
                except Exception as e:
                    print(f"❌ Lỗi Init Backfill {symbol} {tf}: {e}")
        print("✅ Đã lấp đầy Database!")

    async def run(self):
        if not mt5_feed.connect(): return

        for tf in TIMEFRAMES["Watch"]:
            limit = MAX_CANDLES_CONFIG.get(tf, 5000)
            for symbol in WATCHLIST:
                try:
                    n_fetch = self._get_n_fetch(symbol, tf, max_n=100)
                    df = await asyncio.to_thread(mt5_feed.get_candles, symbol, timeframe=tf, n=n_fetch)
                    #print(f"get {symbol} ")
                    if df is None or df.empty: continue

                    # BƯỚC B: GHI VÀO DATABASE BẰNG SQL THUẦN
                    await asyncio.to_thread(self.repo.save_bulk_data, symbol, df, timeframe=tf, max_records=limit)
                    self._update_last_candle_time(symbol, tf, df)
                    await asyncio.to_thread(market_buffer.update_from_df, symbol, tf, df)

                    if len(df) >= 2:
                        last_2_candles = df.iloc[-2:].copy()
                        self.broadcast_queue.put_nowait({
                            "symbol": symbol,
                            "tf": tf,
                            "df": last_2_candles
                        })
                except Exception as e:
                    print(f"Error {symbol} {tf}: {e}")
            

    async def broadcast_worker(self):
        """Luồng riêng chuyên trách việc gửi WebSocket, không làm phiền Scanner"""
        print("🚀 Broadcast Worker Started...")
        while True:
            # Chờ lấy item từ hàng đợi
            item = await self.broadcast_queue.get()
            
            try:
                symbol = item['symbol']
                tf = item['tf']
                df = item['df']
                
                client_symbol = clean_symbol_for_client(symbol)

                # Convert 2 nến sang JSON
                candles_data = []
                for _, row in df.iterrows():
                    # Xử lý time an toàn
                    t_val = row['time']
                    if hasattr(t_val, 'timestamp'):
                        unix_time = int(t_val.timestamp())
                    else:
                        unix_time = int(t_val)

                    candles_data.append({
                        "time": unix_time,
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "value": float(row.get('tick_volume', 0))
                    })
                #print(f"broadcast {symbol} and client {client_symbol}")
                # Gửi payload chứa mảng nến
                payload = {
                    "type": "PRICE_UPDATE",
                    "symbol": symbol,
                    "tf": tf,
                    "data": candles_data # Gửi cả list 2 nến
                }
                await ws_manager.broadcast(payload)

                _payload = {
                    "type": "PRICE_UPDATE",
                    "symbol": client_symbol,
                    "tf": tf,
                    "data": candles_data
                }
                await ws_manager.broadcast(_payload)

            except Exception as e:
                print(f"Broadcast Error: {e}")
            finally:
                # Báo hiệu đã xử lý xong item này
                self.broadcast_queue.task_done()

    async def analyze(self):
        if not mt5_feed.connect(): return
        # Ưu tiên sử dụng cấu hình Multi để hợp lưu nhiều khung, fallback về Pairing
        multi_rules = TIMEFRAMES.get("Multi", {})
        pairing_rules = TIMEFRAMES.get("Pairing", {})

        for tf_micro in TIMEFRAMES["Micro"]:
            # Lấy danh sách các khung Macro cần check
            tfs_macro = multi_rules.get(tf_micro)
            if tfs_macro is None:
                tfs_macro = [pairing_rules.get(tf_micro, "H1")]
            
            for symbol in WATCHLIST:
                try:
                    # 1. XÁC ĐỊNH XU HƯỚNG ĐỒNG THUẬN (CONSENSUS)
                    current_macro_trend = "NEUTRAL"
                    macro_trends = []
                    macro_vols_expanding = []

                    for tf_macro in tfs_macro:
                        df_macro = market_buffer.get_dataframe(symbol, tf_macro)
                        if not df_macro.empty:
                            # Check Price Trend
                            macro_trends.append(tech_engine.get_trend(df_macro))
                            
                            # Check Volume Consensus: Volume hiện tại > Trung bình 20 phiên
                            # Giúp xác nhận đà tăng/giảm có sự ủng hộ của thanh khoản
                            vols = df_macro['tick_volume']
                            if len(vols) >= 20:
                                is_expanding = vols.iloc[-1] > vols.tail(20).mean()
                                macro_vols_expanding.append(is_expanding)
                            else:
                                macro_vols_expanding.append(True) # Không đủ dữ liệu thì bỏ qua lọc vol

                    # Chỉ xác nhận xu hướng nếu TẤT CẢ các khung Macro đồng thuận cả về GIÁ và KHỐI LƯỢNG
                    vol_consensus = all(macro_vols_expanding) if macro_vols_expanding else False
                    
                    if vol_consensus and macro_trends and all(t == "UPTREND" for t in macro_trends):
                        current_macro_trend = "UPTREND"
                    elif vol_consensus and macro_trends and all(t == "DOWNTREND" for t in macro_trends):
                        current_macro_trend = "DOWNTREND"

                    # 2. PHÂN TÍCH ĐIỂM VÀO LỆNH TRÊN KHUNG NHỎ
                    df_analyze = market_buffer.get_dataframe(symbol, tf_micro)
                    
                    if not df_analyze.empty:
                        # Mớm đúng cái trend vĩ mô tương ứng vào để chiến thuật ra quyết định
                        analysis = tech_engine.evaluate_live(df_analyze, macro_trend=current_macro_trend)
                        
                        # Cải tiến: Không 'continue' ở đây. Nếu analysis rỗng, ta vẫn cần 
                        # gọi broadcast_radar để xóa tín hiệu cũ trong Matrix và Frontend.
                        
                        current_price = float(df_analyze.iloc[-1]['close'])
                        current_time = int(df_analyze.iloc[-1]['time'].timestamp()) if hasattr(df_analyze.iloc[-1]['time'], 'timestamp') else int(df_analyze.iloc[-1]['time'])
                        
                        # Lọc bỏ các tín hiệu đã quá vùng hiệu quả (Price Pruning)
                        valid_analysis = [a for a in analysis if not self._is_signal_out_of_bounds(a, current_price)]
                        
                        # Cập nhật Matrix và thông báo cho Frontend
                        await self.broadcast_radar(symbol, tf_micro, valid_analysis, current_time)

                        valid_signals = [a for a in valid_analysis if a.get("signal") != "NEUTRAL"]
                        
                        if valid_signals:
                            # Chọn chiến thuật có điểm số (score) uy tín nhất để vào lệnh
                            # Nếu điểm bằng nhau, nó sẽ ưu tiên chiến thuật quét được đầu tiên
                            best_analysis = sorted(valid_signals, key=lambda x: x.get("score", 0), reverse=True)[0]
                            
                            bot_engine.receive_alpha_signal(symbol, tf_micro, best_analysis, current_time, current_price)

                            #print(f"🔥 LỆNH ẢO [{symbol} - {tf_micro}] từ {best_analysis['strategy_name']}: {best_analysis['signal']} (Score: {best_analysis['score']})")
                        
                            await bot_engine.process_tick(symbol, current_price, current_time)
                except Exception as e:
                    print(f"Error {symbol} {tf_micro}: {e}")
    
    def _is_signal_out_of_bounds(self, analysis, current_price):
        """Kiểm tra xem giá hiện tại đã vượt quá SL hoặc TP của tín hiệu chưa để loại bỏ vùng thừa"""
        sig = analysis.get("signal")
        sl = analysis.get("suggested_sl") or analysis.get("sl")
        tp = analysis.get("suggested_tp") or analysis.get("tp")
        
        if not sig or sig == "NEUTRAL": return False
        
        try:
            price = float(current_price)
            if sig == "BUY":
                if tp and price >= float(tp): return True # Đã đạt mục tiêu
                if sl and price <= float(sl): return True # Đã gãy vùng mua
            elif sig == "SELL":
                if tp and price <= float(tp): return True
                if sl and price >= float(sl): return True
        except:
            pass
        return False

    def _prune_stale_radar(self):
        """Dọn dẹp các tín hiệu đã quá cũ (hơn 3 cây nến) khỏi Matrix RAM"""
        now = time.time()
        tf_seconds = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
        
        for sym in list(self.radar_matrix.keys()):
            for tf in list(self.radar_matrix[sym].keys()):
                results = self.radar_matrix[sym][tf]
                if not results:
                    del self.radar_matrix[sym][tf]
                    continue
                
                # Check timestamp của bản tin (Dùng ts của item đầu tiên)
                last_ts = results[0].get("timestamp", 0)
                limit = tf_seconds.get(tf, 300) * 3
                
                if (now - last_ts) > limit:
                    del self.radar_matrix[sym][tf]
            
            if not self.radar_matrix[sym]:
                del self.radar_matrix[sym]

    async def broadcast_radar(self, symbol, tf, analyses, current_time):
        client_symbol = clean_symbol_for_client(symbol)
        formatted_data = [ 
            {
                "strategy_name": a.get("strategy_name", "Unknown"),
                "signal": a.get("signal", "NEUTRAL"),
                "score": a.get("score", 50),
                "reason": a.get("reason", ""),
                "sl": a.get("suggested_sl", ""),
                "tp": a.get("suggested_tp", ""),
                "timestamp": current_time # Lưu lại để tính toán độ trễ (stale)
            } for a in analyses
        ]
        if symbol not in self.radar_matrix:
            self.radar_matrix[symbol] = {}
        self.radar_matrix[symbol][tf] = formatted_data

        radar_payload = {
            "type": "RADAR_UPDATE",
            "symbol": client_symbol, 
            "tf": tf,
            "data": formatted_data
        }
        await ws_manager.broadcast(radar_payload)
