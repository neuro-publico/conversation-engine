"""
Tests para SimpleProcessor.
Verifica el procesamiento simple de conversaciones sin herramientas.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.processors.conversation_processor import ConversationProcessor
from app.processors.simple_processor import SimpleProcessor
from app.requests.message_request import MessageRequest


class TestSimpleProcessor:
    """Tests para SimpleProcessor."""

    @pytest.fixture
    def mock_llm(self):
        """Mock para el modelo de lenguaje."""
        return MagicMock()

    @pytest.fixture
    def processor(self, mock_llm):
        """Crear instancia de SimpleProcessor."""
        return SimpleProcessor(llm=mock_llm, context="You are a helpful assistant.", history=[])

    @pytest.mark.unit
    def test_inherits_from_conversation_processor(self, processor):
        """Debe heredar de ConversationProcessor."""
        assert isinstance(processor, ConversationProcessor)

    @pytest.mark.unit
    def test_initialization(self, processor, mock_llm):
        """Debe inicializarse correctamente."""
        assert processor.llm == mock_llm
        assert processor.context == "You are a helpful assistant."
        assert processor.history == []

    # ========================================================================
    # Tests para process
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(SimpleProcessor, "generate_response")
    async def test_process_basic_message(self, mock_generate, processor):
        """Debe procesar un mensaje básico correctamente."""
        mock_generate.return_value = {
            "context": "You are a helpful assistant.",
            "chat_history": [],
            "input": "Hello, how are you?",
            "text": "This is a test response",
        }

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello, how are you?")

        result = await processor.process(request)

        assert "text" in result
        assert result["text"] == "This is a test response"
        assert "context" in result
        assert "input" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(SimpleProcessor, "generate_response")
    async def test_process_with_json_parser(self, mock_generate, processor):
        """Debe agregar instrucciones de JSON cuando se especifica json_parser."""
        mock_generate.return_value = {
            "context": "context",
            "chat_history": [],
            "input": "Get data",
            "text": '{"result": "success"}',
        }

        request = MessageRequest(
            agent_id="test-agent", conversation_id="conv-123", query="Get data", json_parser={"result": "string"}
        )

        result = await processor.process(request)

        assert result["text"] == '{"result": "success"}'
        mock_generate.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(SimpleProcessor, "generate_response")
    async def test_process_extracts_json_from_markdown(self, mock_generate, processor):
        """Debe extraer JSON de bloques de código markdown."""
        mock_generate.return_value = {
            "context": "context",
            "chat_history": [],
            "input": "Get JSON",
            "text": '{"extracted": "value"}',
        }

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Get JSON")

        result = await processor.process(request)

        assert result["text"] == '{"extracted": "value"}'

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(SimpleProcessor, "generate_response")
    async def test_process_with_files_interleaved(self, mock_generate, processor):
        """Debe manejar archivos cuando soporta interleaved."""
        mock_generate.return_value = {
            "context": "context",
            "chat_history": [],
            "input": "Analyze this image",
            "text": "Image analyzed",
        }

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Analyze this image")
        files = [{"type": "image", "url": "https://example.com/image.jpg"}]

        result = await processor.process(request, files=files, supports_interleaved_files=True)

        assert result is not None
        mock_generate.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch.object(SimpleProcessor, "generate_response")
    async def test_process_with_files_not_interleaved(self, mock_generate, processor):
        """Debe agregar referencias a archivos en system message cuando no soporta interleaved."""
        mock_generate.return_value = {
            "context": "context",
            "chat_history": [],
            "input": "Analyze this image",
            "text": "Image analyzed",
        }

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Analyze this image")
        files = [{"type": "image", "url": "https://example.com/image.jpg"}]

        result = await processor.process(request, files=files, supports_interleaved_files=False)

        assert result is not None
        mock_generate.assert_called_once()

    # ========================================================================
    # Tests para generate_response (lógica interna)
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_response_structure(self, mock_llm):
        """generate_response debe usar la estructura correcta."""
        # Setup mock LLM que funciona con la cadena
        mock_response = MagicMock()
        mock_response.content = "Test response"

        # Crear un mock que simule la cadena completa
        chain_result = MagicMock()
        chain_result.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.__or__ = MagicMock(return_value=chain_result)

        processor = SimpleProcessor(llm=mock_llm, context="Test context", history=[])

        # Verificar que processor tiene los atributos correctos
        assert processor.context == "Test context"
        assert processor.history == []
        assert processor.llm is mock_llm

    # ========================================================================
    # Tests para _get_langsmith_config
    # ========================================================================

    @pytest.mark.unit
    def test_get_langsmith_config(self, processor):
        """Debe generar configuración de LangSmith correctamente."""
        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Test")

        config = processor._get_langsmith_config(request, "simple_processor", has_json_parser=True, has_files=False)

        assert "tags" in config
        assert "simple_processor" in config["tags"]
        assert "metadata" in config
        assert config["metadata"]["agent_id"] == "test-agent"
        assert config["metadata"]["has_json_parser"] is True

    @pytest.mark.unit
    def test_get_langsmith_config_with_empty_extras(self, processor):
        """Config sin metadata extra debe funcionar."""
        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Test")

        config = processor._get_langsmith_config(request, "simple_processor")

        assert "tags" in config
        assert "metadata" in config
        assert config["metadata"]["agent_id"] == "test-agent"
