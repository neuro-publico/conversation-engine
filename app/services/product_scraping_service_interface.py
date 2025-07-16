from abc import ABC, abstractmethod
from app.requests.product_scraping_request import ProductScrapingRequest


class ProductScrapingServiceInterface(ABC):
    @abstractmethod
    async def scrape_product(self, request: ProductScrapingRequest):
        pass

    async def scrape_direct(self, html):
        pass
