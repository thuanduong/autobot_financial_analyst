import asyncio
import json
import math
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pydantic import BaseModel
import pandas as pd
import numpy as np 

# IMPORT COMPONENTS
from core.data_service import DataService
from core.strategy_manager import StrategyManager
from core.user_manager import UserManager
from core.portfolio_manager import PortfolioManager

app = FastAPI()

# Mount thư mục static (CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- KHỞI TẠO 3 ENGINE DỮ LIỆU RIÊNG BIỆT ---
# 1. Dùng cho Biểu đồ (Linh hoạt theo user chọn)
data_service_chart = DataService(symbol="GC=F", default_timeframe="15m")

# 2. Dùng cho Chiến thuật (Cố định khung nhỏ - Entry)
data_service_main = DataService(symbol="GC=F", default_timeframe="15m")

# 3. Dùng cho Xu hướng (Cố định khung lớn - Filter)
# Lưu ý: Yahoo miễn phí đôi khi khung 4h bị lỗi, nên dùng 1h cho ổn định
data_service_trend = DataService(symbol="GC=F", default_timeframe="1h") 

# Global user manager
user_db = UserManager()
active_portfolios = {}

strategy_manager = StrategyManager()
#portfolio = PortfolioManager()

# --- HÀM PHỤ TRỢ ---
def clean_data_for_json(data):
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data): return None
        return float(data)
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        if np.isnan(data): return None
        return float(data)
    elif pd.isna(data):
        return None
    else:
        return data

def get_portfolio(username: str):
    """Lấy hoặc tạo mới Portfolio cho user"""
    if not username: return None
    if username not in active_portfolios:
        print(f"📂 Loading portfolio for: {username}")
        active_portfolios[username] = PortfolioManager(username)
    return active_portfolios[username]

# --- MODELS ---
class TimeframeRequest(BaseModel):
    timeframe: str

class OrderRequest(BaseModel):
    action: str
    strategy: str

class SymbolRequest(BaseModel):
    symbol: str

class SettingsRequest(BaseModel):
    capital: float
    leverage: float
    bet_amount: float

class GlobalSettingRequest(BaseModel):
    capital: float

class StrategySettingRequest(BaseModel):
    strategy_name: str
    leverage: float
    bet_amount: float

class LoginRequest(BaseModel):
    username: str
    password: str

# --- API ---
@app.get("/")
async def get():
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception:
        return HTMLResponse("<h1>Lỗi: Không tìm thấy file templates/index.html</h1>")

@app.post("/api/timeframe")
async def set_timeframe(req: TimeframeRequest):
    # Chỉ đổi khung của Chart, không ảnh hưởng AI
    if data_service_chart.change_timeframe(req.timeframe):
        return {"status": "success"}
    return {"status": "error"}

@app.post("/api/symbol")
async def set_symbol(req: SymbolRequest):
    # Đổi Symbol thì phải đổi cả 3 ông
    s1 = data_service_chart.change_symbol(req.symbol)
    s2 = data_service_main.change_symbol(req.symbol)
    s3 = data_service_trend.change_symbol(req.symbol)
    
    # Dùng 'and' thay vì '&' cho boolean logic chuẩn Python
    if s1 and s2 and s3:
        # Reset ví tiền để tránh lỗi tính toán giá
        global portfolio
        portfolio = PortfolioManager() 
        return {"status": "success", "msg": f"Đã chuyển toàn bộ hệ thống sang {req.symbol}"}
    
    return {"status": "error", "msg": "Mã không tìm thấy hoặc lỗi Yahoo"}

@app.post("/api/trade")
async def manual_trade(order: OrderRequest, x_user: Optional[str] = Header(None, alias="X-User")):
    if not x_user: 
        print("❌ Lỗi: API Trade thiếu Header X-User")
        return {"status": "error", "msg": "Chưa đăng nhập"}
    
    portfolio = get_portfolio(x_user)
    if not portfolio:
        return {"status": "error", "msg": "Không load được Portfolio"}
    
    print(f"{portfolio.username} trade")
    # Lấy giá từ Chart engine (Realtime nhất để khớp lệnh)
    df = data_service_chart.get_data()
    if df.empty: return {"status": "error", "msg": "No Data"}
    
    price = df.iloc[-1]['close']
    time = str(df.iloc[-1]['time'])
    
    if order.strategy != "ALL":
        signals = {order.strategy: order.action} 
        portfolio.execute_all(signals, price, time)
    
    return {"status": "success", "executed_price": price}

@app.post("/api/settings")
async def update_settings(req: SettingsRequest, x_user: Optional[str] = Header(None, alias="X-User")):
    if not x_user: return {"status": "error", "msg": "Chưa đăng nhập"}
    portfolio = get_portfolio(x_user)
    print(f"⚙️ UPDATE SETTINGS: Vốn {req.capital}$ | Đòn bẩy x{req.leverage} | Đánh {req.bet_amount}$")
    portfolio.update_settings(req.capital, req.leverage, req.bet_amount)
    return {"status": "success", "msg": "Đã cập nhật thông số tài chính"}

@app.post("/api/setting/global")
async def update_global_capital(req: GlobalSettingRequest, x_user: Optional[str] = Header(None, alias="X-User")):
    if not x_user: return {"status": "error", "msg": "Auth Failed"}
    portfolio = get_portfolio(x_user)
    print(f"💰 Global Capital Reset: {req.capital}$")
    portfolio.set_global_capital(req.capital)
    return {"status": "success"}

@app.post("/api/setting/strategy")
async def update_strategy_config(req: StrategySettingRequest, x_user: Optional[str] = Header(None, alias="X-User")):
    if not x_user: return {"status": "error", "msg": "Auth Failed"}
    portfolio = get_portfolio(x_user)
    # print(f"⚙️ Config {req.strategy_name}: x{req.leverage} | {req.bet_amount}$")
    portfolio.set_strategy_config(req.strategy_name, req.leverage, req.bet_amount)
    return {"status": "success"}

@app.post("/api/login")
async def login(req: LoginRequest):
    if user_db.login(req.username, req.password):
        return {"status": "success", "username": req.username}
    return {"status": "error", "msg": "Sai mật khẩu"}

@app.post("/api/register")
async def register(req: LoginRequest):
    if user_db.register(req.username, req.password):
        return {"status": "success", "username": req.username}
    return {"status": "error", "msg": "Trùng tên đăng nhập"}

@app.post("/api/reset_data")
async def reset_data(req: LoginRequest): # Tái sử dụng model LoginRequest để lấy username
    # 1. Xóa DB
    user_db.reset_user_data(req.username)
    # 2. Xóa RAM
    if req.username in active_portfolios:
        del active_portfolios[req.username]
    return {"status": "success", "msg": "Đã reset toàn bộ dữ liệu!"}

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"✅ Client connected")
    username = "Guest"

    try:
        import asyncio
        try:
            init_msg = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        except asyncio.TimeoutError:
            print("⚠️ Client không gửi Login -> Ngắt kết nối.")
            await websocket.close()
            return

        if init_msg.get("type") != "LOGIN":
            print("⚠️ Gói tin đầu tiên không phải LOGIN -> Ngắt kết nối.")
            await websocket.close()
            return
                
        username = init_msg.get("username")
        print(f"✅ WS Authenticated: {username}")
        
        portfolio = get_portfolio(username)
        
        # 1. Gửi lịch sử (Lấy từ Chart Engine)
        df_init = data_service_chart.get_data()
        if not df_init.empty:
            history = []
            for _, row in df_init.iterrows():
                history.append({
                    "time": int(pd.to_datetime(row['time']).timestamp()),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close'])
                })
            await websocket.send_json({"type": "HISTORY", "data": history})

        # 2. Loop Realtime
        while True:
            if websocket.client_state.name == "DISCONNECTED":
                break
            
            # Lấy dữ liệu từ cả 3 nguồn
            df_chart = data_service_chart.get_data()  # Để vẽ nến
            df_main = data_service_main.get_data()    # Để AI tính Entry
            df_trend = data_service_trend.get_data()  # Để AI tính Xu hướng
            
            # Cần đảm bảo CẢ 3 đều có dữ liệu mới chạy tiếp
            if not df_chart.empty and not df_main.empty and not df_trend.empty:
                
                # Giá hiện tại (Lấy theo Chart Engine cho khớp hiển thị)
                current_price = float(df_chart.iloc[-1]['close'])
                current_time = str(df_chart.iloc[-1]['time'])
                
                # --- PHÂN TÍCH ĐA KHUNG ---
                # Truyền data Main và Trend vào Strategy
                analysis_details, signals = strategy_manager.analyze_all(df_main, df_trend)
                
                # --- KHỚP LỆNH ---
                portfolio.execute_all(signals, current_price, current_time)
                summary = portfolio.get_summary(current_price)
                
                # --- GỬI VỀ FRONTEND ---
                # Nến để vẽ (Lấy từ Chart Engine)
                last = df_chart.iloc[-1]
                candle_data = {
                    "time": int(pd.to_datetime(last['time']).timestamp()),
                    "open": float(last['open']),
                    "high": float(last['high']),
                    "low": float(last['low']),
                    "close": float(last['close'])
                }
                
                payload = {
                    "type": "UPDATE",
                    "symbol": data_service_chart.symbol,
                    "timeframe": data_service_chart.timeframe, # Gửi timeframe hiện tại của chart
                    "candle": candle_data,
                    "strategies": clean_data_for_json(summary),
                    "details": clean_data_for_json(analysis_details)
                }
                
                await websocket.send_json(payload)
            else:
                print("⚠️ Đang đồng bộ dữ liệu đa khung...")
            
            await asyncio.sleep(3) # Check mỗi 3s

    except WebSocketDisconnect:
        print("👋 Client Disconnected")
    except Exception as e:
        print("❌ WS Error:")
        traceback.print_exc()