"""
Tests para AliexpressScraper.
Verifica la extracción de datos de productos de AliExpress.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.scrapers.aliexpress_scraper import AliexpressScraper
from app.scrapers.scraper_interface import ScraperInterface


class TestAliexpressScraper:
    """Tests para AliexpressScraper."""

    @pytest.fixture
    def scraper(self):
        """Crear instancia de AliexpressScraper."""
        return AliexpressScraper()

    @pytest.mark.unit
    def test_implements_interface(self, scraper):
        """Debe implementar ScraperInterface."""
        assert isinstance(scraper, ScraperInterface)

    # ========================================================================
    # Tests para extracción de Item ID
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url,expected_id",
        [
            ("https://www.aliexpress.com/item/1005001234567890.html", "1005001234567890"),
            ("https://es.aliexpress.com/item/1005009876543210.html", "1005009876543210"),
            ("https://aliexpress.com/item/4000123456789.html?spm=test", "4000123456789"),
        ],
    )
    def test_extract_item_id_from_url_path(self, scraper, url, expected_id):
        """Debe extraer el ID del producto de URLs con patrón /item/ID.html."""
        item_id = scraper._extract_item_id(url)
        assert item_id == expected_id

    @pytest.mark.unit
    def test_extract_item_id_from_query_param(self, scraper):
        """Debe extraer el ID del producto de query parameters."""
        url = "https://aliexpress.com/item?itemId=1005001234567890"
        item_id = scraper._extract_item_id(url)
        assert item_id == "1005001234567890"

    @pytest.mark.unit
    def test_extract_item_id_invalid_url_raises_exception(self, scraper):
        """Debe lanzar HTTPException para URLs sin ID válido."""
        invalid_urls = [
            "https://www.aliexpress.com/search/test",
            "https://www.aliexpress.com/",
            "https://www.google.com/search",
        ]

        for url in invalid_urls:
            with pytest.raises(HTTPException) as exc_info:
                scraper._extract_item_id(url)
            assert exc_info.value.status_code == 400

    # ========================================================================
    # Tests para extracción de datos del producto
    # ========================================================================

    @pytest.mark.unit
    def test_get_item_data(self, scraper, sample_aliexpress_product_data):
        """Debe extraer item_data de la respuesta."""
        item_data = scraper._get_item_data(sample_aliexpress_product_data)
        assert item_data["title"] == "AliExpress Test Product"

    @pytest.mark.unit
    def test_get_item_data_raises_on_empty(self, scraper):
        """Debe lanzar ValueError si no hay datos de producto."""
        with pytest.raises(ValueError):
            scraper._get_item_data({"result": {}})

    @pytest.mark.unit
    def test_get_name(self, scraper):
        """Debe extraer el nombre del producto."""
        item_data = {"title": "Test Product Name"}
        assert scraper._get_name(item_data) == "Test Product Name"

        item_data = {}
        assert scraper._get_name(item_data) == ""

    @pytest.mark.unit
    def test_get_description_from_html(self, scraper):
        """Debe extraer descripción limpiando HTML."""
        item_data = {"description": {"html": "<p>Test <b>description</b></p>"}}
        description = scraper._get_description(item_data)
        assert "Test" in description
        assert "description" in description
        assert "<p>" not in description  # HTML removido

    @pytest.mark.unit
    def test_get_description_from_properties(self, scraper):
        """Debe extraer descripción de propiedades si no hay HTML."""
        item_data = {
            "properties": {"list": [{"name": "Material", "value": "Cotton"}, {"name": "Size", "value": "Large"}]}
        }
        description = scraper._get_description(item_data)
        assert "Material: Cotton" in description
        assert "Size: Large" in description

    # ========================================================================
    # Tests para parseo de precios
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "price_input,expected",
        [
            (15.99, Decimal("15.99")),
            ("15.99", Decimal("15.99")),
            ("$15.99", Decimal("15.99")),
            (0, Decimal("0")),
        ],
    )
    def test_parse_price_valid_values(self, scraper, price_input, expected):
        """Debe parsear correctamente diferentes formatos de precio."""
        result = scraper._parse_price(price_input)
        assert result == expected

    @pytest.mark.unit
    def test_parse_price_returns_none_for_invalid(self, scraper):
        """Debe retornar None para valores inválidos."""
        assert scraper._parse_price(None) is None
        assert scraper._parse_price("") is None
        assert scraper._parse_price("invalid") is None

    @pytest.mark.unit
    def test_get_price_from_promotion(self, scraper):
        """Debe preferir precio de promoción."""
        item_data = {"sku": {"def": {"promotionPrice": "10.99", "price": "15.99"}}}
        price = scraper._get_price(item_data)
        assert price == Decimal("10.99")

    @pytest.mark.unit
    def test_get_price_range_takes_lower(self, scraper):
        """Para rangos de precio, debe tomar el valor más bajo."""
        item_data = {"sku": {"def": {"price": "10.99 - 15.99"}}}
        price = scraper._get_price(item_data)
        assert price == Decimal("10.99")

    # ========================================================================
    # Tests para imágenes
    # ========================================================================

    @pytest.mark.unit
    def test_get_images(self, scraper):
        """Debe extraer y normalizar URLs de imágenes."""
        item_data = {"images": ["//ae01.alicdn.com/img1.jpg", "https://ae01.alicdn.com/img2.jpg"]}
        images = scraper._get_images(item_data)

        assert len(images) == 2
        assert images[0].startswith("https:")
        assert images[1].startswith("https:")

    @pytest.mark.unit
    def test_ensure_absolute_url(self, scraper):
        """Debe convertir URLs relativas a absolutas."""
        assert scraper._ensure_absolute_url("//example.com/img.jpg") == "https://example.com/img.jpg"
        assert scraper._ensure_absolute_url("https://example.com/img.jpg") == "https://example.com/img.jpg"

    # ========================================================================
    # Tests para scrape completo
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.scrapers.aliexpress_scraper.get_item_detail")
    async def test_scrape_success(self, mock_get_item_detail, scraper, sample_aliexpress_product_data):
        """Debe scrapear correctamente un producto de AliExpress."""
        mock_get_item_detail.return_value = sample_aliexpress_product_data

        result = await scraper.scrape("https://www.aliexpress.com/item/1005001234567890.html")

        assert "data" in result
        data = result["data"]
        assert data["provider_id"] == "aliexpress"
        assert data["external_id"] == "1005001234567890"
        assert data["name"] == "AliExpress Test Product"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.scrapers.aliexpress_scraper.get_item_detail")
    async def test_scrape_handles_api_error(self, mock_get_item_detail, scraper):
        """Debe manejar errores de la API."""
        mock_get_item_detail.side_effect = HTTPException(status_code=400, detail="API Error")

        with pytest.raises(HTTPException) as exc_info:
            await scraper.scrape("https://www.aliexpress.com/item/1005001234567890.html")

        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_direct_returns_empty(self, scraper):
        """scrape_direct debe retornar diccionario vacío."""
        result = await scraper.scrape_direct("<html></html>")
        assert result == {}
