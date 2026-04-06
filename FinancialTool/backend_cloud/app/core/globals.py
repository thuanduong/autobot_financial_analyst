# File: backend_cloud/app/core/globals.py

#from backend_cloud.app.database.repository import TradeRepo
from backend_cloud.app.core.scanner import MarketScanner
from backend_cloud.app.database.chart_repo import ChartRepo 
from backend_cloud.app.database.analyze_repo import AnalyzeRepo
# 1. Khởi tạo Repo
global_repo = ChartRepo()
global_analyze = AnalyzeRepo()

# 2. Khởi tạo Scanner (Bơm repo vào)
global_scanner = MarketScanner(global_repo, global_analyze)

# 3. Trích xuất Broker để dùng cho Route
#global_broker = global_scanner.broker