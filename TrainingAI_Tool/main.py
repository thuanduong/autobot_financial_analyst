# main.py
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from starlette.requests import Request

from core.engine.scanner import MarketScanner
from core.engine.signal_bus import SignalBus
from api.routes import router, set_scanner_instance

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

bus = SignalBus()
scanner = MarketScanner(bus)
set_scanner_instance(scanner)
app.include_router(router)

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("app.html", {"request": request})

@app.on_event("startup")
async def startup_event():
    print("🚀 Server đang khởi động...")
    # Chạy vòng lặp Scanner ngầm
    asyncio.create_task(scanner.run())

# Nếu chạy trực tiếp bằng python main.py (Optional)
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)