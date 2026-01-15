"""
Tests para AmazonScraper.
Verifica la extracción de datos de productos de Amazon.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.scrapers.amazon_scraper import AmazonScraper
from app.scrapers.scraper_interface import ScraperInterface


class TestAmazonScraper:
    """Tests para AmazonScraper."""

    @pytest.fixture
    def scraper(self):
        """Crear instancia de AmazonScraper."""
        return AmazonScraper()

    @pytest.mark.unit
    def test_implements_interface(self, scraper):
        """Debe implementar ScraperInterface."""
        assert isinstance(scraper, ScraperInterface)

    # ========================================================================
    # Tests para extracción de ASIN
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url,expected_asin",
        [
            ("https://www.amazon.com/dp/B08N5WRWNW", "B08N5WRWNW"),
            ("https://www.amazon.com/gp/product/B08N5WRWNW", "B08N5WRWNW"),
            ("https://amazon.com/ASIN/B08N5WRWNW", "B08N5WRWNW"),
            ("https://www.amazon.com/product?asin=B08N5WRWNW", "B08N5WRWNW"),
            ("https://www.amazon.es/dp/B08N5WRWNW/ref=test", "B08N5WRWNW"),
        ],
    )
    def test_extract_asin_valid_urls(self, scraper, url, expected_asin):
        """Debe extraer correctamente el ASIN de URLs válidas."""
        asin = scraper._extract_asin(url)
        assert asin == expected_asin

    @pytest.mark.unit
    def test_extract_asin_invalid_url_raises_exception(self, scraper):
        """Debe lanzar HTTPException para URLs sin ASIN válido."""
        invalid_urls = [
            "https://www.amazon.com/search/test",
            "https://www.amazon.com/",
            "https://www.google.com/search",
        ]

        for url in invalid_urls:
            with pytest.raises(HTTPException) as exc_info:
                scraper._extract_asin(url)
            assert exc_info.value.status_code == 400
            assert "Invalid Amazon URL" in exc_info.value.detail

    # ========================================================================
    # Tests para extracción de datos del producto
    # ========================================================================

    @pytest.mark.unit
    def test_get_name(self, scraper):
        """Debe extraer el nombre del producto."""
        product_data = {"product_title": "Test Product Name"}
        assert scraper._get_name(product_data) == "Test Product Name"

        product_data = {"title": "Alternative Title"}
        assert scraper._get_name(product_data) == "Alternative Title"

        product_data = {}
        assert scraper._get_name(product_data) == ""

    @pytest.mark.unit
    def test_get_description(self, scraper):
        """Debe extraer la descripción del producto."""
        # Con product_description
        product_data = {"product_description": "Test description"}
        assert scraper._get_description(product_data) == "Test description"

        # Con about_product
        product_data = {"about_product": ["Feature 1", "Feature 2"]}
        assert scraper._get_description(product_data) == "Feature 1\nFeature 2"

        # Sin descripción
        product_data = {}
        assert scraper._get_description(product_data) == ""

    @pytest.mark.unit
    def test_get_price(self, scraper):
        """Debe extraer y parsear el precio."""
        product_data = {"product_price": "$49.99"}
        price = scraper._get_price(product_data)
        assert price == Decimal("49.99")

        # Con pricing object
        product_data = {"pricing": {"current_price": "29.99"}}
        price = scraper._get_price(product_data)
        assert price == Decimal("29.99")

        # Sin precio
        product_data = {}
        price = scraper._get_price(product_data)
        assert price is None

    @pytest.mark.unit
    def test_get_images(self, scraper):
        """Debe extraer las imágenes del producto."""
        # Con product_photos
        product_data = {"product_photos": ["img1.jpg", "img2.jpg"]}
        images = scraper._get_images(product_data)
        assert images == ["img1.jpg", "img2.jpg"]

        # Con main_image e images
        product_data = {"product_photo": "main.jpg", "images": ["extra1.jpg", "extra2.jpg"]}
        images = scraper._get_images(product_data)
        assert "main.jpg" in images
        assert len(images) == 3

    # ========================================================================
    # Tests para variantes
    # ========================================================================

    @pytest.mark.unit
    def test_get_variant_attributes(self, scraper):
        """Debe extraer atributos de variantes correctamente."""
        dimensions = ["color", "size"]
        variant_data = {"color": "Red", "size": "Large"}

        attributes = scraper._get_variant_attributes(dimensions, variant_data)

        assert len(attributes) == 2
        assert {"category_name": "Color", "value": "Red"} in attributes
        assert {"category_name": "Size", "value": "Large"} in attributes

    @pytest.mark.unit
    def test_extract_variants_empty_when_no_data(self, scraper):
        """Debe retornar lista vacía cuando no hay datos de variantes."""
        product_data = {}
        variants = scraper._extract_variants(product_data)
        assert variants == []

        product_data = {"product_variations_dimensions": []}
        variants = scraper._extract_variants(product_data)
        assert variants == []

    # ========================================================================
    # Tests para scrape completo
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.scrapers.amazon_scraper.get_product_details")
    async def test_scrape_success(self, mock_get_product_details, scraper, sample_amazon_product_data):
        """Debe scrapear correctamente un producto de Amazon."""
        mock_get_product_details.return_value = sample_amazon_product_data

        result = await scraper.scrape("https://www.amazon.com/dp/B08N5WRWNW")

        assert "data" in result
        data = result["data"]
        assert data["provider_id"] == "amazon"
        assert data["external_id"] == "B08N5WRWNW"
        assert data["name"] == "Amazon Test Product"
        assert "images" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.scrapers.amazon_scraper.get_product_details")
    async def test_scrape_handles_api_error(self, mock_get_product_details, scraper):
        """Debe manejar errores de la API de Amazon."""
        mock_get_product_details.side_effect = Exception("API Error")

        with pytest.raises(HTTPException) as exc_info:
            await scraper.scrape("https://www.amazon.com/dp/B08N5WRWNW")

        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_direct_returns_empty(self, scraper):
        """scrape_direct debe retornar diccionario vacío."""
        result = await scraper.scrape_direct("<html></html>")
        assert result == {}
