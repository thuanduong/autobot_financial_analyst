import asyncio
import threading
import sys
import os

# ==========================================================
# XỬ LÝ CONFIG THEO CLI FLAGS (-oanda, -exness)
# Phải thực hiện TRƯỚC khi import các module khác của app
# ==========================================================
broker_choice = "exness" # Mặc định
if "-oanda" in sys.argv:
    broker_choice = "oanda"
elif "-exness" in sys.argv:
    broker_choice = "exness"

os.environ["TRADING_BROKER"] = broker_choice
print(f"🔧 [CONFIG] System is running for broker: {broker_choice.upper()}")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import Components
#from backend_cloud.app.database.models import init_db

from backend_cloud.app.api.routes import router
from backend_cloud.app.api.auth_routes import router as auth_routes
from backend_cloud.app.api.user_routes import router as user_routes
from backend_cloud.app.api.trade_routes import router as trade_routes

from backend_cloud.app.core.globals import global_scanner, global_analyze
from backend_cloud.app.database.base import engine, Base
from backend_cloud.app.engine.technical_manager import tech_engine

# GLOBAL INSTANCES
scanner = global_scanner

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. KHỞI ĐỘNG
    print("🚀 System Starting...")
    
    tech_engine.init(global_analyze)
    async def safe_run_scanner():
        try:
            print("⏳ Đang kích hoạt run_loop...")
            await scanner.run_loop()
        except asyncio.CancelledError:
            print("⚠️ Scanner bị ép dừng (Cancelled).")
        except Exception as e:
            # Dòng này sẽ lôi cổ cái lỗi đang ẩn nấp ra ánh sáng
            print(f"💥 LỖI NGHIÊM TRỌNG LÀM SCANNER CHẾT LÂM SÀNG: {e}")
            import traceback
            traceback.print_exc() 
    
    # Khởi chạy hàm an toàn
    task = asyncio.create_task(safe_run_scanner())
    
    yield # Server bắt đầu nhận request
    
    # 2. TẮT MÁY
    print("🛑 System Shutting down...")
    if scanner:
        scanner.is_running = False
    
    task.cancel() # Hủy task đang chạy ngầm
    try:
        await task # Đợi task tắt hẳn
    except asyncio.CancelledError:
        pass

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Cloud Trading System", lifespan=lifespan)
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static & Routes
app.mount("/static", StaticFiles(directory="backend_cloud/static"), name="static")
app.include_router(router)
app.include_router(auth_routes)
app.include_router(user_routes)
app.include_router(trade_routes)

if __name__ == "__main__":
    import uvicorn
    # Chạy server
    uvicorn.run("backend_cloud.main:app", host="0.0.0.0", port=8001, reload=False)