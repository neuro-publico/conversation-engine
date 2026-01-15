"""
Tests para ConversationManager.
Verifica la gestión del historial de conversaciones y procesamiento.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse, AgentPreferences
from app.managers.conversation_manager import ConversationManager
from app.managers.conversation_manager_interface import ConversationManagerInterface
from app.requests.message_request import MessageRequest


class TestConversationManager:
    """Tests para ConversationManager."""

    @pytest.fixture
    def manager(self):
        """Crear instancia de ConversationManager."""
        return ConversationManager()

    @pytest.fixture
    def agent_config(self):
        """Crear AgentConfigResponse de prueba."""
        return AgentConfigResponse(
            id=1,
            agent_id="test-agent",
            description="Test agent",
            prompt="You are a helpful assistant.",
            provider_ai="openai",
            model_ai="gpt-4",
            preferences=AgentPreferences(temperature=0.7, max_tokens=1000, top_p=1.0),
            tools=[],
            mcp_config=None,
        )

    @pytest.fixture
    def agent_config_with_tools(self, agent_config):
        """AgentConfigResponse con herramientas."""
        agent_config.tools = [
            {
                "tool_name": "search",
                "description": "Search tool",
                "config": {
                    "name": "search",
                    "description": "Search",
                    "api": "https://api.example.com",
                    "method": "GET",
                    "properties": [{"name": "query", "description": "Search query"}],
                    "body": None,
                    "headers": None,
                    "query_params": None,
                },
            }
        ]
        return agent_config

    @pytest.fixture
    def agent_config_with_mcp(self, agent_config):
        """AgentConfigResponse con MCP."""
        agent_config.mcp_config = {"servers": [{"name": "test-server", "url": "http://localhost:8080"}]}
        return agent_config

    @pytest.mark.unit
    def test_implements_interface(self, manager):
        """Debe implementar ConversationManagerInterface."""
        assert isinstance(manager, ConversationManagerInterface)

    @pytest.mark.unit
    def test_initialization(self, manager):
        """Debe inicializarse con historial vacío."""
        assert manager.history_store == {}
        assert manager.max_history_length == 10

    # ========================================================================
    # Tests para get_conversation_history
    # ========================================================================

    @pytest.mark.unit
    def test_get_conversation_history_empty(self, manager):
        """Debe retornar lista vacía para conversación inexistente."""
        history = manager.get_conversation_history("new-conv")
        assert history == []

    @pytest.mark.unit
    def test_get_conversation_history_with_data(self, manager):
        """Debe retornar historial existente."""
        manager.history_store["conv-123"] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        history = manager.get_conversation_history("conv-123")

        assert len(history) == 2
        assert history[0]["content"] == "Hello"

    @pytest.mark.unit
    def test_get_conversation_history_empty_id(self, manager):
        """Debe retornar lista vacía para ID vacío."""
        history = manager.get_conversation_history("")
        assert history == []

    # ========================================================================
    # Tests para _update_conversation_history
    # ========================================================================

    @pytest.mark.unit
    def test_update_conversation_history(self, manager):
        """Debe actualizar historial correctamente."""
        manager._update_conversation_history(
            conversation_id="conv-123", user_message_content="Hello", ai_response_content="Hi there!"
        )

        history = manager.history_store["conv-123"]
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}

    @pytest.mark.unit
    def test_update_conversation_history_appends(self, manager):
        """Debe agregar mensajes al historial existente."""
        manager.history_store["conv-123"] = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response"},
        ]

        manager._update_conversation_history(
            conversation_id="conv-123", user_message_content="Second", ai_response_content="Another response"
        )

        assert len(manager.history_store["conv-123"]) == 4

    @pytest.mark.unit
    def test_update_conversation_history_truncates(self, manager):
        """Debe truncar historial cuando excede max_history_length."""
        manager.max_history_length = 4

        # Agregar más mensajes que el límite
        for i in range(5):
            manager._update_conversation_history(
                conversation_id="conv-123", user_message_content=f"Message {i}", ai_response_content=f"Response {i}"
            )

        history = manager.history_store["conv-123"]
        assert len(history) == 4  # Truncado al máximo

    @pytest.mark.unit
    def test_update_conversation_history_empty_id_does_nothing(self, manager):
        """No debe actualizar si conversation_id está vacío."""
        manager._update_conversation_history(conversation_id="", user_message_content="Hello", ai_response_content="Hi")

        assert "" not in manager.history_store

    # ========================================================================
    # Tests para process_conversation
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.managers.conversation_manager.AIProviderFactory")
    @patch("app.managers.conversation_manager.SimpleProcessor")
    async def test_process_conversation_simple(self, mock_simple_processor, mock_factory, manager, agent_config):
        """Debe usar SimpleProcessor cuando no hay herramientas ni MCP."""
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = MagicMock()
        mock_provider.supports_interleaved_files.return_value = True
        mock_factory.get_provider.return_value = mock_provider

        mock_processor_instance = MagicMock()
        mock_processor_instance.process = AsyncMock(return_value={"text": "Simple response"})
        mock_simple_processor.return_value = mock_processor_instance

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello")

        result = await manager.process_conversation(request, agent_config)

        assert result["text"] == "Simple response"
        mock_simple_processor.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.managers.conversation_manager.AIProviderFactory")
    @patch("app.managers.conversation_manager.ToolGenerator")
    @patch("app.managers.conversation_manager.AgentProcessor")
    async def test_process_conversation_with_tools(
        self, mock_agent_processor, mock_tool_gen, mock_factory, manager, agent_config_with_tools
    ):
        """Debe usar AgentProcessor cuando hay herramientas."""
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = MagicMock()
        mock_provider.supports_interleaved_files.return_value = True
        mock_factory.get_provider.return_value = mock_provider

        mock_tool_gen.generate_tools.return_value = [MagicMock()]

        mock_processor_instance = MagicMock()
        mock_processor_instance.process = AsyncMock(return_value={"text": "Agent response"})
        mock_agent_processor.return_value = mock_processor_instance

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Use tool")

        result = await manager.process_conversation(request, agent_config_with_tools)

        assert result["text"] == "Agent response"
        mock_agent_processor.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.managers.conversation_manager.AIProviderFactory")
    @patch("app.managers.conversation_manager.MCPProcessor")
    async def test_process_conversation_with_mcp(
        self, mock_mcp_processor, mock_factory, manager, agent_config_with_mcp
    ):
        """Debe usar MCPProcessor cuando hay configuración MCP."""
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = MagicMock()
        mock_provider.supports_interleaved_files.return_value = True
        mock_factory.get_provider.return_value = mock_provider

        mock_processor_instance = MagicMock()
        mock_processor_instance.process = AsyncMock(return_value={"text": "MCP response"})
        mock_mcp_processor.return_value = mock_processor_instance

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="MCP query")

        result = await manager.process_conversation(request, agent_config_with_mcp)

        assert result["text"] == "MCP response"
        mock_mcp_processor.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.managers.conversation_manager.AIProviderFactory")
    @patch("app.managers.conversation_manager.SimpleProcessor")
    async def test_process_conversation_updates_history(self, mock_processor, mock_factory, manager, agent_config):
        """Debe actualizar historial después de procesar."""
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = MagicMock()
        mock_provider.supports_interleaved_files.return_value = True
        mock_factory.get_provider.return_value = mock_provider

        mock_processor_instance = MagicMock()
        mock_processor_instance.process = AsyncMock(return_value={"text": "Response"})
        mock_processor.return_value = mock_processor_instance

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello")

        await manager.process_conversation(request, agent_config)

        history = manager.history_store["conv-123"]
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Response"

    # ========================================================================
    # Tests para fallback
    # ========================================================================

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.managers.conversation_manager.AIProviderFactory")
    @patch("app.managers.conversation_manager.SimpleProcessor")
    async def test_fallback_with_anthropic(self, mock_processor, mock_factory, manager, agent_config):
        """Debe hacer fallback a Anthropic cuando SimpleProcessor falla."""
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = MagicMock()
        mock_provider.supports_interleaved_files.return_value = True

        # Primer llamado (openai) - falla
        # Segundo llamado (claude) - éxito
        mock_factory.get_provider.side_effect = [mock_provider, mock_provider]

        mock_processor_instance = MagicMock()
        mock_processor_instance.process = AsyncMock(
            side_effect=[Exception("Primary failed"), {"text": "Fallback response"}]
        )
        mock_processor.return_value = mock_processor_instance

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello")

        result = await manager.process_conversation(request, agent_config)

        assert result["text"] == "Fallback response"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.managers.conversation_manager.AIProviderFactory")
    @patch("app.managers.conversation_manager.ToolGenerator")
    @patch("app.managers.conversation_manager.AgentProcessor")
    async def test_no_fallback_for_agent_processor(
        self, mock_agent, mock_tool_gen, mock_factory, manager, agent_config_with_tools
    ):
        """No debe hacer fallback cuando AgentProcessor falla."""
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = MagicMock()
        mock_provider.supports_interleaved_files.return_value = True
        mock_factory.get_provider.return_value = mock_provider

        mock_tool_gen.generate_tools.return_value = [MagicMock()]

        mock_processor_instance = MagicMock()
        mock_processor_instance.process = AsyncMock(side_effect=Exception("Agent failed"))
        mock_agent.return_value = mock_processor_instance

        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello")

        with pytest.raises(Exception) as exc_info:
            await manager.process_conversation(request, agent_config_with_tools)

        assert "Agent failed" in str(exc_info.value)
