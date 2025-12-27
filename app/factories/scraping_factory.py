from urllib.parse import urlparse

from fastapi import Depends

from app.scrapers.scraper_interface import ScraperInterface
from app.scrapers.amazon_scraper import AmazonScraper
from app.scrapers.aliexpress_scraper import AliexpressScraper
from app.scrapers.cj_scraper import CJScraper
from app.scrapers.dropi_scraper import DropiScraper
from app.scrapers.ia_scraper import IAScraper
from app.services.message_service_interface import MessageServiceInterface


class ScrapingFactory:
    def __init__(self, message_service: MessageServiceInterface = Depends()):
        self.message_service = message_service

    def get_scraper(self, url: str, country: str = "co") -> ScraperInterface:
        domain = urlparse(url).netloc.lower()

        if "amazon" in domain:
            return AmazonScraper()
        elif "aliexpress" in domain:
            return AliexpressScraper()
        elif "cjdropshipping" in domain:
            return CJScraper()
        elif "dropi" in domain:
            return DropiScraper(country=country)
        else:
            return IAScraper(message_service=self.message_service)
