"""
Tests de integración para los endpoints de la API.
Verifica el comportamiento end-to-end de los controladores.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.handle_controller import router
from app.services.audio_service_interface import AudioServiceInterface
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service_interface import MessageServiceInterface
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface
from app.services.video_service_interface import VideoServiceInterface


class TestAPIEndpoints:
    """Tests para los endpoints de la API."""

    @pytest.fixture
    def app(self):
        """Crear aplicación FastAPI de prueba."""
        test_app = FastAPI()
        test_app.include_router(router)
        return test_app

    @pytest.fixture
    def mock_message_service(self):
        """Mock para MessageService."""
        mock = MagicMock(spec=MessageServiceInterface)
        mock.handle_message = AsyncMock(return_value={"text": "Test response"})
        mock.handle_message_json = AsyncMock(return_value={"result": "success"})
        mock.recommend_products = AsyncMock(
            return_value=MagicMock(ai_response={"recommendation": "product"}, products=[{"name": "Product 1"}])
        )
        mock.generate_pdf = AsyncMock(return_value={"s3_url": "https://s3.example.com/doc.pdf"})
        mock.generate_copies = AsyncMock(return_value={"copies": {"headline": "Test"}})
        mock.resolve_funnel = AsyncMock(
            return_value={"pain_detection": "pain", "buyer_detection": "buyer", "sales_angles": []}
        )
        mock.resolve_brand_context = AsyncMock(return_value={"brands": ["Brand1"], "contexts": ["Context1"]})
        return mock

    @pytest.fixture
    def mock_image_service(self):
        """Mock para ImageService."""
        mock = MagicMock(spec=ImageServiceInterface)
        mock.generate_variation_images = AsyncMock(
            return_value=MagicMock(
                original_url="https://example.com/original.jpg",
                generated_urls=["https://example.com/var1.jpg"],
                generated_prompt="Test prompt",
            )
        )
        mock.generate_images_from = AsyncMock(
            return_value=MagicMock(
                original_url="https://example.com/original.jpg",
                generated_urls=["https://example.com/gen1.jpg"],
                generated_prompt="Test prompt",
            )
        )
        return mock

    @pytest.fixture
    def mock_video_service(self):
        """Mock para VideoService."""
        mock = MagicMock(spec=VideoServiceInterface)
        mock.generate_video = AsyncMock(return_value={"video_url": "https://example.com/video.mp4"})
        return mock

    @pytest.fixture
    def mock_audio_service(self):
        """Mock para AudioService."""
        mock = MagicMock(spec=AudioServiceInterface)
        mock.generate_audio = AsyncMock(return_value={"audio_url": "https://example.com/audio.mp3"})
        return mock

    @pytest.fixture
    def client(self, app, mock_message_service, mock_image_service, mock_video_service, mock_audio_service):
        """Crear cliente de prueba con dependencias mockeadas."""
        app.dependency_overrides[MessageServiceInterface] = lambda: mock_message_service
        app.dependency_overrides[ImageServiceInterface] = lambda: mock_image_service
        app.dependency_overrides[VideoServiceInterface] = lambda: mock_video_service
        app.dependency_overrides[AudioServiceInterface] = lambda: mock_audio_service
        return TestClient(app)

    # ========================================================================
    # Tests para /health
    # ========================================================================

    @pytest.mark.integration
    def test_health_check(self, client):
        """Debe retornar status OK."""
        response = client.get("/api/ms/conversational-engine/health")

        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

    # ========================================================================
    # Tests para /handle-message
    # ========================================================================

    @pytest.mark.integration
    def test_handle_message_success(self, client, mock_message_service):
        """Debe procesar mensaje correctamente."""
        response = client.post(
            "/api/ms/conversational-engine/handle-message",
            json={"agent_id": "test-agent", "conversation_id": "conv-123", "query": "Hello"},
        )

        assert response.status_code == 200
        assert response.json() == {"text": "Test response"}
        mock_message_service.handle_message.assert_called_once()

    @pytest.mark.integration
    def test_handle_message_with_metadata(self, client, mock_message_service):
        """Debe pasar metadata_filter correctamente."""
        response = client.post(
            "/api/ms/conversational-engine/handle-message",
            json={
                "agent_id": "test-agent",
                "conversation_id": "conv-123",
                "query": "Hello",
                "metadata_filter": [{"key": "category", "value": "tech", "evaluator": "="}],
                "parameter_prompt": {"language": "es"},
            },
        )

        assert response.status_code == 200

    @pytest.mark.integration
    def test_handle_message_validation_error(self, client):
        """Debe retornar 422 para datos inválidos."""
        response = client.post(
            "/api/ms/conversational-engine/handle-message",
            json={
                "agent_id": "test-agent"
                # Falta conversation_id y query
            },
        )

        assert response.status_code == 422

    # ========================================================================
    # Tests para /handle-message-json
    # ========================================================================

    @pytest.mark.integration
    def test_handle_message_json_success(self, client, mock_message_service):
        """Debe retornar respuesta JSON parseada."""
        response = client.post(
            "/api/ms/conversational-engine/handle-message-json",
            json={"agent_id": "test-agent", "conversation_id": "", "query": "Get data"},
        )

        assert response.status_code == 200
        assert response.json() == {"result": "success"}

    # ========================================================================
    # Tests para /recommend-product
    # ========================================================================

    @pytest.mark.integration
    def test_recommend_product_success(self, client, mock_message_service):
        """Debe recomendar productos."""
        response = client.post(
            "/api/ms/conversational-engine/recommend-product",
            json={"product_name": "Headphones", "product_description": "Wireless headphones", "similar": False},
        )

        assert response.status_code == 200

    # ========================================================================
    # Tests para /generate-pdf
    # ========================================================================

    @pytest.mark.integration
    def test_generate_pdf_success(self, client, mock_message_service):
        """Debe generar PDF."""
        response = client.post(
            "/api/ms/conversational-engine/generate-pdf",
            json={
                "product_name": "Test Product",
                "product_description": "Description",
                "product_id": "prod-123",
                "owner_id": "owner-123",
                "title": "Manual",
                "image_url": "https://example.com/img.jpg",
                "language": "es",
                "content": "Product content",
            },
        )

        assert response.status_code == 200

    # ========================================================================
    # Tests para /generate-copies
    # ========================================================================

    @pytest.mark.integration
    def test_generate_copies_success(self, client, mock_message_service):
        """Debe generar copies."""
        response = client.post(
            "/api/ms/conversational-engine/generate-copies", json={"prompt": "Product description for copies"}
        )

        assert response.status_code == 200
        assert "copies" in response.json()

    # ========================================================================
    # Tests para /resolve-info-funnel
    # ========================================================================

    @pytest.mark.integration
    def test_resolve_funnel_success(self, client, mock_message_service):
        """Debe resolver información del funnel."""
        response = client.post(
            "/api/ms/conversational-engine/resolve-info-funnel",
            json={"product_name": "Test Product", "product_description": "Description", "language": "es"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "pain_detection" in data
        assert "buyer_detection" in data
        assert "sales_angles" in data

    # ========================================================================
    # Tests para Dropi endpoints
    # ========================================================================

    @pytest.mark.integration
    @patch("app.services.dropi_service.dropi_client")
    def test_get_departments(self, mock_dropi_client, client):
        """Debe obtener departamentos de Dropi."""
        mock_dropi_client.get_departments = AsyncMock(return_value={"objects": [{"id": 1, "name": "Dept 1"}]})

        response = client.get("/api/ms/conversational-engine/integration/dropi/departments")

        assert response.status_code == 200

    @pytest.mark.integration
    @patch("app.services.dropi_service.dropi_client")
    def test_get_cities_by_department(self, mock_dropi_client, client):
        """Debe obtener ciudades por departamento."""
        mock_dropi_client.get_cities_by_department = AsyncMock(
            return_value={"objects": {"cities": [{"id": 1, "name": "City 1"}]}}
        )

        response = client.get("/api/ms/conversational-engine/integration/dropi/departments/1/cities")

        assert response.status_code == 200


class TestAuthenticatedEndpoints:
    """Tests para endpoints que requieren autenticación."""

    @pytest.mark.integration
    def test_scrape_product_requires_auth_header(self):
        """Endpoint scrape-product requiere header de autenticación."""
        # Este test verifica que el endpoint existe y requiere auth
        # La implementación real del middleware maneja la autenticación
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(router)

        mock_scraping = MagicMock(spec=ProductScrapingServiceInterface)
        mock_scraping.scrape_product = AsyncMock(return_value={"data": {}})
        test_app.dependency_overrides[ProductScrapingServiceInterface] = lambda: mock_scraping

        client = TestClient(test_app, raise_server_exceptions=False)

        # Sin header de auth
        response = client.post(
            "/api/ms/conversational-engine/scrape-product", json={"product_url": "https://amazon.com/dp/B08TEST"}
        )

        # Debería fallar por falta de autenticación (401 o 500 dependiendo de la config)
        assert response.status_code in [401, 500, 422]

    @pytest.mark.integration
    def test_generate_images_api_key_requires_header(self):
        """Endpoint con api-key requiere x-api-key header."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(router)

        mock_image = MagicMock(spec=ImageServiceInterface)
        mock_image.generate_images_from = AsyncMock(return_value=MagicMock())
        test_app.dependency_overrides[ImageServiceInterface] = lambda: mock_image

        client = TestClient(test_app, raise_server_exceptions=False)

        response = client.post(
            "/api/ms/conversational-engine/generate-images-from/api-key",
            json={"prompt": "Generate image", "file_url": "https://example.com/img.jpg"},
        )

        # Debería fallar por falta de API key
        assert response.status_code in [401, 500]
