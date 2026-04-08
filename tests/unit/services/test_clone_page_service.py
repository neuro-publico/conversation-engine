"""
Tests para ClonePageService.
Verifica el servicio de clonación de páginas.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.requests.clone_page_request import ClonePageRequest
from app.responses.clone_page_response import ClonePageResponse
from app.services.clone_page_service import ClonePageService
from app.services.clone_page_service_interface import ClonePageServiceInterface


class TestClonePageService:
    """Tests para ClonePageService."""

    @pytest.fixture
    def service(self):
        return ClonePageService()

    @pytest.fixture
    def mock_scrape_response(self):
        return {
            "content": "<html><body><h1>Test Page</h1></body></html>",
            "screenshot": "base64screenshotdata",
        }

    @pytest.fixture
    def mock_ai_response(self):
        return json.dumps(
            {
                "html": "<!DOCTYPE html><html><head></head><body><h1>Cloned</h1></body></html>",
                "images": ["https://example.com/img1.jpg"],
                "metadata": {
                    "title": "Test Page",
                    "colors": ["#ffffff", "#000000"],
                    "fonts": ["Inter"],
                },
            }
        )

    @pytest.mark.unit
    def test_implements_interface(self, service):
        """Debe implementar ClonePageServiceInterface."""
        assert isinstance(service, ClonePageServiceInterface)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clone_page_success(self, service, mock_scrape_response, mock_ai_response):
        """Debe clonar una página correctamente."""
        request = ClonePageRequest(url="https://example.com/landing")

        with patch("app.services.clone_page_service.aiohttp") as mock_aiohttp:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_scrape_response)

            mock_session = AsyncMock()
            mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_aiohttp.ClientSession = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
            )
            mock_aiohttp.ClientTimeout = MagicMock()

            mock_llm_response = MagicMock()
            mock_llm_response.content = mock_ai_response

            with patch("app.services.clone_page_service.ChatAnthropic") as mock_anthropic:
                mock_llm = AsyncMock()
                mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
                mock_anthropic.return_value = mock_llm

                result = await service.clone_page(request)

                assert isinstance(result, ClonePageResponse)
                assert "<h1>Cloned</h1>" in result.html
                assert result.metadata.original_url == "https://example.com/landing"
                assert result.metadata.title == "Test Page"
                assert len(result.images) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_page_error(self, service):
        """Debe lanzar HTTPException si el scraper falla."""
        request = ClonePageRequest(url="https://example.com/landing")

        with patch("app.services.clone_page_service.aiohttp") as mock_aiohttp:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")

            mock_session = AsyncMock()
            mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_aiohttp.ClientSession = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
            )
            mock_aiohttp.ClientTimeout = MagicMock()

            with pytest.raises(HTTPException) as exc_info:
                await service._scrape_page("https://example.com/landing")

            assert exc_info.value.status_code == 400

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scrape_page_empty_html(self, service):
        """Debe lanzar HTTPException si el HTML está vacío."""
        with patch("app.services.clone_page_service.aiohttp") as mock_aiohttp:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"content": "", "screenshot": "abc"})

            mock_session = AsyncMock()
            mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_aiohttp.ClientSession = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session))
            )
            mock_aiohttp.ClientTimeout = MagicMock()

            with pytest.raises(HTTPException) as exc_info:
                await service._scrape_page("https://example.com")

            assert "empty HTML" in exc_info.value.detail

    @pytest.mark.unit
    def test_parse_response_valid_json(self, service):
        """Debe parsear JSON válido directamente."""
        raw = json.dumps({"html": "<html></html>", "images": [], "metadata": {}})
        result = service._parse_response(raw)
        assert result["html"] == "<html></html>"

    @pytest.mark.unit
    def test_parse_response_json_in_code_block(self, service):
        """Debe extraer JSON de un bloque de código markdown."""
        raw = '```json\n{"html": "<html></html>", "images": [], "metadata": {}}\n```'
        result = service._parse_response(raw)
        assert result["html"] == "<html></html>"

    @pytest.mark.unit
    def test_parse_response_invalid_json_raises(self, service):
        """Debe lanzar HTTPException si no puede parsear la respuesta."""
        with pytest.raises(HTTPException) as exc_info:
            service._parse_response("This is not JSON at all")

        assert exc_info.value.status_code == 500
