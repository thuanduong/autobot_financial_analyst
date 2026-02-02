# api/routes.py
from fastapi import APIRouter, Request, Body, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState
from fastapi.templating import Jinja2Templates
from database.repository import TradeRepo
from database.chart_repo import ChartRepo
from core.user.portfolio import PortfolioManager
from core.data_provider.mt5_provider import MT5Provider # Import MT5
from core.engine.scanner import MarketScanner
from pydantic import BaseModel
import json
import asyncio
import time
import MetaTrader5 as mt5

router = APIRouter()
templates = Jinja2Templates(directory="templates")
repo = TradeRepo()
mt5_service = MT5Provider()
chart_repo = ChartRepo()

# Biến global scanner sẽ được inject từ main.py
scanner_instance = None

def set_scanner_instance(scanner):
    global scanner_instance
    scanner_instance = scanner
    print("✅ Scanner injected into Routes")

# --- MODELS ---
class OrderRequest(BaseModel):
    username: str
    symbol: str
    action: str  # BUY hoặc SELL
    volume: float = 0.1

class CloseOrderRequest(BaseModel):
    order_id: int
    username: str

# --- PAGES ---
@router.get("/")
@router.get("/radar")
@router.get("/terminal")
async def app_entry(request: Request):
    # Luôn trả về app.html (Single Page App)
    return templates.TemplateResponse("app.html", {
        "request": request, 
        "page_name": "app" 
    })

# --- API DỮ LIỆU (JSON) ---

# 1. API Test kết nối (Debug)
@router.get("/api/ping")
def ping():
    return {"status": "ok", "message": "Pong!"}

@router.get("/api/scan-results")
def get_scan_results(tf: str = Query("M5")):
    if not scanner_instance:
        return {"status": "Starting...", "data": {}}
    
    return {
        "status": scanner_instance.market_status,
        "data": scanner_instance.latest_scan.get(tf, {})
    }


# 3. API Lấy danh sách User
@router.get("/api/users")
def get_users():
    users = repo.get_all_users()
    # Convert Row object sang dict
    return [{"username": u['username'], "balance": u['balance']} for u in users]


# 4. ĐẶT LỆNH MANUAL
@router.post("/api/trade")
def place_trade(order: OrderRequest):
    # 1. Check user
    if not repo.get_user(order.username):
        repo.create_user(order.username)

    pm = PortfolioManager(order.username)
    
    # 2. Lấy giá thị trường
    current_price = 0
    if scanner_instance and order.symbol in scanner_instance.latest_scan:
        current_price = scanner_instance.latest_scan[order.symbol]['price']
    
    # Nếu Scanner chưa quét ra giá, thử gọi MT5 trực tiếp (Fallback)
    if current_price == 0:
        # Import cục bộ để tránh vòng lặp import
        from core.data_provider.mt5_provider import MT5Provider
        mt5 = MT5Provider()
        current_price = mt5.get_price(order.symbol)

    if current_price == 0:
        return {"status": "error", "msg": "Không lấy được giá thị trường!"}

    # 3. XỬ LÝ ACTION
    if order.action == "CLOSE":
        # --- Logic Đóng Lệnh ---
        result = pm.close_position(order.symbol, current_price)
        if result:
            return {"status": "success", "msg": f"Đã đóng lệnh {order.symbol}. Giá: {current_price}"}
        else:
            return {"status": "error", "msg": "Không tìm thấy lệnh mở để đóng!"}
    else:
        # --- Logic Mở Lệnh (BUY/SELL) ---
        pm.open_position(order.symbol, order.action, current_price, leverage=100)
        return {"status": "success", "msg": f"Đã vào lệnh {order.action} {order.symbol}"}

# 5. LẤY LỊCH SỬ LỆNH CỦA USER
@router.get("/api/orders/{username}")
def get_orders(username: str):
    try:
        # Gọi hàm từ repository
        orders = repo.get_user_orders(username)
        return {"status": "success", "data": orders}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


@router.post("/api/close-order")
def close_specific_order(req: CloseOrderRequest):
    try:
        print(f"📩 Yêu cầu đóng lệnh #{req.order_id} từ {req.username}")

        # 1. Tìm lệnh trong DB
        order = repo.get_order_by_id(req.order_id)
        if not order: 
            return {"status": "error", "msg": "Lệnh không tồn tại trong DB"}
        
        if order['status'] != 'OPEN': 
            return {"status": "error", "msg": "Lệnh này đã đóng rồi"}

        # 2. Lấy giá hiện tại
        # Ưu tiên lấy từ Scanner (RAM) cho nhanh
        current_price = 0
        if scanner_instance and order['symbol'] in scanner_instance.latest_scan:
            current_price = scanner_instance.latest_scan[order['symbol']]['price']
        
        # Nếu không có thì lấy trực tiếp từ MT5
        if current_price == 0:
            current_price = mt5_service.get_price(order['symbol'])
        
        # Vẫn 0 thì báo lỗi
        if current_price == 0:
             return {"status": "error", "msg": f"Không lấy được giá {order['symbol']} từ MT5"}

        # 3. Tính PnL (Đảm bảo ép kiểu float để tránh lỗi cộng trừ chuỗi)
        entry = float(order['entry_price'])
        vol = float(order['volume'])
        price = float(current_price)
        
        pnl = 0.0
        if order['type'] == 'BUY':
            pnl = (price - entry) * vol
        else: # SELL
            pnl = (entry - price) * vol
            
        # Contract Size (Vàng * 100)
        if "XAU" in order['symbol']:
            pnl = pnl * 100
            
        # 4. Update DB
        repo.close_order_by_id(req.order_id, price, pnl)
        
        return {"status": "success", "msg": f"Đã đóng lệnh #{req.order_id}. PnL: {pnl:.2f}$"}

    except Exception as e:
        # IN LỖI RA TERMINAL ĐỂ DEBUG
        import traceback
        traceback.print_exc()
        return {"status": "error", "msg": f"Lỗi Server: {str(e)}"}

@router.get("/api/stats/{username}")
def get_user_stats(username: str):
    # 1. Lấy thông tin User
    user = repo.get_user(username)
    if not user:
        return {"balance": 0, "equity": 0, "pnl": 0, "active_count": 0}
    
    # 2. Lấy danh sách lệnh OPEN
    orders = repo.get_user_orders(username)
    active_orders = [o for o in orders if o['status'] == 'OPEN']
    
    # 3. Tính Floating PnL (Lời lỗ tạm tính)
    floating_pnl = 0.0
    
    for o in active_orders:
        # Lấy giá hiện tại (Ưu tiên Scanner -> MT5)
        current_price = 0
        if scanner_instance and o['symbol'] in scanner_instance.latest_scan:
            current_price = scanner_instance.latest_scan[o['symbol']]['price']
        
        if current_price == 0:
            current_price = mt5_service.get_price(o['symbol'])
            
        # Nếu vẫn ko lấy được giá thì bỏ qua lệnh này
        if current_price == 0: continue
            
        # Tính PnL
        entry = float(o['entry_price'])
        vol = float(o['volume'])
        price = float(current_price)
        
        pnl = 0
        if o['type'] == 'BUY':
            pnl = (price - entry) * vol
        else:
            pnl = (entry - price) * vol
            
        if "XAU" in o['symbol']:
            pnl *= 100
            
        floating_pnl += pnl

    # 4. Tổng hợp
    balance = float(user['balance'])
    equity = balance + floating_pnl
    
    return {
        "balance": round(balance, 2),
        "equity": round(equity, 2),
        "pnl": round(floating_pnl, 2),
        "active_count": len(active_orders)
    }

# --- API WEBSOCKET: CHART STREAMING ---
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    current_symbol = "XAUUSD.sml" 
    current_timeframe = "M5"

    try:
        while True:
            # --- KIỂM TRA TRẠNG THÁI TRƯỚC KHI CHẠY VÒNG LẶP ---
            if websocket.client_state == WebSocketState.DISCONNECTED:
                break

            # 1. LẮNG NGHE YÊU CẦU TỪ CLIENT (Non-blocking)
            try:
                # Chờ tin nhắn trong 0.5s
                data_text = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                msg = json.loads(data_text)
                
                if msg.get('type') == 'SWITCH_SYMBOL':
                    current_symbol = msg.get('symbol')
                    current_timeframe = msg.get('timeframe', 'M5')
                    
                    # LOGIC LẤY DATA (MT5 -> DB)
                    if scanner_instance:
                        # A. Gọi MT5 trước
                        df = scanner_instance.mt5.get_data(current_symbol, n=500, timeframe=current_timeframe)
                        
                        # B. Fallback DB
                        if df is None or df.empty:
                            df = scanner_instance.repo.get_history(current_symbol, limit=500, timeframe=current_timeframe)
                        
                        # C. Gửi Data (Kiểm tra kết nối trước khi gửi)
                        if websocket.client_state == WebSocketState.CONNECTED:
                            if df is not None and not df.empty:
                                candles = []
                                for _, row in df.iterrows():
                                    raw_time = row['time']
                                    ts = int(raw_time.timestamp()) if hasattr(raw_time, 'timestamp') else int(raw_time)
                                    candles.append({
                                        "time": ts, 
                                        "open": row['open'], "high": row['high'], 
                                        "low": row['low'], "close": row['close']
                                    })
                                
                                await websocket.send_json({
                                    "type": "HISTORY", "data": candles, 
                                    "symbol": current_symbol, "timeframe": current_timeframe
                                })
                            else:
                                await websocket.send_json({"type": "ERROR", "message": "No Data"})

            except asyncio.TimeoutError:
                pass # Hết 0.5s mà không có lệnh switch thì chạy tiếp xuống phần Update giá
            except WebSocketDisconnect:
                print("⚠️ Client disconnected during receive")
                break # Thoát vòng lặp ngay

            # 2. GỬI GIÁ REALTIME (TICK UPDATE)
            if scanner_instance:
                try:
                    # Kiểm tra kết nối lần nữa trước khi gửi tick
                    if websocket.client_state == WebSocketState.DISCONNECTED: break

                    tick = mt5.symbol_info_tick(current_symbol)
                    if tick:
                        price = tick.last
                        ts = int(tick.time)
                        await websocket.send_json({
                            "type": "UPDATE", 
                            "candle": {"time": ts, "close": price}, 
                            "symbol": current_symbol
                        })
                except (WebSocketDisconnect, RuntimeError):
                    print("⚠️ Client disconnected during send")
                    break # Thoát vòng lặp
                except Exception as e:
                    pass # Lỗi lặt vặt khi gửi tick thì bỏ qua, không crash app

    except Exception as e:
        print(f"❌ WS Critical Error: {e}")
    finally:
        print("🔌 WebSocket Closed cleanly")

