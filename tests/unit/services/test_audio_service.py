"""
Tests para AudioService.
Verifica la generación de audio.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.requests.generate_audio_request import GenerateAudioRequest
from app.services.audio_service import AudioService
from app.services.audio_service_interface import AudioServiceInterface


class TestAudioService:
    """Tests para AudioService."""

    @pytest.fixture
    def mock_fal_client(self):
        """Mock para FalClient."""
        mock = MagicMock()
        mock.tts_multilingual_v2 = AsyncMock(
            return_value={"audio_url": "https://example.com/audio.mp3", "duration": 5.5}
        )
        return mock

    @pytest.fixture
    def service(self, mock_fal_client):
        """Crear instancia de AudioService con mock."""
        return AudioService(fal_client=mock_fal_client)

    @pytest.mark.unit
    def test_implements_interface(self, service):
        """Debe implementar AudioServiceInterface."""
        assert isinstance(service, AudioServiceInterface)

    # ========================================================================
    # Tests para generate_audio
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_audio_success(self, service, mock_fal_client):
        """Debe generar audio correctamente."""
        request = GenerateAudioRequest(text="Hello, this is a test message.")

        result = await service.generate_audio(request)

        assert result == {"audio_url": "https://example.com/audio.mp3", "duration": 5.5}
        mock_fal_client.tts_multilingual_v2.assert_called_once_with(
            text="Hello, this is a test message.", fal_webhook=None
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_audio_with_webhook(self, service, mock_fal_client):
        """Debe generar audio con webhook."""
        request = GenerateAudioRequest(
            text="Test message", content={"fal_webhook": "https://webhook.example.com/callback"}
        )

        await service.generate_audio(request)

        call_args = mock_fal_client.tts_multilingual_v2.call_args
        assert call_args[1].get("fal_webhook") == "https://webhook.example.com/callback"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_audio_with_extra_params(self, service, mock_fal_client):
        """Debe pasar parámetros extra a FAL."""
        request = GenerateAudioRequest(text="Test message", content={"voice_id": "custom_voice", "speed": 1.2})

        await service.generate_audio(request)

        call_kwargs = mock_fal_client.tts_multilingual_v2.call_args[1]
        assert call_kwargs.get("voice_id") == "custom_voice"
        assert call_kwargs.get("speed") == 1.2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_audio_missing_text(self, service):
        """Debe lanzar error si falta texto."""
        request = GenerateAudioRequest(text="")

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_audio(request)

        assert exc_info.value.status_code == 400
        assert "text" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_audio_fal_error(self, service, mock_fal_client):
        """Debe manejar errores de FAL correctamente."""
        mock_fal_client.tts_multilingual_v2.side_effect = Exception("FAL API Error")

        request = GenerateAudioRequest(text="Test message")

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_audio(request)

        assert exc_info.value.status_code == 502
        assert "FAL" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_audio_long_text(self, service, mock_fal_client):
        """Debe manejar textos largos."""
        long_text = "This is a long text. " * 100
        request = GenerateAudioRequest(text=long_text)

        await service.generate_audio(request)

        call_args = mock_fal_client.tts_multilingual_v2.call_args
        assert call_args[1]["text"] == long_text
