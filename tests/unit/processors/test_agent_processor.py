"""
Tests para AgentProcessor.
Verifica el procesamiento de conversaciones con herramientas.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.processors.agent_processor import AgentProcessor
from app.processors.conversation_processor import ConversationProcessor
from app.requests.message_request import MessageRequest


class TestAgentProcessor:
    """Tests para AgentProcessor."""

    @pytest.fixture
    def mock_llm(self):
        """Mock para el modelo de lenguaje."""
        mock = MagicMock()
        mock.bind_tools = MagicMock(return_value=mock)
        return mock

    @pytest.fixture
    def mock_tools(self):
        """Mock para herramientas."""
        tool1 = MagicMock()
        tool1.name = "search_tool"
        tool1.description = "Search for information"

        tool2 = MagicMock()
        tool2.name = "calculate_tool"
        tool2.description = "Perform calculations"

        return [tool1, tool2]

    @pytest.fixture
    def processor(self, mock_llm, mock_tools):
        """Crear instancia de AgentProcessor."""
        return AgentProcessor(
            llm=mock_llm, context="You are a helpful assistant with tools.", history=[], tools=mock_tools
        )

    @pytest.mark.unit
    def test_inherits_from_conversation_processor(self, processor):
        """Debe heredar de ConversationProcessor."""
        assert isinstance(processor, ConversationProcessor)

    @pytest.mark.unit
    def test_initialization(self, processor, mock_llm, mock_tools):
        """Debe inicializarse correctamente con herramientas."""
        assert processor.llm == mock_llm
        assert processor.context == "You are a helpful assistant with tools."
        assert processor.history == []
        assert processor.tools == mock_tools
        assert len(processor.tools) == 2

    # ========================================================================
    # Tests para process
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.processors.agent_processor.create_tool_calling_agent")
    @patch("app.processors.agent_processor.AgentExecutor")
    async def test_process_creates_agent_executor(self, mock_executor_class, mock_create_agent, processor):
        """Debe crear AgentExecutor correctamente."""
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "Agent response", "intermediate_steps": []})
        mock_executor_class.return_value = mock_executor

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Search for something")

        result = await processor.process(request)

        mock_create_agent.assert_called_once()
        mock_executor_class.assert_called_once()
        assert result["text"] == "Agent response"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.processors.agent_processor.create_tool_calling_agent")
    @patch("app.processors.agent_processor.AgentExecutor")
    async def test_process_with_tools(self, mock_executor_class, mock_create_agent, processor, mock_tools):
        """Debe pasar herramientas al AgentExecutor."""
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "Response"})
        mock_executor_class.return_value = mock_executor

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Use a tool")

        await processor.process(request)

        executor_call_kwargs = mock_executor_class.call_args[1]
        assert executor_call_kwargs["tools"] == mock_tools

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.processors.agent_processor.create_tool_calling_agent")
    @patch("app.processors.agent_processor.AgentExecutor")
    async def test_process_handles_output_key(self, mock_executor_class, mock_create_agent, processor):
        """Debe mapear 'output' a 'text' en la respuesta."""
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "The output message", "intermediate_steps": []})
        mock_executor_class.return_value = mock_executor

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Query")

        result = await processor.process(request)

        assert "text" in result
        assert result["text"] == "The output message"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.processors.agent_processor.create_tool_calling_agent")
    @patch("app.processors.agent_processor.AgentExecutor")
    async def test_process_executor_config(self, mock_executor_class, mock_create_agent, processor):
        """Debe configurar AgentExecutor con opciones correctas."""
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "Response"})
        mock_executor_class.return_value = mock_executor

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Query")

        await processor.process(request)

        executor_call_kwargs = mock_executor_class.call_args[1]
        assert executor_call_kwargs["verbose"] is False
        assert executor_call_kwargs["handle_parsing_errors"] is True
        assert executor_call_kwargs["max_iterations"] == 3
        assert executor_call_kwargs["return_intermediate_steps"] is True

    # ========================================================================
    # Tests para manejo de errores
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.processors.agent_processor.create_tool_calling_agent")
    @patch("app.processors.agent_processor.AgentExecutor")
    async def test_process_handles_execution_error(self, mock_executor_class, mock_create_agent, processor):
        """Debe manejar errores de ejecución del agente."""
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(side_effect=Exception("Agent execution failed"))
        mock_executor_class.return_value = mock_executor

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Query")

        result = await processor.process(request)

        assert "message" in result
        assert "reformular" in result["message"].lower() or "procesar" in result["message"].lower()

    # ========================================================================
    # Tests para _get_langsmith_config
    # ========================================================================

    @pytest.mark.unit
    def test_get_langsmith_config_includes_tools(self, processor):
        """Debe incluir información de herramientas en metadata."""
        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Test")

        config = processor._get_langsmith_config(request, "agent_processor", has_tools=True)

        assert "agent_processor" in config["tags"]
        assert config["metadata"]["has_tools"] is True
