"""
Tests para ScrapingFactory.
Verifica la correcta selección de scrapers según el dominio de la URL.
"""

from unittest.mock import MagicMock

import pytest

from app.factories.scraping_factory import ScrapingFactory
from app.scrapers.aliexpress_scraper import AliexpressScraper
from app.scrapers.amazon_scraper import AmazonScraper
from app.scrapers.cj_scraper import CJScraper
from app.scrapers.dropi_scraper import DropiScraper
from app.scrapers.ia_scraper import IAScraper
from app.scrapers.scraper_interface import ScraperInterface


class TestScrapingFactory:
    """Tests para ScrapingFactory."""

    @pytest.fixture
    def factory(self, mock_message_service):
        """Crear instancia de ScrapingFactory con mock de message_service."""
        return ScrapingFactory(message_service=mock_message_service)

    @pytest.mark.unit
    def test_get_amazon_scraper(self, factory):
        """Debe retornar AmazonScraper para URLs de Amazon."""
        urls = [
            "https://www.amazon.com/dp/B08N5WRWNW",
            "https://amazon.com/gp/product/B08N5WRWNW",
            "https://www.amazon.es/dp/B08N5WRWNW",
            "https://www.amazon.com.mx/dp/B08N5WRWNW",
        ]

        for url in urls:
            scraper = factory.get_scraper(url)
            assert isinstance(scraper, AmazonScraper), f"Failed for URL: {url}"
            assert isinstance(scraper, ScraperInterface)

    @pytest.mark.unit
    def test_get_aliexpress_scraper(self, factory):
        """Debe retornar AliexpressScraper para URLs de AliExpress."""
        urls = [
            "https://www.aliexpress.com/item/1005001234567890.html",
            "https://es.aliexpress.com/item/1005001234567890.html",
            "https://aliexpress.com/item/1005001234567890.html",
        ]

        for url in urls:
            scraper = factory.get_scraper(url)
            assert isinstance(scraper, AliexpressScraper), f"Failed for URL: {url}"
            assert isinstance(scraper, ScraperInterface)

    @pytest.mark.unit
    def test_get_cj_scraper(self, factory):
        """Debe retornar CJScraper para URLs de CJ Dropshipping."""
        urls = [
            "https://www.cjdropshipping.com/product/test-product-p-123456.html",
            "https://cjdropshipping.com/product/test-p-789.html",
        ]

        for url in urls:
            scraper = factory.get_scraper(url)
            assert isinstance(scraper, CJScraper), f"Failed for URL: {url}"
            assert isinstance(scraper, ScraperInterface)

    @pytest.mark.unit
    def test_get_dropi_scraper(self, factory):
        """Debe retornar DropiScraper para URLs de Dropi."""
        urls = [
            "https://app.dropi.co/catalog/product/12345",
            "https://dropi.co/products/test",
        ]

        for url in urls:
            scraper = factory.get_scraper(url)
            assert isinstance(scraper, DropiScraper), f"Failed for URL: {url}"
            assert isinstance(scraper, ScraperInterface)

    @pytest.mark.unit
    def test_dropi_scraper_with_country(self, factory):
        """DropiScraper debe inicializarse con el país correcto."""
        url = "https://app.dropi.co/catalog/product/12345"

        scraper_co = factory.get_scraper(url, country="co")
        assert isinstance(scraper_co, DropiScraper)

        scraper_mx = factory.get_scraper(url, country="mx")
        assert isinstance(scraper_mx, DropiScraper)

    @pytest.mark.unit
    def test_get_ia_scraper_for_unknown_domain(self, factory):
        """Debe retornar IAScraper para dominios desconocidos."""
        urls = [
            "https://www.macys.com/shop/product/123",
            "https://www.walmart.com/ip/test-product",
            "https://www.ebay.com/itm/123456",
            "https://www.unknown-store.com/product/test",
        ]

        for url in urls:
            scraper = factory.get_scraper(url)
            assert isinstance(scraper, IAScraper), f"Failed for URL: {url}"
            assert isinstance(scraper, ScraperInterface)

    @pytest.mark.unit
    def test_factory_requires_message_service_for_ia_scraper(self, mock_message_service):
        """IAScraper requiere message_service para funcionar."""
        factory = ScrapingFactory(message_service=mock_message_service)
        scraper = factory.get_scraper("https://unknown-domain.com/product")

        assert isinstance(scraper, IAScraper)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url,expected_scraper",
        [
            ("https://www.amazon.com/dp/B08TEST", AmazonScraper),
            ("https://www.aliexpress.com/item/123.html", AliexpressScraper),
            ("https://cjdropshipping.com/product/test", CJScraper),
            ("https://dropi.co/products/test", DropiScraper),
            ("https://other-store.com/product", IAScraper),
        ],
    )
    def test_scraper_selection_parametrized(self, factory, url, expected_scraper):
        """Test parametrizado para selección de scrapers."""
        scraper = factory.get_scraper(url)
        assert isinstance(scraper, expected_scraper)

    @pytest.mark.unit
    def test_url_case_insensitive(self, factory):
        """La detección de dominio debe ser case-insensitive."""
        scraper_lower = factory.get_scraper("https://www.amazon.com/dp/B08TEST")
        scraper_upper = factory.get_scraper("https://WWW.AMAZON.COM/dp/B08TEST")

        assert type(scraper_lower) == type(scraper_upper)
        assert isinstance(scraper_lower, AmazonScraper)
