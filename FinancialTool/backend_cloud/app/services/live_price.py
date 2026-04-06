import MetaTrader5 as mt5

def get_live_execution_price(symbol: str, order_type: str) -> float:
    """
    Request giá trực tiếp từ MT5 ngay tại thời điểm gọi hàm.
    Bỏ qua hoàn toàn Database để đảm bảo độ trễ = 0.
    """
    # Đảm bảo đã kết nối MT5
    if not mt5.initialize():
        raise Exception("Không thể kết nối đến MT5 Engine")

    # Lấy tick (thông tin giá ngay tức thời) của mã giao dịch
    tick = mt5.symbol_info_tick(symbol)
    
    if tick is None:
        raise Exception(f"Không lấy được giá live cho {symbol}")

    # TRỌNG TÂM CỦA TRADING: Phân biệt Bid / Ask
    # Người dùng MUA (BUY) -> Phải khớp giá ASK (Cao hơn)
    # Người dùng BÁN (SELL) -> Phải khớp giá BID (Thấp hơn)
    if order_type.upper() == "BUY":
        return float(tick.ask)
    elif order_type.upper() == "SELL":
        return float(tick.bid)
    else:
        raise ValueError("Loại lệnh không hợp lệ")