"""
Tests para google_vision_client.
Verifica la integración con Google Cloud Vision API.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.externals.google_vision.google_vision_client import analyze_image
from app.externals.google_vision.responses.vision_analysis_response import VisionAnalysisResponse


class TestGoogleVisionClient:
    """Tests para google_vision_client."""

    @pytest.fixture
    def sample_vision_response(self):
        """Respuesta de ejemplo de Google Vision API."""
        return {
            "responses": [
                {
                    "labelAnnotations": [
                        {"description": "Product", "score": 0.95},
                        {"description": "Electronics", "score": 0.85},
                        {"description": "Technology", "score": 0.75},
                    ],
                    "logoAnnotations": [{"description": "Apple", "score": 0.90}],
                }
            ]
        }

    @pytest.fixture
    def sample_vision_response_no_logo(self):
        """Respuesta sin logo detectado."""
        return {"responses": [{"labelAnnotations": [{"description": "Product", "score": 0.95}], "logoAnnotations": []}]}

    @pytest.fixture
    def sample_vision_response_low_score(self):
        """Respuesta con scores bajos."""
        return {
            "responses": [
                {
                    "labelAnnotations": [{"description": "Unknown", "score": 0.3}],
                    "logoAnnotations": [{"description": "Maybe Logo", "score": 0.5}],
                }
            ]
        }

    # ========================================================================
    # Tests para analyze_image
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.google_vision.google_vision_client.aiohttp.ClientSession")
    async def test_analyze_image_success(self, mock_session_class, sample_vision_response, sample_base64_image):
        """Debe analizar imagen correctamente."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_vision_response)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        result = await analyze_image(sample_base64_image)

        assert isinstance(result, VisionAnalysisResponse)
        assert result.logo_description == "Apple"
        assert "Product" in result.label_description
        assert "Electronics" in result.label_description

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.google_vision.google_vision_client.aiohttp.ClientSession")
    async def test_analyze_image_no_logo(self, mock_session_class, sample_vision_response_no_logo, sample_base64_image):
        """Debe manejar imágenes sin logo detectado."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_vision_response_no_logo)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        result = await analyze_image(sample_base64_image)

        assert result.logo_description == ""
        assert "Product" in result.label_description

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.google_vision.google_vision_client.aiohttp.ClientSession")
    async def test_analyze_image_filters_low_scores(
        self, mock_session_class, sample_vision_response_low_score, sample_base64_image
    ):
        """Debe filtrar resultados con score bajo."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_vision_response_low_score)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        result = await analyze_image(sample_base64_image)

        assert result.logo_description == ""  # Score < 0.65
        assert result.label_description == ""  # Score < 0.65

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_image_api_error(self, sample_base64_image):
        """Debe lanzar excepción en error de API."""
        with patch("app.externals.google_vision.google_vision_client.aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value="Bad Request")

            # Create proper async context manager mocks
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_post_cm)

            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_cm

            with pytest.raises(Exception) as exc_info:
                await analyze_image(sample_base64_image)

            assert "Error en Google Vision API" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.externals.google_vision.google_vision_client.aiohttp.ClientSession")
    async def test_analyze_image_empty_response(self, mock_session_class, sample_base64_image):
        """Debe manejar respuesta vacía."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"responses": [{}]})

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        result = await analyze_image(sample_base64_image)

        assert result.logo_description == ""
        assert result.label_description == ""


class TestVisionAnalysisResponse:
    """Tests para VisionAnalysisResponse."""

    @pytest.mark.unit
    def test_response_creation(self):
        """Debe crear respuesta correctamente."""
        response = VisionAnalysisResponse(logo_description="TestLogo", label_description="Product, Electronics")

        assert response.logo_description == "TestLogo"
        assert response.label_description == "Product, Electronics"

    @pytest.mark.unit
    def test_get_analysis_text(self):
        """Debe generar texto de análisis."""
        response = VisionAnalysisResponse(logo_description="Apple", label_description="Phone, Technology")

        analysis_text = response.get_analysis_text()

        # Verificar que el método existe y retorna string
        assert isinstance(analysis_text, str)
