from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Body, Query, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

# Import các Core
from backend_cloud.app.services.mt5_feed import mt5_feed
from backend_cloud.app.database.chart_repo import ChartRepo
from backend_cloud.app.core.globals import global_repo, global_scanner, global_analyze
from backend_cloud.app.core.virtual_broker import VirtualBroker
from backend_cloud.app.api.websocket import ws_manager
from backend_cloud.app.core.utils import resolve_broker_symbol
from backend_cloud.app.database.models import User
from backend_cloud.app.api.deps import get_current_user_ws

from backend_cloud.app.database.analyze_models import SignalHistory

# Init Router & Templates
router = APIRouter()
templates = Jinja2Templates(directory="backend_cloud/templates")

# Init Instances (Sẽ được Main inject vào hoặc dùng singleton)
# Ở đây dùng tạm singleton để đơn giản code demo
repo: ChartRepo = global_repo
scanner = global_scanner

# --- 1. WEB PAGES ---
@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Trang chủ hiển thị Chart và Bot"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/mobile", response_class=HTMLResponse)
async def mobile_page(request: Request):
    """Trang Mobile rút gọn"""
    return templates.TemplateResponse("mobile.html", {"request": request})

# --- 2. WEBSOCKET ENDPOINT ---
@router.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket, current_user: User = Depends(get_current_user_ws)):
    """
    Endpoint xử lý kết nối WebSocket.
    Lưu ý: Không kiểm tra User trong DB để tránh lỗi 403 với 'demo_user'.
    """
    try:
        client_id = str(current_user.id)
        await ws_manager.connect(websocket, client_id)
        
        while True:
            # Lắng nghe tin nhắn từ client (như ping/pong) để giữ connection
            await websocket.receive_text()

    except WebSocketDisconnect:
        if 'client_id' in locals():
            await ws_manager.disconnect(websocket, client_id)
    except Exception as e:
        print(f"📡 WebSocket Connection Error for User {current_user.id}: {e}")
        if 'client_id' in locals():
            await ws_manager.disconnect(websocket, client_id)


# API 1: Load mặc định khi mở trang (Lấy 200-500 nến)
@router.get("/api/chart/history/initial")
async def get_initial_history(
    symbol: str, 
    tf: str, 
    limit: int = Query(default=300, le=2000) # Mặc định 300 nến
):
    broker_symbol = resolve_broker_symbol(symbol)
    
    data = global_repo.get_recent_candles(broker_symbol, tf, limit)
    return data

# API 2: Load theo Range (Dùng cho Lazy Load khi cuộn chuột hoặc lấp Gap)
@router.get("/api/chart/history/range")
async def get_range_history(
    symbol: str, 
    tf: str, 
    from_time: int, # Unix Timestamp
    to_time: int    # Unix Timestamp
):
    """
    Frontend gọi API này khi người dùng cuộn về quá khứ.
    Ví dụ: Chart đang hiển thị tới 10:00, user cuộn thêm -> gọi API lấy 08:00 -> 10:00
    """
    broker_symbol = resolve_broker_symbol(symbol)
    data = global_repo.get_candles_in_range(broker_symbol, tf, from_time, to_time)
    return data


@router.get("/api/signals/history")
def get_historical_signals(
    symbol: str = Query(...), 
    tf: str = Query(...),
    from_time: Optional[int] = Query(None),
    to_time: Optional[int] = Query(None),
    limit: int = Query(200), 
    db: Session = Depends(global_analyze.get_analyze_db)
):    
    query = db.query(SignalHistory).filter(
        SignalHistory.symbol == symbol,
        SignalHistory.timeframe == tf
    )

    if from_time:
        query = query.filter(SignalHistory.timestamp >= from_time)
    if to_time:
        query = query.filter(SignalHistory.timestamp <= to_time)

    signals = query.order_by(SignalHistory.timestamp.desc()).limit(limit).all()

    signals_asc = list(reversed(signals))
    
    return {
        "status": "success",
        "data": [
            {
                "time": s.timestamp,
                "strategy_id": s.strategy_id, # Thêm trường này để Frontend lọc
                "signal": s.signal,
                "outcome": s.outcome,         # PENDING, WIN, LOSS
                "sl": s.suggested_sl,
                "tp": s.suggested_tp,
                "pnl": s.realized_pnl         # Lời/Lỗ thực tế
            } for s in signals_asc
        ]
    }