from backend_cloud.config.settings import WATCHLIST, SYMBOL_SUFFIX

def resolve_broker_symbol(client_symbol: str) -> str:
    """
    Input: 'XAUUSD' (từ Client)
    Output: 'XAUUSD.sml' (trong Config/MT5)
    Logic: Tìm mã trong WATCHLIST có phần gốc trùng với input
    """
    # 1. Nếu trùng khớp hoàn toàn (Client gửi đúng mã sàn)
    if client_symbol in WATCHLIST:
        return client_symbol

    # 2. Tìm kiếm chính xác dựa trên Suffix (Hỗ trợ cả .suffix và suffix)
    if SYMBOL_SUFFIX:
        patterns = [f"{client_symbol}{SYMBOL_SUFFIX}", f"{client_symbol}.{SYMBOL_SUFFIX}"]
        for p in patterns:
            if p in WATCHLIST:
                return p

    # 3. Fuzzy match fallback
    for broker_symbol in WATCHLIST:
        # Nếu mã sàn bắt đầu bằng mã gốc (VD: XAUUSD.sml bắt đầu bằng XAUUSD)
        if broker_symbol.startswith(client_symbol):
            return broker_symbol
            
    # 4. Nếu không tìm thấy, trả về nguyên gốc (để log lỗi sau này)
    return client_symbol

def clean_symbol_for_client(broker_symbol: str) -> str:
    """
    Input: 'XAUUSD.sml'
    Output: 'XAUUSD'
    Dùng để bắn Socket xuống Client cho đẹp
    """
    result = broker_symbol
    
    if SYMBOL_SUFFIX:
        # Ưu tiên xóa kèm dấu chấm nếu có (VD: .sml)
        dot_suffix = f".{SYMBOL_SUFFIX}"
        if result.endswith(dot_suffix):
            result = result[:-len(dot_suffix)]
        elif result.endswith(SYMBOL_SUFFIX):
            result = result[:-len(SYMBOL_SUFFIX)]
            
    # Dọn dẹp nốt dấu chấm ở cuối nếu còn sót lại (Trường hợp suffix không khớp nhưng có dấu chấm)
    return result.rstrip('.')