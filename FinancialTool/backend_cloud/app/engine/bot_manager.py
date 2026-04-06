# core/engine/bot_manager.py
from datetime import datetime
from backend_cloud.app.api.websocket import ws_manager
from backend_cloud.app.database.analyze_models import SignalHistory
from backend_cloud.app.database.analyze_repo import AnalyzeRepo
from backend_cloud.app.core.utils import clean_symbol_for_client, resolve_broker_symbol
from backend_cloud.app.services.news_feed import news_service

class BotManager:
    def __init__(self):
        # Lưu trữ các tín hiệu đang được "đưa vào tầm ngắm" nhưng chưa khớp lệnh
        self.watch_list = {} # VD: { "XAUUSD": {"type": "SELL", "zone_high": 1050, "zone_low": 1000} }
        self.last_closed_time = {}
        self.tf_seconds = {
            "M1": 60,
            "M5": 300,
            "M15": 900,
            "M30": 1800,
            "H1": 3600,
            "H4": 14400,
            "D1": 86400
        }
        self._analyze_repo: AnalyzeRepo = None

    def setAnalyzeRepo(self, analyze_repo: AnalyzeRepo):
        self._analyze_repo = analyze_repo

    def receive_alpha_signal(self, symbol: str, tf: str, analysis: dict, current_time: int, current_price: float):
        """
        Nhận tín hiệu từ Radar. Đánh giá xem có đưa vào danh sách Rình mồi không.
        """
        strategy_id = analysis.get("strategy_name")
        order_key = f"{symbol}_{tf}_{strategy_id}"

        if order_key in self.watch_list and self.watch_list[order_key]["status"] == "IN_POSITION":
            return
        
        if order_key in self.last_closed_time:
            seconds_passed = current_time - self.last_closed_time[order_key]
            cooldown_period = 300
            if seconds_passed < cooldown_period:
                return
        
        # KIỂM TRA TIN TỨC (NEWS FILTER)
        news_alert = news_service.check_high_impact_news(symbol)
        if news_alert["has_news"]:
            print(f"⚠️ BỎ QUA TÍN HIỆU {symbol}: Đang có tin mạnh '{news_alert['title']}' ({news_alert['time_diff_min']}m)")
            return
            
        # Giả sử chỉ lấy tín hiệu điểm cao (> 80)
        if analysis.get("score", 0) >= 80 and analysis.get("signal") in ["BUY", "SELL"]:
            print(f"👀 BotManager đưa {symbol} vào tầm ngắm: Cần canh giá tốt để {analysis['signal']}")
            
            # LẤY VÙNG ENTRY TỐI ƯU (Tránh khớp lệnh lưng chừng)
            # Ưu tiên lấy vùng từ Analysis, nếu không có thì tạo buffer +/- 0.05% quanh giá entry
            entry_zone_min = analysis.get("entry_zone_min")
            entry_zone_max = analysis.get("entry_zone_max")
            
            if entry_zone_min is None or entry_zone_max is None:
                base_entry = analysis.get("entry_price") or current_price
                # Tạo một vùng hẹp để giá phải thực sự "chạm" vào mới khớp
                entry_zone_min = base_entry * 0.9995
                entry_zone_max = base_entry * 1.0005
            
            self.watch_list[order_key] = {
                "symbol": symbol,
                "tf": tf,
                "signal": analysis["signal"],
                "strategy": strategy_id,
                "zone_min": entry_zone_min,
                "zone_max": entry_zone_max,
                "target_tp": analysis.get("suggested_tp"),
                "target_sl": analysis.get("suggested_sl"),
                "status": "WAITING_FOR_PRICE", # Trạng thái đang rình
                "created_at": current_time
            }

    async def process_tick(self, symbol: str, current_price: float, current_time: int):
        """
        Hàm này được gọi mỗi giây khi giá chạy. 
        Nhiệm vụ: Canh me xem giá đã vào Vùng tối ưu chưa để bóp cò!
        """
        for order_key in list(self.watch_list.keys()):
            order = self.watch_list[order_key]
            if order["symbol"] != symbol:
                continue
            #print(f"STATUS {order["status"]}")
            # ----------------------------------------------------
            # TRẠNG THÁI 1: ĐANG RÌNH MỒI (Chờ giá hồi về vùng đẹp)
            # ----------------------------------------------------
            if order["status"] == "WAITING_FOR_PRICE":
                # 1. KIỂM TRA HẾT HẠN (Sau 3 cây nến mà chưa khớp thì bỏ)
                candle_duration = self.tf_seconds.get(order["tf"], 300)
                if (current_time - order["created_at"]) > (candle_duration * 3):
                    print(f"⌛ [CANCEL] {order_key}: Quá thời gian chờ (Hết hạn sau 3 nến)")
                    del self.watch_list[order_key]
                    continue

                # 2. KIỂM TRA GIÁ CHẠY THẲNG ĐẾN TP (Missed Opportunity)
                # Nếu giá đã chạm TP trước khi hồi về vùng Entry -> Setup không còn giá trị
                is_missed = False
                if order["signal"] == "BUY" and current_price >= order["target_tp"]:
                    is_missed = True
                elif order["signal"] == "SELL" and current_price <= order["target_tp"]:
                    is_missed = True
                
                if is_missed:
                    print(f"🚫 [CANCEL] {order_key}: Giá đã chạm TP trước khi khớp entry (Bỏ lỡ cơ hội)")
                    del self.watch_list[order_key]
                    continue

                # 3. KIỂM TRA GIÁ CHẠM SL TRƯỚC (Setup hỏng - Bắt dao rơi thất bại)
                is_failed = False
                if order["signal"] == "BUY" and current_price <= order["target_sl"]:
                    is_failed = True
                elif order["signal"] == "SELL" and current_price >= order["target_sl"]:
                    is_failed = True
                
                if is_failed:
                    print(f"💀 [CANCEL] {order_key}: Giá đã chạm SL trước khi khớp entry (Setup hỏng)")
                    del self.watch_list[order_key]
                    continue

                # 4. KIỂM TRA ĐIỀU KIỆN KHỚP LỆNH (Chỉ khớp khi giá nằm TRONG vùng Entry)
                executed = False
                if order["zone_min"] <= current_price <= order["zone_max"]:
                    executed = True
                    
                if executed:
                    print(f"🔫 BÓP CÒ [{order['strategy']}]: Khớp lệnh {order['signal']} tại {current_price}!")
                    order["status"] = "IN_POSITION"
                    order["entry_price"] = current_price
                    order["open_time"] = current_time
                    
                    # Gọi hàm lưu DB và bắn Socket Mũi tên Vàng (PENDING)
                    await self.execute_paper_trade(order_key, order)

            # ----------------------------------------------------
            # TRẠNG THÁI 2: LỆNH ĐANG CHẠY (Canh chốt lời/cắt lỗ)
            # ----------------------------------------------------
            elif order["status"] == "IN_POSITION":
                closed = False
                outcome = ""
                
                # Logic cho lệnh BUY
                if order["signal"] == "BUY":
                    if current_price >= order["target_tp"]:
                        closed = True; outcome = "WIN"
                    elif current_price <= order["target_sl"]:
                        closed = True; outcome = "LOSS"
                        
                # Logic cho lệnh SELL
                elif order["signal"] == "SELL":
                    if current_price <= order["target_tp"]:
                        closed = True; outcome = "WIN"
                    elif current_price >= order["target_sl"]:
                        closed = True; outcome = "LOSS"

                # NẾU CHẠM SL HOẶC TP -> TIẾN HÀNH ĐÓNG LỆNH
                if closed:
                    # Tính toán Lời/Lỗ (PnL)
                    pnl = (current_price - order["entry_price"]) if order["signal"] == "BUY" else (order["entry_price"] - current_price)
                    
                    print(f"💰 CHỐT SỔ [{order['strategy']} - {symbol}]: {outcome} | PnL: {pnl:.2f} giá")
                    
                    # Gọi hàm cập nhật DB (Đổi PENDING thành WIN/LOSS) và XÓA khỏi RAM
                    await self.close_paper_trade(order_key, order, current_price, current_time, outcome, pnl)
                    
                    # Xóa lệnh khỏi bộ nhớ Rình mồi để đón chu kỳ phân tích mới
                    del self.watch_list[order_key]

    async def execute_paper_trade(self, order_key: str, order: dict):
        """Lưu lệnh PENDING vào DB khi giá chạm vùng Rình mồi"""
        db = self._analyze_repo.AnalyzeSessionLocal()
        try:
            new_signal = SignalHistory(
                strategy_id=order["strategy"],
                symbol=order["symbol"],
                timeframe=order["tf"],
                timestamp=order["open_time"],
                signal=order["signal"],
                score=order.get("score", 80),
                entry_price=order["entry_price"],
                suggested_sl=order["target_sl"],
                suggested_tp=order["target_tp"],
                reason=f"Giá chạm vùng rình mồi. Min: {order.get('zone_min')}, Max: {order.get('zone_max')}",
                outcome="PENDING" # Đánh dấu lệnh đang chạy
            )
            db.add(new_signal)
            db.commit()
            
            # Bắn Socket lên Frontend để vẽ Mũi tên Vàng (Lệnh ảo đang chạy)
            client_symbol = resolve_broker_symbol(order["symbol"])
            
            await ws_manager.broadcast({
                "type": "SIGNAL_UPDATE",
                "symbol": client_symbol,
                "tf": order["tf"],
                "data": {
                    "time": order["open_time"],
                    "signal": order["signal"],
                    "strategy_id": order["strategy"],
                    "sl": order["target_sl"],
                    "tp": order["target_tp"],
                    "outcome": "PENDING"
                }
            })
        except Exception as e:
            db.rollback()
            print(f"❌ Lỗi ghi mở lệnh {order_key}: {e}")
        finally:
            db.close()

    async def close_paper_trade(self, order_key: str, order: dict, close_price: float, close_time: int, outcome: str, pnl: float):
        """Cập nhật lệnh thành WIN/LOSS khi giá chạm SL/TP"""
        self.last_closed_time[order_key] = close_time
        db = self._analyze_repo.AnalyzeSessionLocal()
        try:
            # Tìm lại đúng cái lệnh PENDING hồi nãy để cập nhật
            existing_signal = db.query(SignalHistory).filter(
                SignalHistory.symbol == order["symbol"],
                SignalHistory.timeframe == order["tf"],
                SignalHistory.timestamp == order["open_time"],
                SignalHistory.strategy_id == order["strategy"]
            ).first()

            if existing_signal:
                existing_signal.outcome = outcome
                existing_signal.close_price = close_price
                existing_signal.close_time = close_time
                existing_signal.realized_pnl = pnl
                db.commit()

                # Bắn Socket báo Frontend cập nhật màu Mũi tên (Từ Vàng sang Xanh/Đỏ)
                client_symbol = resolve_broker_symbol(order["symbol"])
                await ws_manager.broadcast({
                    "type": "SIGNAL_UPDATE",
                    "symbol": client_symbol,
                    "tf": order["tf"],
                    "data": {
                        "time": order["open_time"],  # Vẫn dùng open_time để Chart tìm đúng mũi tên cũ
                        "signal": order["signal"],
                        "strategy_id": order["strategy"],
                        "sl": order["target_sl"],
                        "tp": order["target_tp"],
                        "outcome": outcome,          # "WIN" hoặc "LOSS"
                        "pnl": round(pnl, 2)
                    }
                })
            else:
                print(f"⚠️ Không tìm thấy lệnh PENDING trong DB để chốt: {order_key}")
                
        except Exception as e:
            db.rollback()
            print(f"❌ Lỗi cập nhật chốt lệnh {order_key}: {e}")
        finally:
            db.close()
    
    def sync_pending_orders(self):
        """Đồng bộ các lệnh chưa chốt (PENDING) từ Database lên RAM khi khởi động"""
        print("🔄 [BotManager] Đang đồng bộ các lệnh PENDING từ Database...")
        db = self._analyze_repo.AnalyzeSessionLocal()
        try:
            # Tìm tất cả lệnh đang treo
            pending_signals = db.query(SignalHistory).filter(
                SignalHistory.outcome == "PENDING"
            ).all()

            count = 0
            for s in pending_signals:
                # Tái tạo lại khóa y hệt lúc tạo lệnh
                order_key = f"{s.symbol}_{s.timeframe}_{s.strategy_id}"
                
                # Phục hồi bộ nhớ cho Bot
                self.watch_list[order_key] = {
                    "symbol": s.symbol,
                    "tf": s.timeframe,
                    "strategy": s.strategy_id,
                    "signal": s.signal,
                    "entry_price": s.entry_price,
                    "open_time": s.timestamp,
                    "target_sl": s.suggested_sl,
                    "target_tp": s.suggested_tp,
                    "status": "IN_POSITION" # Quan trọng: Đánh dấu là đang ôm lệnh để quét SL/TP
                }
                count += 1
                
            print(f"✅ [BotManager] Đã khôi phục thành công {count} lệnh đang chạy vào bộ nhớ!")
        except Exception as e:
            print(f"❌ [BotManager] Lỗi đồng bộ lệnh: {e}")
        finally:
            db.close()

# Khởi tạo Singleton
bot_engine = BotManager()