from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional

from backend_cloud.app.database.base import get_db
from backend_cloud.app.database.models import User, Order, OrderStatus, SymbolConfig, UserOrder
from backend_cloud.app.api.deps import get_current_user
from backend_cloud.app.schemas.trade import OrderCreate, OrderClose, SymbolConfigCreate, SymbolConfigUpdate
from backend_cloud.app.services.live_price import get_live_execution_price
from backend_cloud.app.core.utils import resolve_broker_symbol, clean_symbol_for_client
from backend_cloud.app.api.websocket import ws_manager
from backend_cloud.app.core.globals import global_analyze
# Import mt5 để tránh lỗi NameError trong các hàm history
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from backend_cloud.app.database.analyze_models import SignalHistory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trade", tags=["Trading Engine"])

@router.post("/order")
async def place_order(
    order_in: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API Xử lý Đặt lệnh chuẩn MT5"""
    wallet = current_user.wallet
    if not wallet:
        raise HTTPException(status_code=400, detail="Không tìm thấy ví tiền ảo.")

    broker_symbol = resolve_broker_symbol(order_in.symbol)

    # 1. Truy vấn Cấu hình của Symbol (Contract Size, Leverage)
    symbol_config = db.query(SymbolConfig).filter(SymbolConfig.symbol == broker_symbol).first()
    if symbol_config and not symbol_config.is_active:
         raise HTTPException(status_code=400, detail=f"Mã giao dịch {order_in.symbol} hiện đang bị vô hiệu hóa.")
    
    contract_size = symbol_config.contract_size if symbol_config else Decimal("1.0")
    leverage = symbol_config.base_leverage if symbol_config else 1

    # 2. BACKEND TỰ LẤY GIÁ THỊ TRƯỜNG HIỆN TẠI (Market Price)
    try:
        live_price_float = get_live_execution_price(broker_symbol, order_in.order_type)
        current_price = Decimal(str(live_price_float))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Báo giá thất bại: {str(e)}")

    # 3. Tính toán Ký quỹ (Margin) theo công thức MT5
    volume = Decimal(str(order_in.volume))
    
    # Công thức: (Volume * Contract_Size * Current_Price) / Leverage
    required_margin = (volume * contract_size * current_price) / Decimal(leverage)

    # 4. Kiểm tra sức chịu đựng của Ví
    if wallet.balance < required_margin:
        raise HTTPException(
            status_code=400, 
            detail=f"Ký quỹ không đủ. Cần ${required_margin:,.2f} để mở lệnh này."
        )

    try:
        # 5. LƯU LỆNH VỚI MỨC GIÁ ĐÃ CHỐT (open_price)
        new_order = Order(
            user_id=current_user.id,
            symbol=broker_symbol,
            order_type=order_in.order_type,
            volume=volume,
            open_price=current_price, # <--- Khóa chặt giá trị này vào DB
            status=OrderStatus.OPEN
        )
        db.add(new_order)

        # 6. Trừ tiền ký quỹ vào Balance (Tiền thực tế có thể rút)
        wallet.balance -= required_margin
        
        # Lưu vào DB (Transaction an toàn)
        db.commit()
        db.refresh(new_order)
        
        new_balance = float(wallet.balance)

        await ws_manager.send_personal_message(
            user_id=current_user.id,
            message={
                "type": "BALANCE_UPDATE", 
                "balance": new_balance,
                "message": f"Bạn vừa đặt lệnh {required_margin}$"
            }
        )

        return {
            "status": "success",
            "message": f"Khớp lệnh {order_in.order_type} {float(volume)} {order_in.symbol} tại giá {float(current_price)}",
            "order_id": new_order.id,
            "open_price": float(current_price),
            "margin_used": float(required_margin)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi khớp lệnh.")

@router.post("/close_order")
async def close_order(
    close_req: OrderClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API Xử lý Đóng lệnh và tính toán PnL"""
    wallet = current_user.wallet
    if not wallet:
        raise HTTPException(status_code=400, detail="Không tìm thấy ví tiền ảo.")

    # 1. Tìm lệnh và kiểm tra tính hợp lệ
    order = db.query(Order).filter(
        Order.id == close_req.order_id, 
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy lệnh hoặc lệnh không thuộc về bạn.")
    
    if order.status != OrderStatus.OPEN:
        raise HTTPException(status_code=400, detail="Lệnh này đã được đóng trước đó.")

    # 2. Lấy cấu hình Symbol để tính toán
    broker_symbol = resolve_broker_symbol(order.symbol)

    symbol_config = db.query(SymbolConfig).filter(SymbolConfig.symbol == broker_symbol).first()

    contract_size = symbol_config.contract_size if symbol_config else Decimal("1.0")
    leverage = symbol_config.base_leverage if symbol_config else 1


    # 3. Lấy giá đóng lệnh từ RAM
    try:
        # ĐÓNG LỆNH LÀ THỰC HIỆN GIAO DỊCH NGƯỢC LẠI
        # Lệnh mở BUY -> Khi đóng phải BÁN -> dùng giá BID (tức là gọi SELL)
        # Lệnh mở SELL -> Khi đóng phải MUA -> dùng giá ASK (tức là gọi BUY)
        close_order_type = "SELL" if order.order_type == "BUY" else "BUY"
        live_price_float = get_live_execution_price(broker_symbol, close_order_type)
        close_price = Decimal(str(live_price_float))
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 4. Tính toán PnL (Lợi nhuận/Thua lỗ)
    volume = order.volume
    
    if order.order_type == "BUY":
        pnl = volume * contract_size * (close_price - order.open_price)
    else: # Lệnh SELL
        pnl = volume * contract_size * (order.open_price - close_price)

    # 5. Tính lại Margin đã khóa lúc mở lệnh để trả lại cho user
    margin_reserved = (volume * contract_size * order.open_price) / Decimal(leverage)

    try:
        # Cập nhật trạng thái Lệnh
        order.status = OrderStatus.CLOSED
        order.close_price = close_price
        order.close_time = datetime.now(timezone.utc)
        order.profit_loss = pnl

        # Cập nhật Ví tiền (Balance)
        # Khi đóng lệnh: Balance = Balance hiện tại + Tiền Ký Quỹ Đã Khóa + Tiền Lời(Lỗ)
        wallet.balance = wallet.balance + margin_reserved + pnl

        db.commit()
        db.refresh(order)
        db.refresh(wallet)
        
        new_balance = float(wallet.balance)

        await ws_manager.send_personal_message(
            user_id=current_user.id,
            message={
                "type": "BALANCE_UPDATE", 
                "balance": new_balance,
                "message": f"Bạn vừa chốt lời/lỗ {float(pnl)}$"
            }
        )

        return {
            "status": "success",
            "message": f"Đã đóng lệnh {order.id}. PnL: {float(pnl):,.2f}",
            "order_id": order.id,
            "close_price": float(close_price),
            "pnl": float(pnl),
            "new_balance": new_balance
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error closing order: {e}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi đóng lệnh.")

@router.get("/orders")
def get_orders(
    status: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách lệnh của User (Có thể lọc theo trạng thái OPEN/CLOSED)"""
    query = db.query(Order).filter(Order.user_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
        
    # Trả về các lệnh mới nhất lên đầu
    orders = query.order_by(Order.open_time.desc()).all()
    return orders

@router.get("/get_active_symbols")
def get_active_symbols(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lấy danh sách các mã giao dịch đã được cấu hình và đang active"""
    symbols = db.query(SymbolConfig).filter(
        SymbolConfig.user_id == current_user.id,
        SymbolConfig.is_active == True).all()
    
    return [
        {
            "symbol": s.symbol,
            "contract_size": float(s.contract_size),
            "leverage": s.base_leverage
        } for s in symbols
    ]

@router.post("/add_symbol")
def add_symbol(
config_in: SymbolConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Thêm cấu hình mới cho một mã giao dịch"""
    # Kiểm tra xem mã này đã tồn tại chưa
    broker_symbol = resolve_broker_symbol(config_in.symbol)
    existing_symbol = db.query(SymbolConfig).filter(SymbolConfig.symbol == broker_symbol, SymbolConfig.user_id == current_user.id).first()
    if existing_symbol:
        raise HTTPException(status_code=400, detail=f"Mã giao dịch {config_in.symbol} đã tồn tại.")

    new_symbol = SymbolConfig(
        user_id=current_user.id,
        symbol=broker_symbol,
        contract_size=config_in.contract_size,
        base_leverage=config_in.base_leverage,
        is_active=config_in.is_active
    )
    
    db.add(new_symbol)
    db.commit()
    db.refresh(new_symbol)
    
    return {
        "status": "success", 
        "message": f"Đã thêm mã {new_symbol.symbol}",
        "data": new_symbol
    }

@router.put("/edit_symbol/{symbol_id}")
def edit_symbol(
    symbol_id: int,
    config_in: SymbolConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật cấu hình của một mã giao dịch (Contract Size, Leverage...)"""
    # symbol_id truyền từ Frontend là ID (Primary Key) của bản ghi, không cần resolve broker name
    symbol = db.query(SymbolConfig).filter(SymbolConfig.id == symbol_id, SymbolConfig.user_id == current_user.id).first()
    
    if not symbol:
        raise HTTPException(status_code=404, detail="Không tìm thấy cấu hình của mã này.")

    # Cập nhật các trường nếu có dữ liệu gửi lên
    if config_in.contract_size is not None:
        symbol.contract_size = config_in.contract_size
    if config_in.base_leverage is not None:
        symbol.base_leverage = config_in.base_leverage
    if config_in.is_active is not None:
        symbol.is_active = config_in.is_active

    db.commit()
    db.refresh(symbol)
    
    return {
        "status": "success", 
        "message": f"Đã cập nhật mã {symbol.symbol}",
        "data": symbol
    }

@router.delete("/del_symbol/{symbol_id}")
def delete_symbol(
    symbol_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa hoàn toàn một mã giao dịch khỏi hệ thống"""
    # Query trực tiếp bằng ID thay vì dùng broker_symbol (vốn là string) để so khớp với ID (int)
    symbol = db.query(SymbolConfig).filter(SymbolConfig.id == symbol_id, SymbolConfig.user_id == current_user.id).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Không tìm thấy cấu hình của mã này.")

    # Lưu ý: Cần cân nhắc kĩ trước khi xóa nếu đã có Order liên kết với mã này trong DB.
    # Phương án an toàn hơn thường là set is_active = False qua API Edit.
    symbol_name = symbol.symbol
    db.delete(symbol)
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Đã xóa cấu hình mã {symbol_name} thành công."
    }

@router.get("/get_symbols")
def get_symbols(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbols = db.query(SymbolConfig).filter(SymbolConfig.user_id == current_user.id).all()
    return [
        {
            "id": s.id, 
            "symbol": s.symbol,
            "contract_size": float(s.contract_size),
            "leverage": s.base_leverage,
            "is_active": s.is_active
        } for s in symbols
    ]


@router.get("/signals/history")
async def get_bot_signal_history(
    symbol: str = Query(..., description="Mã giao dịch, VD: XAUUSD"),
    tf: str = Query(..., description="Khung thời gian, VD: M5"),
    from_time: Optional[int] = Query(None, description="Unix timestamp bắt đầu"),
    to_time: Optional[int] = Query(None, description="Unix timestamp kết thúc"),
    limit: int = Query(100, description="Số lượng record cần lấy"),
    db: Session = Depends(global_analyze.get_analyze_db)
):
    """
    API cung cấp lịch sử đánh đấm của các chiến thuật (Paper Trades).
    Hỗ trợ lấy theo vùng thời gian để tối ưu cho Chart.
    """
    try:
        query = db.query(SignalHistory).filter(
            SignalHistory.symbol == symbol,
            SignalHistory.timeframe == tf
        )

        # Nếu có range thời gian, ưu tiên lấy theo range và có thể mở rộng limit
        actual_limit = limit
        if from_time:
            query = query.filter(SignalHistory.timestamp >= from_time)
            actual_limit = max(limit, 500) # Tăng limit nếu đang load range quá khứ
        if to_time:
            query = query.filter(SignalHistory.timestamp <= to_time)
            actual_limit = max(limit, 500)

        # Luôn lấy desc để lấy mới nhất trong vùng đó, sau đó Frontend sẽ sort lại asc
        signals = query.order_by(SignalHistory.timestamp.desc()).limit(actual_limit).all()

        # Chuẩn bị dữ liệu trả về cho Frontend
        data_response = []
        for s in signals:
            data_response.append({
                "id": s.id,
                "time": s.timestamp,                # Dùng cho Chart cắm mũi tên
                "strategy_id": s.strategy_id,       # Dùng để phân loại trên bảng
                "symbol": s.symbol,
                "signal": s.signal,                 # BUY / SELL
                "outcome": s.outcome,               # PENDING / WIN / LOSS
                "entry_price": s.entry_price,
                "close_price": s.close_price,
                "sl": s.suggested_sl,
                "tp": s.suggested_tp,
                "pnl": s.realized_pnl,              # Lời/Lỗ thực tế
                "reason": s.reason
            })

        return {
            "status": "success",
            "message": "Lấy lịch sử thành công",
            "data": data_response
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi truy xuất dữ liệu: {str(e)}",
            "data": []
        }

@router.get("/radar/state")
async def get_radar_state():
    """API đồng bộ trạng thái Matrix Radar cho Frontend khi mới load trang"""
    from backend_cloud.app.core.globals import global_scanner
    # Chuyển đổi broker symbol sang client symbol trước khi trả về
    matrix = {}
    for broker_sym, tf_data in global_scanner.radar_matrix.items():
        client_sym = clean_symbol_for_client(broker_sym)
        matrix[client_sym] = tf_data
    return {"status": "success", "data": matrix}

#USER ODERS

@router.post("/orders/close/{ticket}")
async def close_user_order(
    ticket: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # 1. Tìm lệnh gốc trong DB
    order_record = db.query(UserOrder).filter(
        UserOrder.mt5_ticket == ticket,
        UserOrder.user_id == current_user.id,
        UserOrder.status == OrderStatus.OPEN  # Sử dụng Enum
    ).first()

    if not order_record:
        raise HTTPException(status_code=404, detail="Không tìm thấy lệnh OPEN hoặc không có quyền sở hữu.")

    # 2. Thực thi đóng lệnh qua MT5 (Giữ nguyên logic cũ của bạn)
    # close_result = execute_mt5_close(ticket, ...)
    
    # 3. NẾU ĐÓNG THÀNH CÔNG -> LƯU DATABASE
    if True: #close_result.retcode == mt5.TRADE_RETCODE_DONE:
        close_price = 0 #close_result.price
        
        # Tính toán Profit/Loss ($)
        if order_record.order_type == "BUY":
            pnl = (close_price - float(order_record.open_price)) * float(order_record.volume)
        else:
            pnl = (float(order_record.open_price) - close_price) * float(order_record.volume)

        # Cập nhật Record với cấu trúc mới
        order_record.status = OrderStatus.CLOSED
        order_record.close_price = close_price
        order_record.close_time = datetime.now(timezone.utc)
        order_record.profit_loss = pnl
        
        db.commit()
        
        return {"status": "success", "message": f"Chốt lệnh thành công", "pnl": pnl}
    else:
        raise HTTPException(status_code=400, detail="MT5 từ chối đóng lệnh.")

@router.get("/orders/history")
async def get_manual_order_history(days: int = 7):
    """Lấy lịch sử các lệnh thủ công đã chốt trong X ngày qua"""
    if mt5 is None or not mt5.terminal_info():
        raise HTTPException(status_code=500, detail="Thư viện MT5 chưa sẵn sàng hoặc chưa kết nối")

    # Lấy từ 7 ngày trước đến hiện tại
    from_date = datetime.now() - timedelta(days=days)
    to_date = datetime.now() + timedelta(days=1) # Cộng 1 ngày để bao trọn hôm nay

    # Lấy Deals (Giao dịch thực tế) từ MT5
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None:
        return []

    closed_orders = []
    for deal in deals:
        # Trong MT5, DEAL_ENTRY_OUT (mã là 1) nghĩa là hành động Đóng lệnh (Chốt sổ)
        if deal.entry == 1: 
            closed_orders.append({
                "id": deal.position_id, # ID gốc của lệnh lúc mở
                "symbol": deal.symbol,
                "order_type": "BUY" if deal.type == 1 else "SELL", # Lệnh OUT ngược chiều với lệnh IN
                "volume": deal.volume,
                "open_price": 0, # MT5 deal out không lưu open_price dễ dàng, ta có thể bỏ qua hoặc map sau
                "close_price": deal.price,
                "open_time": deal.time, # Thời gian đóng lệnh
                "pnl": deal.profit, # 💰 Đây chính là Lời/Lỗ thực tế
                "status": "CLOSED"
            })

    # Đảo ngược mảng để lệnh mới đóng nằm trên cùng
    return list(reversed(closed_orders))
