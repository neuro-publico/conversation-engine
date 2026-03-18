"""
Tests para MercadoLibreScraper.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.scrapers.mercadolibre_scraper import MercadoLibreScraper
from app.scrapers.scraper_interface import ScraperInterface

MOCK_PRODUCT = {
    "id": "MCO52063439",
    "name": "Leche Deslactosada Alqueria 1L x6",
    "main_features": [{"text": "Sin lactosa"}, {"text": "Pack x6 unidades"}],
    "buy_box_winner": {"price": 29900.0},
    "pictures": [
        {"url": "https://example.com/img1.jpg"},
        {"url": "https://example.com/img2.jpg"},
    ],
}


class TestMercadoLibreScraper:
    @pytest.fixture
    def scraper(self):
        return MercadoLibreScraper()

    @pytest.mark.unit
    def test_implements_interface(self, scraper):
        assert isinstance(scraper, ScraperInterface)

    # ------------------------------------------------------------------ #
    # _extract_product_id
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url,expected_id",
        [
            ("https://www.mercadolibre.com.co/producto/p/MCO52063439", "MCO52063439"),
            ("https://www.mercadolibre.com.co/leche/p/MCO52063439?q=leche", "MCO52063439"),
            ("https://www.mercadolibre.com.co/MCO62607084", "MCO62607084"),
            ("https://api.mercadolibre.com/products/MCO62607084", "MCO62607084"),
        ],
    )
    def test_extract_product_id_valid(self, scraper, url, expected_id):
        assert scraper._extract_product_id(url) == expected_id

    @pytest.mark.unit
    def test_extract_product_id_invalid_raises(self, scraper):
        with pytest.raises(HTTPException) as exc:
            scraper._extract_product_id("https://www.mercadolibre.com.co/sin-id")
        assert exc.value.status_code == 400

    # ------------------------------------------------------------------ #
    # _get_description
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    def test_get_description_from_main_features(self, scraper):
        data = {"main_features": [{"text": "Sin lactosa"}, {"text": "Pack x6"}]}
        assert scraper._get_description(data) == "Sin lactosa\nPack x6"

    @pytest.mark.unit
    def test_get_description_from_short_description(self, scraper):
        data = {"short_description": {"content": "Descripcion corta"}}
        assert scraper._get_description(data) == "Descripcion corta"

    @pytest.mark.unit
    def test_get_description_empty(self, scraper):
        assert scraper._get_description({}) == ""

    # ------------------------------------------------------------------ #
    # _get_price
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    def test_get_price_from_buy_box(self, scraper):
        data = {"buy_box_winner": {"price": 29900.0}}
        assert scraper._get_price(data) == 29900.0

    @pytest.mark.unit
    def test_get_price_none_when_missing(self, scraper):
        assert scraper._get_price({}) is None

    # ------------------------------------------------------------------ #
    # _get_images
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    def test_get_images(self, scraper):
        data = {"pictures": [{"url": "https://img1.jpg"}, {"url": "https://img2.jpg"}]}
        assert scraper._get_images(data) == ["https://img1.jpg", "https://img2.jpg"]

    @pytest.mark.unit
    def test_get_images_empty(self, scraper):
        assert scraper._get_images({}) == []

    # ------------------------------------------------------------------ #
    # scrape
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_returns_formatted_data(self, scraper):
        with patch(
            "app.scrapers.mercadolibre_scraper.get_product_details",
            new=AsyncMock(return_value=MOCK_PRODUCT),
        ):
            result = await scraper.scrape("https://www.mercadolibre.com.co/p/MCO52063439")

        data = result["data"]
        assert data["provider_id"] == "mercadolibre"
        assert data["external_id"] == "MCO52063439"
        assert data["name"] == "Leche Deslactosada Alqueria 1L x6"
        assert data["external_sell_price"] == 29900.0
        assert len(data["images"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_raises_on_api_error(self, scraper):
        with patch(
            "app.scrapers.mercadolibre_scraper.get_product_details",
            new=AsyncMock(side_effect=Exception("connection error")),
        ):
            with pytest.raises(HTTPException) as exc:
                await scraper.scrape("https://www.mercadolibre.com.co/p/MCO52063439")
        assert exc.value.status_code == 400

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_direct_returns_empty(self, scraper):
        result = await scraper.scrape_direct("<html></html>")
        assert result == {}
