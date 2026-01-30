# main.py
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core.engine.scanner import MarketScanner
from core.engine.signal_bus import SignalBus
from api import routes  # <--- Import file routes vừa sửa

app = FastAPI()

# 1. Mount Static (CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Đăng ký Router (QUAN TRỌNG: Nếu thiếu dòng này sẽ bị lỗi 404 API)
app.include_router(routes.router)

# 3. Khởi tạo Core Engine
bus = SignalBus()
scanner = MarketScanner(bus)

# 4. Inject Scanner vào Routes 
# (Để API có thể đọc dữ liệu từ Scanner)
routes.scanner_instance = scanner

@app.on_event("startup")
async def startup_event():
    print("🚀 Server đang khởi động...")
    # Chạy vòng lặp Scanner ngầm
    asyncio.create_task(scanner.run())

# Nếu chạy trực tiếp bằng python main.py (Optional)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)