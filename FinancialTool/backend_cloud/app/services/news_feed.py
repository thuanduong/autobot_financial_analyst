import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class NewsFeedService:
    def __init__(self):
        self.news_cache = []
        self.last_fetch = None
        # URL lịch kinh tế dạng JSON (Ví dụ từ nfs.faireconomy.media hoặc nguồn khác)
        # Nếu không có nguồn JSON, ta có thể parse HTML hoặc dùng thư viện 'investpy'
        self.source_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json" 

    def fetch_calendar(self):
        """Lấy lịch kinh tế tuần này"""
        try:
            # Giả sử ta lấy được data dạng list dict
            # resp = requests.get(self.source_url)
            # data = resp.json()
            
            # MOCK DATA (Giả lập tin tức để test)
            now = datetime.utcnow()
            mock_data = [
                {
                    "title": "Non-Farm Employment Change",
                    "country": "USD",
                    "date": (now + timedelta(minutes=10)).isoformat(), # Sắp ra tin sau 10p
                    "impact": "High",
                    "forecast": "180K",
                    "previous": "175K"
                },
                {
                    "title": "CPI y/y",
                    "country": "USD",
                    "date": (now + timedelta(hours=2)).isoformat(),
                    "impact": "High",
                    "forecast": "3.2%",
                    "previous": "3.1%"
                }
            ]
            
            self.news_cache = mock_data
            self.last_fetch = datetime.now()
            logger.info(f"✅ Đã cập nhật {len(self.news_cache)} tin tức mới.")
            return self.news_cache
        except Exception as e:
            logger.error(f"❌ Lỗi lấy tin tức: {e}")
            return []

    def check_high_impact_news(self, symbol: str, lookahead_minutes=60, lookback_minutes=30) -> dict:
        """
        Kiểm tra xem có tin mạnh (High Impact) nào liên quan đến cặp tiền này
        trong khoảng [Quá khứ 30p, Tương lai 60p] hay không.
        """
        if not self.news_cache or (datetime.now() - self.last_fetch > timedelta(hours=4)):
            self.fetch_calendar()

        # Tách cặp tiền để biết tin nước nào ảnh hưởng. VD: XAUUSD -> USD
        related_currencies = []
        if "USD" in symbol or "XAU" in symbol: related_currencies.append("USD")
        if "EUR" in symbol: related_currencies.append("EUR")
        if "GBP" in symbol: related_currencies.append("GBP")
        if "JPY" in symbol: related_currencies.append("JPY")
        # ... thêm các cặp khác

        now = datetime.now(timezone.utc)
        alert = None

        for news in self.news_cache:
            if news["country"] not in related_currencies: continue
            if news["impact"] != "High": continue # Chỉ lọc tin mạnh
            
            try:
                news_time = datetime.fromisoformat(news["date"])
                # Kiểm tra khoảng thời gian
                time_diff = (news_time - now).total_seconds() / 60 # Phút
                
                # Nếu tin nằm trong vùng nguy hiểm: 
                # Từ -30p (đã ra tin) đến +60p (sắp ra tin)
                if -lookback_minutes <= time_diff <= lookahead_minutes:
                    alert = {
                        "has_news": True,
                        "title": news["title"],
                        "country": news["country"],
                        "time_diff_min": round(time_diff, 1),
                        "impact": news["impact"]
                    }
                    break
            except: continue
            
        return alert or {"has_news": False}

news_service = NewsFeedService()
