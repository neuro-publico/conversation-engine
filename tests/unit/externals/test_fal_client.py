"""
Tests para FalClient.
Verifica la integración con FAL AI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.externals.fal.fal_client import FalClient


class TestFalClient:
    """Tests para FalClient."""

    @pytest.fixture
    def client(self):
        """Crear instancia de FalClient con API key."""
        return FalClient(api_key="test-api-key")

    @pytest.fixture
    def mock_httpx_response(self):
        """Mock de respuesta httpx."""
        mock = MagicMock()
        mock.json.return_value = {"result": "success"}
        mock.raise_for_status = MagicMock()
        return mock

    @pytest.mark.unit
    def test_initialization_with_api_key(self, client):
        """Debe inicializarse con API key proporcionada."""
        assert client.api_key == "test-api-key"

    @pytest.mark.unit
    def test_initialization_from_env(self):
        """Debe usar API key de variable de entorno."""
        with patch("app.externals.fal.fal_client.FAL_AI_API_KEY", "env-api-key"):
            client = FalClient()
            assert client.api_key == "env-api-key"

    # ========================================================================
    # Tests para _post
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.fal.fal_client.httpx.AsyncClient")
    async def test_post_success(self, mock_client_class, client, mock_httpx_response):
        """Debe realizar POST correctamente."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_httpx_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await client._post("test/path", {"key": "value"})

        assert result == {"result": "success"}
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.fal.fal_client.httpx.AsyncClient")
    async def test_post_with_webhook(self, mock_client_class, client, mock_httpx_response):
        """Debe incluir webhook en URL."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_httpx_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        await client._post("test/path", {"key": "value"}, fal_webhook="https://callback.example.com")

        call_args = mock_client.post.call_args
        assert "fal_webhook" in call_args[0][0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_post_without_api_key_raises(self):
        """Debe lanzar error si no hay API key."""
        client = FalClient(api_key=None)

        with pytest.raises(ValueError) as exc_info:
            await client._post("test/path", {})

        assert "FAL_AI_API_KEY" in str(exc_info.value)

    # ========================================================================
    # Tests para tts_multilingual_v2
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(FalClient, "_post")
    async def test_tts_multilingual_v2(self, mock_post, client):
        """Debe llamar a TTS endpoint correctamente."""
        mock_post.return_value = {"audio_url": "https://example.com/audio.mp3"}

        result = await client.tts_multilingual_v2(text="Hello world")

        mock_post.assert_called_once_with("fal-ai/elevenlabs/tts/multilingual-v2", {"text": "Hello world"}, None)
        assert result["audio_url"] == "https://example.com/audio.mp3"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(FalClient, "_post")
    async def test_tts_with_extra_params(self, mock_post, client):
        """Debe pasar parámetros extra."""
        mock_post.return_value = {"audio_url": "https://example.com/audio.mp3"}

        await client.tts_multilingual_v2(text="Hello", voice_id="custom_voice", speed=1.5)

        call_args = mock_post.call_args
        payload = call_args[0][1]
        assert payload["voice_id"] == "custom_voice"
        assert payload["speed"] == 1.5

    # ========================================================================
    # Tests para bytedance_omnihuman
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(FalClient, "_post")
    async def test_bytedance_omnihuman(self, mock_post, client):
        """Debe llamar a OmniHuman endpoint correctamente."""
        mock_post.return_value = {"video_url": "https://example.com/video.mp4"}

        result = await client.bytedance_omnihuman(
            image_url="https://example.com/image.jpg", audio_url="https://example.com/audio.mp3"
        )

        mock_post.assert_called_once_with(
            "fal-ai/bytedance/omnihuman",
            {"image_url": "https://example.com/image.jpg", "audio_url": "https://example.com/audio.mp3"},
            None,
        )
        assert result["video_url"] == "https://example.com/video.mp4"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(FalClient, "_post")
    async def test_bytedance_omnihuman_with_webhook(self, mock_post, client):
        """Debe incluir webhook."""
        mock_post.return_value = {"request_id": "123"}

        await client.bytedance_omnihuman(
            image_url="https://example.com/image.jpg",
            audio_url="https://example.com/audio.mp3",
            fal_webhook="https://callback.example.com",
        )

        call_args = mock_post.call_args
        assert call_args[0][2] == "https://callback.example.com"

    # ========================================================================
    # Tests para kling_image_to_video
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(FalClient, "_post")
    async def test_kling_image_to_video(self, mock_post, client):
        """Debe llamar a Kling endpoint correctamente."""
        mock_post.return_value = {"video_url": "https://example.com/video.mp4"}

        result = await client.kling_image_to_video(
            prompt="A beautiful animation", image_url="https://example.com/image.jpg"
        )

        mock_post.assert_called_once_with(
            "fal-ai/kling-video/v2/master/image-to-video",
            {"prompt": "A beautiful animation", "image_url": "https://example.com/image.jpg"},
            None,
        )
        assert result["video_url"] == "https://example.com/video.mp4"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(FalClient, "_post")
    async def test_kling_with_extra_params(self, mock_post, client):
        """Debe pasar parámetros extra como duración."""
        mock_post.return_value = {"video_url": "https://example.com/video.mp4"}

        await client.kling_image_to_video(
            prompt="Animation", image_url="https://example.com/image.jpg", duration=10, fps=30
        )

        call_args = mock_post.call_args
        payload = call_args[0][1]
        assert payload["duration"] == 10
        assert payload["fps"] == 30
