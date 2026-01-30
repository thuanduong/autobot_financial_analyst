# api\check_symbols.py
import MetaTrader5 as mt5
from config.settings import MT5_PATH

if not mt5.initialize(path=MT5_PATH):
    print("❌ Lỗi kết nối MT5")
else:
    print("✅ Đã kết nối MT5. Đang tìm kiếm các mã thực tế...")
    
    # Lấy tất cả mã có chứa chữ USD
    symbols = mt5.symbols_get()
    
    print("\n--- DANH SÁCH MÃ TÌM THẤY TRÊN OANDA ---")
    found_count = 0
    for s in symbols:
        # Lọc ra các mã phổ biến để xem tên thật
        if "XAU" in s.name or "EUR" in s.name or "BTC" in s.name:
            print(f"👉 Tên hiển thị: {s.name} \t(Path: {s.path})")
            found_count += 1
            
    if found_count == 0:
        print("⚠️ Không tìm thấy mã nào! Hãy chắc chắn bạn đã nhấn Ctrl+U trong MT5 và hiện các mã lên.")
    
    mt5.shutdown()