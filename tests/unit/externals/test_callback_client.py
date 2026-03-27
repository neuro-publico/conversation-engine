"""
Tests para callback_client.
Verifica el envio de resultados via webhook con reintentos.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.externals.callback.callback_client import post_callback


class TestCallbackClient:
    """Tests para post_callback."""

    @pytest.fixture
    def payload(self):
        return {"status": "success", "request_id": "abc-123", "s3_url": "https://s3.example.com/img.png"}

    @pytest.mark.unit
    async def test_post_callback_success(self, payload):
        """Debe hacer POST exitoso al callback URL."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.externals.callback.callback_client.httpx.AsyncClient", return_value=mock_client):
            await post_callback("https://example.com/webhook", payload, api_key="test-key")

        mock_client.post.assert_called_once_with(
            "https://example.com/webhook",
            json=payload,
            headers={"x-api-key": "test-key", "Content-Type": "application/json"},
        )

    @pytest.mark.unit
    async def test_post_callback_retries_on_failure(self, payload):
        """Debe reintentar hasta max_retries veces en caso de error."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Connection error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.externals.callback.callback_client.httpx.AsyncClient", return_value=mock_client):
            with patch("app.externals.callback.callback_client.asyncio.sleep", new_callable=AsyncMock):
                await post_callback("https://example.com/webhook", payload, max_retries=3, api_key="test-key")

        assert mock_client.post.call_count == 3

    @pytest.mark.unit
    async def test_post_callback_succeeds_on_second_attempt(self, payload):
        """Debe parar de reintentar despues de un exito."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[httpx.HTTPError("fail"), mock_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.externals.callback.callback_client.httpx.AsyncClient", return_value=mock_client):
            with patch("app.externals.callback.callback_client.asyncio.sleep", new_callable=AsyncMock):
                await post_callback("https://example.com/webhook", payload, max_retries=3, api_key="test-key")

        assert mock_client.post.call_count == 2

    @pytest.mark.unit
    async def test_post_callback_uses_api_key_from_config(self, payload):
        """Debe usar API_KEY de config cuando no se pasa api_key."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.externals.callback.callback_client.httpx.AsyncClient", return_value=mock_client):
            with patch("app.externals.callback.callback_client.API_KEY", "config-api-key"):
                await post_callback("https://example.com/webhook", payload)

        call_headers = mock_client.post.call_args[1]["headers"]
        assert call_headers["x-api-key"] == "config-api-key"
