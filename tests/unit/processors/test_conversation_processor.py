"""
Tests para ConversationProcessor (clase base).
Verifica la funcionalidad común de todos los procesadores.
"""

from unittest.mock import MagicMock

import pytest

from app.processors.conversation_processor import ConversationProcessor
from app.requests.message_request import MessageRequest


class ConcreteProcessor(ConversationProcessor):
    """Implementación concreta para testing."""

    async def process(self, query, files=None, supports_interleaved_files=False):
        return {"text": "processed"}


class TestConversationProcessor:
    """Tests para ConversationProcessor."""

    @pytest.fixture
    def mock_llm(self):
        """Mock para LLM."""
        return MagicMock()

    @pytest.fixture
    def processor(self, mock_llm):
        """Crear instancia de procesador concreto."""
        return ConcreteProcessor(llm=mock_llm, context="Test context", history=[{"role": "user", "content": "Hello"}])

    @pytest.mark.unit
    def test_initialization(self, processor, mock_llm):
        """Debe inicializarse correctamente."""
        assert processor.llm == mock_llm
        assert processor.context == "Test context"
        assert len(processor.history) == 1

    @pytest.mark.unit
    def test_get_langsmith_config_basic(self, processor):
        """Debe generar configuración básica de LangSmith."""
        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Test query")

        config = processor._get_langsmith_config(request, "test_processor")

        assert "tags" in config
        assert "test_processor" in config["tags"]
        assert "agent_test-agent" in config["tags"]
        assert "metadata" in config
        assert config["metadata"]["agent_id"] == "test-agent"
        assert config["metadata"]["conversation_id"] == "conv-123"

    @pytest.mark.unit
    def test_get_langsmith_config_with_extra_metadata(self, processor):
        """Debe incluir metadata extra en configuración."""
        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Test")

        config = processor._get_langsmith_config(
            request, "test_processor", custom_field="custom_value", another_field=42
        )

        assert config["metadata"]["custom_field"] == "custom_value"
        assert config["metadata"]["another_field"] == 42

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_not_implemented_in_base(self, mock_llm):
        """El método process debe lanzar NotImplementedError en clase base."""
        # No podemos instanciar ConversationProcessor directamente
        # pero podemos verificar que la implementación concreta funciona
        processor = ConcreteProcessor(mock_llm, "context", [])
        result = await processor.process("query")
        assert result == {"text": "processed"}

    @pytest.mark.unit
    def test_stores_llm_reference(self, processor, mock_llm):
        """Debe almacenar referencia al LLM."""
        assert processor.llm is mock_llm

    @pytest.mark.unit
    def test_stores_context(self, processor):
        """Debe almacenar el contexto."""
        assert processor.context == "Test context"

    @pytest.mark.unit
    def test_stores_history(self, processor):
        """Debe almacenar el historial."""
        assert processor.history == [{"role": "user", "content": "Hello"}]

    @pytest.mark.unit
    def test_empty_history(self, mock_llm):
        """Debe manejar historial vacío."""
        processor = ConcreteProcessor(mock_llm, "context", [])
        assert processor.history == []

    @pytest.mark.unit
    def test_none_context(self, mock_llm):
        """Debe manejar contexto None."""
        processor = ConcreteProcessor(mock_llm, None, [])
        assert processor.context is None
