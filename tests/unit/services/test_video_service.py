"""
Tests para VideoService.
Verifica la generación de videos.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.requests.generate_video_request import GenerateVideoRequest, VideoType
from app.services.video_service import VideoService
from app.services.video_service_interface import VideoServiceInterface


class TestVideoService:
    """Tests para VideoService."""

    @pytest.fixture
    def mock_fal_client(self):
        """Mock para FalClient."""
        mock = MagicMock()
        mock.kling_image_to_video = AsyncMock(return_value={"video_url": "https://example.com/video.mp4"})
        mock.bytedance_omnihuman = AsyncMock(return_value={"video_url": "https://example.com/human.mp4"})
        return mock

    @pytest.fixture
    def service(self, mock_fal_client):
        """Crear instancia de VideoService con mock."""
        return VideoService(fal_client=mock_fal_client)

    @pytest.mark.unit
    def test_implements_interface(self, service):
        """Debe implementar VideoServiceInterface."""
        assert isinstance(service, VideoServiceInterface)

    # ========================================================================
    # Tests para generate_video - animated_scene
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_animated_scene(self, service, mock_fal_client):
        """Debe generar video de escena animada."""
        request = GenerateVideoRequest(
            type=VideoType.animated_scene,
            content={"prompt": "A beautiful sunset animation", "image_url": "https://example.com/image.jpg"},
        )

        result = await service.generate_video(request)

        assert result == {"video_url": "https://example.com/video.mp4"}
        mock_fal_client.kling_image_to_video.assert_called_once_with(
            prompt="A beautiful sunset animation", image_url="https://example.com/image.jpg", fal_webhook=None
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_animated_scene_with_webhook(self, service, mock_fal_client):
        """Debe generar video con webhook."""
        request = GenerateVideoRequest(
            type=VideoType.animated_scene,
            content={
                "prompt": "Animation",
                "image_url": "https://example.com/image.jpg",
                "fal_webhook": "https://webhook.example.com/callback",
            },
        )

        await service.generate_video(request)

        mock_fal_client.kling_image_to_video.assert_called_once()
        call_kwargs = mock_fal_client.kling_image_to_video.call_args[1]
        assert call_kwargs.get("fal_webhook") == "https://webhook.example.com/callback"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_animated_scene_missing_prompt(self, service):
        """Debe lanzar error si falta prompt."""
        request = GenerateVideoRequest(
            type=VideoType.animated_scene, content={"image_url": "https://example.com/image.jpg"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_video(request)

        assert exc_info.value.status_code == 400
        assert "prompt" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_animated_scene_missing_image(self, service):
        """Debe lanzar error si falta image_url."""
        request = GenerateVideoRequest(type=VideoType.animated_scene, content={"prompt": "Animation prompt"})

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_video(request)

        assert exc_info.value.status_code == 400
        assert "image_url" in exc_info.value.detail

    # ========================================================================
    # Tests para generate_video - human_scene
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_human_scene(self, service, mock_fal_client):
        """Debe generar video de escena humana."""
        request = GenerateVideoRequest(
            type=VideoType.human_scene,
            content={"image_url": "https://example.com/person.jpg", "audio_url": "https://example.com/audio.mp3"},
        )

        result = await service.generate_video(request)

        assert result == {"video_url": "https://example.com/human.mp4"}
        mock_fal_client.bytedance_omnihuman.assert_called_once_with(
            image_url="https://example.com/person.jpg", audio_url="https://example.com/audio.mp3", fal_webhook=None
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_human_scene_missing_image(self, service):
        """Debe lanzar error si falta image_url."""
        request = GenerateVideoRequest(
            type=VideoType.human_scene, content={"audio_url": "https://example.com/audio.mp3"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_video(request)

        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_human_scene_missing_audio(self, service):
        """Debe lanzar error si falta audio_url."""
        request = GenerateVideoRequest(
            type=VideoType.human_scene, content={"image_url": "https://example.com/person.jpg"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_video(request)

        assert exc_info.value.status_code == 400

    # ========================================================================
    # Tests para manejo de errores
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_video_fal_error(self, service, mock_fal_client):
        """Debe manejar errores de FAL correctamente."""
        mock_fal_client.kling_image_to_video.side_effect = Exception("FAL API Error")

        request = GenerateVideoRequest(
            type=VideoType.animated_scene, content={"prompt": "Animation", "image_url": "https://example.com/image.jpg"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_video(request)

        assert exc_info.value.status_code == 502
        assert "FAL" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_video_extra_params(self, service, mock_fal_client):
        """Debe pasar parámetros extra a FAL."""
        request = GenerateVideoRequest(
            type=VideoType.animated_scene,
            content={"prompt": "Animation", "image_url": "https://example.com/image.jpg", "duration": 5, "fps": 30},
        )

        await service.generate_video(request)

        call_kwargs = mock_fal_client.kling_image_to_video.call_args[1]
        assert call_kwargs.get("duration") == 5
        assert call_kwargs.get("fps") == 30
