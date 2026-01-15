"""
Tests para ProductScrapingService.
Verifica el servicio de scraping de productos.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.requests.product_scraping_request import ProductScrapingRequest
from app.services.product_scraping_service import ProductScrapingService
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface


class TestProductScrapingService:
    """Tests para ProductScrapingService."""

    @pytest.fixture
    def mock_scraping_factory(self):
        """Mock para ScrapingFactory."""
        mock = MagicMock()
        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(return_value={"data": {"name": "Test Product", "price": "29.99"}})
        mock_scraper.scrape_direct = AsyncMock(return_value={"data": {"name": "Direct Product"}})
        mock.get_scraper = MagicMock(return_value=mock_scraper)
        return mock

    @pytest.fixture
    def service(self, mock_scraping_factory):
        """Crear instancia de ProductScrapingService con mock."""
        return ProductScrapingService(scraping_factory=mock_scraping_factory)

    @pytest.mark.unit
    def test_implements_interface(self, service):
        """Debe implementar ProductScrapingServiceInterface."""
        assert isinstance(service, ProductScrapingServiceInterface)

    # ========================================================================
    # Tests para scrape_product
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_product_success(self, service, mock_scraping_factory):
        """Debe scrapear producto correctamente."""
        request = ProductScrapingRequest(product_url="https://www.amazon.com/dp/B08N5WRWNW")

        result = await service.scrape_product(request)

        assert "data" in result
        assert result["data"]["name"] == "Test Product"
        mock_scraping_factory.get_scraper.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_product_with_country(self, service, mock_scraping_factory):
        """Debe pasar el país al factory."""
        request = ProductScrapingRequest(product_url="https://dropi.co/products/test", country="mx")

        await service.scrape_product(request)

        mock_scraping_factory.get_scraper.assert_called_with("https://dropi.co/products/test", country="mx")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_product_extracts_domain(self, service, mock_scraping_factory):
        """Debe extraer el dominio correctamente."""
        request = ProductScrapingRequest(product_url="https://www.amazon.com/dp/B08N5WRWNW?ref=test")

        await service.scrape_product(request)

        # Verificar que se llamó al scraper.scrape con URL y dominio
        scraper = mock_scraping_factory.get_scraper.return_value
        call_args = scraper.scrape.call_args
        assert "www.amazon.com" in call_args[0][1]

    # ========================================================================
    # Tests para scrape_direct
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_direct_success(self, service, mock_scraping_factory):
        """Debe scrapear HTML directo correctamente."""
        html = "<html><body><h1>Product</h1></body></html>"

        result = await service.scrape_direct(html)

        assert "data" in result
        scraper = mock_scraping_factory.get_scraper.return_value
        scraper.scrape_direct.assert_called_once_with(html)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_direct_uses_fallback_url(self, service, mock_scraping_factory):
        """Debe usar URL fallback para obtener scraper."""
        html = "<html></html>"

        await service.scrape_direct(html)

        # Verifica que get_scraper fue llamado (con cualquier URL)
        mock_scraping_factory.get_scraper.assert_called_once()


class TestDropiService:
    """Tests para DropiService."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_departments(self):
        """Debe obtener departamentos correctamente."""
        from unittest.mock import patch

        from app.services.dropi_service import DropiService

        with patch("app.services.dropi_service.dropi_client") as mock_client:
            mock_client.get_departments = AsyncMock(return_value={"objects": [{"id": 1, "name": "Dept 1"}]})

            service = DropiService()
            result = await service.get_departments("co")

            assert len(result) == 1
            assert result[0]["name"] == "Dept 1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cities_by_department(self):
        """Debe obtener ciudades por departamento."""
        from unittest.mock import patch

        from app.services.dropi_service import DropiService

        with patch("app.services.dropi_service.dropi_client") as mock_client:
            mock_client.get_cities_by_department = AsyncMock(
                return_value={"objects": {"cities": [{"id": 1, "name": "City 1"}]}}
            )

            service = DropiService()
            result = await service.get_cities_by_department(1, "co")

            assert len(result) == 1
            assert result[0]["name"] == "City 1"
