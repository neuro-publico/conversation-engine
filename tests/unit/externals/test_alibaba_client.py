"""
Tests para alibaba_client.
Verifica la integración con Alibaba DataHub API.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAlibabaClient:
    """Tests para alibaba_client."""

    @pytest.fixture
    def mock_httpx_response(self):
        """Mock de respuesta httpx."""
        mock = MagicMock()
        mock.json.return_value = {"result": {"item": {"title": "Test Product"}}}
        mock.raise_for_status = MagicMock()
        return mock

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.alibaba.alibaba_client.httpx.AsyncClient")
    async def test_get_item_detail_success(self, mock_client_class, mock_httpx_response):
        """Debe obtener detalles de un item correctamente."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_httpx_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.alibaba.alibaba_client import get_item_detail

        result = await get_item_detail("123456")

        assert result == {"result": {"item": {"title": "Test Product"}}}
        mock_client.get.assert_called_once()
        call_kwargs = mock_client.get.call_args
        assert call_kwargs.kwargs["params"] == {"itemId": "123456"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.alibaba.alibaba_client.httpx.AsyncClient")
    async def test_get_item_detail_sends_correct_headers(self, mock_client_class, mock_httpx_response):
        """Debe enviar los headers de RapidAPI correctamente."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_httpx_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.alibaba.alibaba_client import get_item_detail

        await get_item_detail("789")

        call_kwargs = mock_client.get.call_args
        headers = call_kwargs.kwargs["headers"]
        assert "x-rapidapi-host" in headers
        assert "x-rapidapi-key" in headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.alibaba.alibaba_client.httpx.AsyncClient")
    async def test_get_item_detail_uses_timeout(self, mock_client_class, mock_httpx_response):
        """Debe usar timeout de 30 segundos."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_httpx_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.alibaba.alibaba_client import get_item_detail

        await get_item_detail("123")

        call_kwargs = mock_client.get.call_args
        assert call_kwargs.kwargs["timeout"] == 30.0
