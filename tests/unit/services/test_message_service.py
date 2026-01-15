"""
Tests para MessageService.
Verifica el procesamiento de mensajes y funcionalidades relacionadas.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.requests.brand_context_resolver_request import BrandContextResolverRequest
from app.requests.copy_request import CopyRequest
from app.requests.message_request import MessageRequest
from app.requests.recommend_product_request import RecommendProductRequest
from app.requests.resolve_funnel_request import ResolveFunnelRequest
from app.services.message_service import MessageService
from app.services.message_service_interface import MessageServiceInterface


class TestMessageService:
    """Tests para MessageService."""

    @pytest.fixture
    def mock_conversation_manager(self):
        """Mock para ConversationManager."""
        mock = MagicMock()
        mock.process_conversation = AsyncMock(return_value={"text": "Test response"})
        return mock

    @pytest.fixture
    def service(self, mock_conversation_manager):
        """Crear instancia de MessageService con mocks."""
        return MessageService(conversation_manager=mock_conversation_manager)

    @pytest.mark.unit
    def test_implements_interface(self, service):
        """Debe implementar MessageServiceInterface."""
        assert isinstance(service, MessageServiceInterface)

    # ========================================================================
    # Tests para handle_message
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_handle_message_success(self, mock_get_agent, service, mock_agent_config):
        """Debe procesar un mensaje correctamente."""
        mock_get_agent.return_value = mock_agent_config

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello")

        result = await service.handle_message(request)

        assert result == {"text": "Test response"}
        mock_get_agent.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_handle_message_with_metadata_filter(self, mock_get_agent, service, mock_agent_config):
        """Debe pasar metadata_filter correctamente."""
        mock_get_agent.return_value = mock_agent_config

        request = MessageRequest(
            agent_id="test-agent",
            conversation_id="conv-123",
            query="Hello",
            metadata_filter=[{"key": "category", "value": "tech", "evaluator": "="}],
        )

        await service.handle_message(request)

        call_args = mock_get_agent.call_args
        assert call_args is not None

    # ========================================================================
    # Tests para handle_message_with_config
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_handle_message_with_config_returns_both(self, mock_get_agent, service, mock_agent_config):
        """Debe retornar tanto el mensaje como la configuración del agente."""
        mock_get_agent.return_value = mock_agent_config

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello")

        result = await service.handle_message_with_config(request)

        assert "message" in result
        assert "agent_config" in result
        assert result["message"] == {"text": "Test response"}

    # ========================================================================
    # Tests para handle_message_json
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_handle_message_json_parses_response(
        self, mock_get_agent, service, mock_agent_config, mock_conversation_manager
    ):
        """Debe parsear la respuesta JSON."""
        mock_get_agent.return_value = mock_agent_config
        mock_conversation_manager.process_conversation = AsyncMock(return_value={"text": '{"result": "success"}'})

        request = MessageRequest(agent_id="test-agent", conversation_id="", query="Get JSON")

        result = await service.handle_message_json(request)

        assert result == {"result": "success"}

    # ========================================================================
    # Tests para recommend_products
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.search_products")
    @patch("app.services.message_service.get_agent")
    async def test_recommend_products(
        self, mock_get_agent, mock_search, service, mock_agent_config, mock_conversation_manager
    ):
        """Debe recomendar productos basándose en IA y búsqueda."""
        mock_get_agent.return_value = mock_agent_config
        mock_conversation_manager.process_conversation = AsyncMock(
            return_value={"text": '{"recommended_product": "wireless headphones"}'}
        )

        mock_amazon_response = MagicMock()
        mock_amazon_response.get_products.return_value = [{"name": "Product 1"}]
        mock_search.return_value = mock_amazon_response

        request = RecommendProductRequest(
            product_name="Headphones", product_description="Bluetooth headphones", similar=False
        )

        result = await service.recommend_products(request)

        assert result.ai_response == {"recommended_product": "wireless headphones"}
        assert len(result.products) == 1

    # ========================================================================
    # Tests para process_multiple_agents
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_process_multiple_agents_combines_responses(
        self, mock_get_agent, service, mock_agent_config, mock_conversation_manager
    ):
        """Debe combinar respuestas de múltiples agentes."""
        mock_get_agent.return_value = mock_agent_config

        # Simular diferentes respuestas para cada llamada
        mock_conversation_manager.process_conversation = AsyncMock(
            side_effect=[{"text": '{"field1": "value1"}'}, {"text": '{"field2": "value2"}'}]
        )

        agent_queries = [{"agent": "agent1", "query": "query1"}, {"agent": "agent2", "query": "query2"}]

        result = await service.process_multiple_agents(agent_queries)

        assert "field1" in result or "field2" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_process_multiple_agents_handles_errors(
        self, mock_get_agent, service, mock_agent_config, mock_conversation_manager
    ):
        """Debe manejar errores en agentes individuales."""
        mock_get_agent.return_value = mock_agent_config
        mock_conversation_manager.process_conversation = AsyncMock(side_effect=Exception("Agent error"))

        agent_queries = [{"agent": "agent1", "query": "query1"}]

        with pytest.raises(ValueError):
            await service.process_multiple_agents(agent_queries)

    # ========================================================================
    # Tests para generate_copies
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(MessageService, "process_multiple_agents")
    async def test_generate_copies(self, mock_process, service):
        """Debe generar copies usando múltiples agentes."""
        mock_process.return_value = {"headline": "Test Headline", "body": "Test Body"}

        request = CopyRequest(prompt="Product description")

        result = await service.generate_copies(request)

        assert "copies" in result
        assert result["copies"]["headline"] == "Test Headline"

    # ========================================================================
    # Tests para resolve_funnel
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_resolve_funnel(self, mock_get_agent, service, mock_agent_config, mock_conversation_manager):
        """Debe resolver información del funnel."""
        mock_get_agent.return_value = mock_agent_config

        responses = [
            {"text": "Pain detection result"},
            {"text": "Buyer detection result"},
            {"angles": [{"name": "Angle 1", "description": "Desc"}]},
        ]
        mock_conversation_manager.process_conversation = AsyncMock(
            side_effect=[
                {"text": "Pain detection result"},
                {"text": "Buyer detection result"},
                {"text": '{"angles": [{"name": "Angle 1", "description": "Desc"}]}'},
            ]
        )

        request = ResolveFunnelRequest(
            product_name="Test Product", product_description="Test Description", language="es"
        )

        result = await service.resolve_funnel(request)

        assert "pain_detection" in result
        assert "buyer_detection" in result
        assert "sales_angles" in result

    # ========================================================================
    # Tests para resolve_brand_context
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.services.message_service.get_agent")
    async def test_resolve_brand_context(self, mock_get_agent, service, mock_agent_config, mock_conversation_manager):
        """Debe resolver contexto de marca."""
        mock_get_agent.return_value = mock_agent_config
        mock_conversation_manager.process_conversation = AsyncMock(
            side_effect=[
                {"text": '{"brands": ["Brand1", "Brand2"]}'},
                {"text": '{"contexts": ["Context1", "Context2"]}'},
            ]
        )

        request = BrandContextResolverRequest(websites_info=["https://store.example.com"])

        result = await service.resolve_brand_context(request)

        assert "brands" in result
        assert "contexts" in result
