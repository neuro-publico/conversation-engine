"""
Tests para ImageService.
Verifica la generación y procesamiento de imágenes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.requests.generate_image_request import GenerateImageRequest
from app.requests.variation_image_request import VariationImageRequest
from app.services.image_service import ImageService
from app.services.image_service_interface import ImageServiceInterface


class TestImageService:
    """Tests para ImageService."""

    @pytest.fixture
    def mock_message_service(self):
        """Mock para MessageService."""
        mock = MagicMock()
        mock.handle_message_with_config = AsyncMock(
            return_value={
                "message": {"text": "Generate a product image with blue background"},
                "agent_config": MagicMock(
                    provider_ai="openai", model_ai="dall-e-3", preferences=MagicMock(extra_parameters=None)
                ),
            }
        )
        return mock

    @pytest.fixture
    def service(self, mock_message_service):
        """Crear instancia de ImageService con mocks."""
        return ImageService(message_service=mock_message_service)

    @pytest.mark.unit
    def test_implements_interface(self, service):
        """Debe implementar ImageServiceInterface."""
        assert isinstance(service, ImageServiceInterface)

    # ========================================================================
    # Tests para _upload_to_s3
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.image_service.upload_file")
    @patch("app.services.image_service.compress_image_to_target")
    async def test_upload_to_s3(self, mock_compress, mock_upload, service, sample_base64_image):
        """Debe subir imagen comprimida a S3."""
        mock_compress.return_value = sample_base64_image
        mock_upload.return_value = MagicMock(s3_url="https://s3.example.com/image.webp")

        result = await service._upload_to_s3(
            image_base64=sample_base64_image, owner_id="user-123", folder_id="folder-456", prefix_name="test"
        )

        assert result.s3_url == "https://s3.example.com/image.webp"
        mock_compress.assert_called_once()
        mock_upload.assert_called_once()

    # ========================================================================
    # Tests para _generate_single_variation
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.image_service.upload_file")
    @patch("app.services.image_service.compress_image_to_target")
    @patch("app.services.image_service.google_image")
    async def test_generate_single_variation_google(self, mock_google, mock_compress, mock_upload, service):
        """Debe generar variación usando Google por defecto."""
        mock_google.return_value = b"fake_image_bytes"
        mock_compress.return_value = "base64_compressed"
        mock_upload.return_value = MagicMock(s3_url="https://s3.example.com/variation.webp")

        result = await service._generate_single_variation(
            url_images=["https://example.com/original.jpg"],
            prompt="Generate variation",
            owner_id="user-123",
            folder_id="folder-456",
        )

        assert result == "https://s3.example.com/variation.webp"
        mock_google.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.image_service.upload_file")
    @patch("app.services.image_service.compress_image_to_target")
    @patch("app.services.image_service.openai_image_edit")
    async def test_generate_single_variation_openai(self, mock_openai, mock_compress, mock_upload, service):
        """Debe generar variación usando OpenAI cuando se especifica."""
        mock_openai.return_value = b"fake_image_bytes"
        mock_compress.return_value = "base64_compressed"
        mock_upload.return_value = MagicMock(s3_url="https://s3.example.com/variation.webp")

        result = await service._generate_single_variation(
            url_images=["https://example.com/original.jpg"],
            prompt="Generate variation",
            owner_id="user-123",
            folder_id="folder-456",
            provider="openai",
        )

        assert result == "https://s3.example.com/variation.webp"
        mock_openai.assert_called_once()

    # ========================================================================
    # Tests para generate_variation_images
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.image_service.upload_file")
    @patch("app.services.image_service.compress_image_to_target")
    @patch("app.services.image_service.analyze_image")
    @patch("app.services.image_service.google_image")
    async def test_generate_variation_images(
        self, mock_google, mock_analyze, mock_compress, mock_upload, service, sample_base64_image, mock_message_service
    ):
        """Debe generar múltiples variaciones de imagen."""
        from app.externals.google_vision.responses.vision_analysis_response import VisionAnalysisResponse

        # Use actual VisionAnalysisResponse dataclass
        mock_analyze.return_value = VisionAnalysisResponse(
            logo_description="TestLogo", label_description="Product, Electronics"
        )
        mock_google.return_value = b"fake_image_bytes"
        mock_compress.return_value = sample_base64_image
        mock_upload.return_value = MagicMock(s3_url="https://s3.example.com/image.webp")

        # Update mock to return proper agent_config
        mock_message_service.handle_message_with_config = AsyncMock(
            return_value={
                "message": {"text": "Generate a product image with blue background"},
                "agent_config": MagicMock(
                    provider_ai="google", model_ai="gemini", preferences=MagicMock(extra_parameters=None)
                ),
            }
        )

        request = VariationImageRequest(file=sample_base64_image, num_variations=2, language="es")

        result = await service.generate_variation_images(request, owner_id="user-123")

        assert result.original_url is not None
        assert len(result.generated_urls) == 2
        assert result.generated_prompt is not None

    # ========================================================================
    # Tests para generate_images_from
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.image_service.upload_file")
    @patch("app.services.image_service.compress_image_to_target")
    @patch("app.services.image_service.google_image")
    async def test_generate_images_from(self, mock_google, mock_compress, mock_upload, service, sample_base64_image):
        """Debe generar imágenes desde prompt y archivo."""
        mock_google.return_value = b"fake_image_bytes"
        mock_compress.return_value = sample_base64_image
        mock_upload.return_value = MagicMock(s3_url="https://s3.example.com/image.webp")

        request = GenerateImageRequest(
            file=sample_base64_image,
            file_url="https://example.com/original.jpg",
            prompt="Create a product image",
            num_variations=1,
        )

        result = await service.generate_images_from(request, owner_id="user-123")

        assert result.original_url is not None
        assert len(result.generated_urls) == 1
        assert result.generated_prompt == "Create a product image"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.image_service.upload_file")
    @patch("app.services.image_service.compress_image_to_target")
    @patch("app.services.image_service.google_image")
    async def test_generate_images_from_url(
        self, mock_google, mock_compress, mock_upload, service, sample_base64_image
    ):
        """Debe generar imágenes desde URL."""
        mock_google.return_value = b"fake_image_bytes"
        mock_compress.return_value = sample_base64_image
        mock_upload.return_value = MagicMock(s3_url="https://s3.example.com/image.webp")

        request = GenerateImageRequest(
            file_url="https://example.com/original.jpg", prompt="Create a product image", num_variations=1
        )

        result = await service.generate_images_from(request, owner_id="user-123")

        assert len(result.generated_urls) == 1

    # ========================================================================
    # Tests para generate_images_from_agent
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(ImageService, "generate_images_from")
    async def test_generate_images_from_agent(self, mock_generate, service, sample_base64_image):
        """Debe generar imágenes usando un agente para el prompt."""
        mock_generate.return_value = MagicMock(
            original_url="https://example.com/original.jpg",
            generated_urls=["https://example.com/generated.jpg"],
            generated_prompt="Agent generated prompt",
        )

        request = GenerateImageRequest(
            agent_id="image-prompt-agent", file_url="https://example.com/original.jpg", num_variations=1, language="es"
        )

        result = await service.generate_images_from_agent(request, owner_id="user-123")

        assert result is not None
        mock_generate.assert_called_once()
