import MetaTrader5 as mt5

def get_live_execution_price(symbol: str, order_type: str) -> float:
    """
    Request giá trực tiếp từ MT5 ngay tại thời điểm gọi hàm.
    Bỏ qua hoàn toàn Database để đảm bảo độ trễ = 0.
    """
    # Kiểm tra trạng thái kết nối hiện tại thay vì initialize mới liên tục
    terminal_info = mt5.terminal_info()
    if terminal_info is None:
        raise Exception("Không thể kết nối đến MT5 Engine")

    # Lấy tick (thông tin giá ngay tức thời) của mã giao dịch
    try:
        tick = mt5.symbol_info_tick(symbol)
    except Exception as e:
        print(f"❌ MT5 Tick Error for {symbol}: {e}")
        tick = None
    
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