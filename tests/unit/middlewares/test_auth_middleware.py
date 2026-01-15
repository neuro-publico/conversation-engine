"""
Tests para auth_middleware.
Verifica la autenticación por API Key y Bearer Token.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.middlewares.auth_middleware import require_api_key, require_auth, verify_api_key, verify_user_token


class TestVerifyApiKey:
    """Tests para verify_api_key."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_api_key_success(self):
        """Debe retornar True para API key válida."""
        with patch("app.middlewares.auth_middleware.API_KEY", "valid-api-key"):
            result = await verify_api_key("valid-api-key")
            assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_api_key_missing(self):
        """Debe lanzar 401 si no se proporciona API key."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(None)

        assert exc_info.value.status_code == 401
        assert "not provided" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_api_key_empty(self):
        """Debe lanzar 401 si API key está vacía."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key("")

        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self):
        """Debe lanzar 401 si API key es inválida."""
        with patch("app.middlewares.auth_middleware.API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key("wrong-api-key")

            assert exc_info.value.status_code == 401
            assert "Invalid" in exc_info.value.detail


class TestRequireApiKey:
    """Tests para el decorador require_api_key."""

    @pytest.fixture
    def mock_request(self):
        """Mock de FastAPI Request."""
        mock = MagicMock()
        mock.headers = MagicMock()
        mock.headers.get = MagicMock(return_value="valid-api-key")
        return mock

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_require_api_key_success(self, mock_request):
        """Debe ejecutar función cuando API key es válida."""
        with patch("app.middlewares.auth_middleware.API_KEY", "valid-api-key"):

            @require_api_key
            async def protected_function(request):
                return {"success": True}

            result = await protected_function(mock_request)

            assert result == {"success": True}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_require_api_key_missing_request(self):
        """Debe lanzar 500 si request es None."""

        @require_api_key
        async def protected_function(request):
            return {"success": True}

        with pytest.raises(HTTPException) as exc_info:
            await protected_function(None)

        assert exc_info.value.status_code == 500

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_require_api_key_invalid(self, mock_request):
        """Debe lanzar 401 si API key es inválida."""
        mock_request.headers.get.return_value = "wrong-key"

        with patch("app.middlewares.auth_middleware.API_KEY", "valid-api-key"):

            @require_api_key
            async def protected_function(request):
                return {"success": True}

            with pytest.raises(HTTPException) as exc_info:
                await protected_function(mock_request)

            assert exc_info.value.status_code == 401


class TestVerifyUserToken:
    """Tests para verify_user_token."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_token_missing(self):
        """Debe lanzar 401 si no hay token."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_user_token(None)

        assert exc_info.value.status_code == 401
        assert "not provided" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_token_empty(self):
        """Debe lanzar 401 si token está vacío."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_user_token("")

        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.middlewares.auth_middleware.httpx.AsyncClient")
    async def test_verify_token_success(self, mock_client_class):
        """Debe retornar datos del usuario para token válido."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user_id": "123", "name": "Test User"}

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        with patch("app.middlewares.auth_middleware.AUTH_SERVICE_URL", "http://auth.example.com"):
            result = await verify_user_token("Bearer valid-token")

            assert result == {"user_id": "123", "name": "Test User"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """Debe lanzar 401 para token inválido."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("app.middlewares.auth_middleware.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("app.middlewares.auth_middleware.AUTH_SERVICE_URL", "http://auth.example.com"):
                with pytest.raises(HTTPException) as exc_info:
                    await verify_user_token("Bearer invalid-token")

                assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_token_network_error(self):
        """Debe lanzar 500 si hay error de red."""
        import httpx

        with patch("app.middlewares.auth_middleware.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(side_effect=httpx.RequestError("Network error", request=MagicMock()))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("app.middlewares.auth_middleware.AUTH_SERVICE_URL", "http://auth.example.com"):
                with pytest.raises(HTTPException) as exc_info:
                    await verify_user_token("Bearer token")

                assert exc_info.value.status_code == 500
                assert "Error verifying" in exc_info.value.detail


class TestRequireAuth:
    """Tests para el decorador require_auth."""

    @pytest.fixture
    def mock_request(self):
        """Mock de FastAPI Request."""
        mock = MagicMock()
        mock.headers = MagicMock()
        mock.headers.get = MagicMock(return_value="Bearer valid-token")
        mock.state = MagicMock()
        return mock

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.middlewares.auth_middleware.verify_user_token")
    async def test_require_auth_success(self, mock_verify, mock_request):
        """Debe ejecutar función y agregar user_info al state."""
        mock_verify.return_value = {"user_id": "123"}

        @require_auth
        async def protected_function(request):
            return {"user": request.state.user_info}

        result = await protected_function(mock_request)

        assert result == {"user": {"user_id": "123"}}
        assert mock_request.state.user_info == {"user_id": "123"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_require_auth_missing_request(self):
        """Debe lanzar 500 si request es None."""

        @require_auth
        async def protected_function(request):
            return {"success": True}

        with pytest.raises(HTTPException) as exc_info:
            await protected_function(None)

        assert exc_info.value.status_code == 500

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.middlewares.auth_middleware.verify_user_token")
    async def test_require_auth_invalid_token(self, mock_verify, mock_request):
        """Debe lanzar 401 si token es inválido."""
        mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid token")

        @require_auth
        async def protected_function(request):
            return {"success": True}

        with pytest.raises(HTTPException) as exc_info:
            await protected_function(mock_request)

        assert exc_info.value.status_code == 401
