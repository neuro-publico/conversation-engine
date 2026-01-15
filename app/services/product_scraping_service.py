from urllib.parse import urlparse

from fastapi import Depends

from app.factories.scraping_factory import ScrapingFactory
from app.requests.product_scraping_request import ProductScrapingRequest
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface


class ProductScrapingService(ProductScrapingServiceInterface):
    def __init__(self, scraping_factory: ScrapingFactory = Depends()):
        self.scraping_factory = scraping_factory

    async def scrape_product(self, request: ProductScrapingRequest):
        url = str(request.product_url)
        domain = urlparse(url).netloc.lower()

        scraper = self.scraping_factory.get_scraper(url, country=request.country)
        return await scraper.scrape(url, domain)

    async def scrape_direct(self, html):
        scraper = self.scraping_factory.get_scraper(
            "https://www.macys.com/shop/womens-clothing/accessories/womens-sunglasses/Upc_bops_purchasable,Productsperpage/5376,120?id=28295&_additionalStoreLocations=5376"
        )

        return await scraper.scrape_direct(html)
