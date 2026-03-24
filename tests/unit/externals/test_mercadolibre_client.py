"""
Tests para mercadolibre_client.
Verifica la integración con MercadoLibre API y el manejo de tokens OAuth.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestMercadoLibreClient:
    """Tests para mercadolibre_client."""

    @pytest.fixture(autouse=True)
    def reset_token_cache(self):
        """Resetear cache de token entre tests."""
        import app.externals.mercadolibre.mercadolibre_client as ml

        ml._cached_token = None
        ml._token_expires_at = 0
        yield
        ml._cached_token = None
        ml._token_expires_at = 0

    @pytest.fixture
    def mock_token_response(self):
        """Mock de respuesta de token OAuth."""
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"access_token": "test-token-123", "expires_in": 21600}
        mock.raise_for_status = MagicMock()
        return mock

    @pytest.fixture
    def mock_product_response(self):
        """Mock de respuesta de producto."""
        mock = MagicMock()
        mock.json.return_value = {"id": "MCO123", "name": "Test Product", "pictures": []}
        mock.raise_for_status = MagicMock()
        return mock

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.mercadolibre.mercadolibre_client.httpx.AsyncClient")
    async def test_get_access_token_fetches_new_token(self, mock_client_class, mock_token_response):
        """Debe obtener un nuevo token cuando no hay cache."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_token_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.mercadolibre.mercadolibre_client import _get_access_token

        token = await _get_access_token()

        assert token == "test-token-123"
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_access_token_uses_cached_token(self):
        """Debe usar token cacheado si no ha expirado."""
        import app.externals.mercadolibre.mercadolibre_client as ml

        ml._cached_token = "cached-token"
        ml._token_expires_at = time.time() + 3600

        token = await ml._get_access_token()

        assert token == "cached-token"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.mercadolibre.mercadolibre_client.httpx.AsyncClient")
    async def test_get_access_token_refreshes_expired_token(self, mock_client_class, mock_token_response):
        """Debe refrescar token cuando ha expirado."""
        import app.externals.mercadolibre.mercadolibre_client as ml

        ml._cached_token = "old-token"
        ml._token_expires_at = time.time() - 100

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_token_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        token = await ml._get_access_token()

        assert token == "test-token-123"
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.mercadolibre.mercadolibre_client._get_access_token", new_callable=AsyncMock)
    @patch("app.externals.mercadolibre.mercadolibre_client.httpx.AsyncClient")
    async def test_get_product_details_success(self, mock_client_class, mock_get_token, mock_product_response):
        """Debe obtener detalles del producto correctamente."""
        mock_get_token.return_value = "test-token"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_product_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.mercadolibre.mercadolibre_client import get_product_details

        result = await get_product_details("MCO123")

        assert result["id"] == "MCO123"
        assert result["name"] == "Test Product"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.mercadolibre.mercadolibre_client._get_access_token", new_callable=AsyncMock)
    @patch("app.externals.mercadolibre.mercadolibre_client.httpx.AsyncClient")
    async def test_get_product_details_sends_auth_header(
        self, mock_client_class, mock_get_token, mock_product_response
    ):
        """Debe enviar header de Authorization con Bearer token."""
        mock_get_token.return_value = "my-token"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_product_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.mercadolibre.mercadolibre_client import get_product_details

        await get_product_details("MCO456")

        call_kwargs = mock_client.get.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer my-token"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.mercadolibre.mercadolibre_client._get_access_token", new_callable=AsyncMock)
    @patch("app.externals.mercadolibre.mercadolibre_client.httpx.AsyncClient")
    async def test_get_product_details_raises_on_http_error(self, mock_client_class, mock_get_token):
        """Debe propagar errores HTTP."""
        mock_get_token.return_value = "test-token"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.mercadolibre.mercadolibre_client import get_product_details

        with pytest.raises(httpx.HTTPStatusError):
            await get_product_details("INVALID")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.mercadolibre.mercadolibre_client.httpx.AsyncClient")
    async def test_get_access_token_raises_on_auth_error(self, mock_client_class):
        """Debe propagar errores de autenticación OAuth."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        )
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        from app.externals.mercadolibre.mercadolibre_client import _get_access_token

        with pytest.raises(httpx.HTTPStatusError):
            await _get_access_token()
