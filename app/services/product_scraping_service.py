from fastapi import Depends

from app.requests.product_scraping_request import ProductScrapingRequest
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface
from app.factories.scraping_factory import ScrapingFactory
from urllib.parse import urlparse


class ProductScrapingService(ProductScrapingServiceInterface):
    def __init__(self, scraping_factory: ScrapingFactory = Depends()):
        self.scraping_factory = scraping_factory

    async def scrape_product(self, request: ProductScrapingRequest):
        url = str(request.product_url)
        domain = urlparse(url).netloc.lower()

        scraper = self.scraping_factory.get_scraper(url)
        return await scraper.scrape(url, domain)
