"""
Tests para los modelos Pydantic de requests y responses.
Verifica la validación y serialización de datos.
"""

import pytest
from pydantic import ValidationError

from app.externals.agent_config.responses.agent_config_response import (
    AgentConfigResponse,
    AgentPreferences,
    Config,
    Property,
    Tool,
)
from app.requests.message_request import MessageRequest, MetadataFilter


class TestMessageRequest:
    """Tests para MessageRequest."""

    @pytest.mark.unit
    def test_create_basic_request(self):
        """Debe crear request con campos requeridos."""
        request = MessageRequest(agent_id="test-agent", conversation_id="conv-123", query="Hello")

        assert request.agent_id == "test-agent"
        assert request.conversation_id == "conv-123"
        assert request.query == "Hello"
        assert request.metadata_filter == []
        assert request.parameter_prompt == {}
        assert request.files == []
        assert request.json_parser is None

    @pytest.mark.unit
    def test_create_full_request(self):
        """Debe crear request con todos los campos."""
        request = MessageRequest(
            agent_id="test-agent",
            conversation_id="conv-123",
            query="Hello",
            metadata_filter=[MetadataFilter(key="category", value="tech")],
            parameter_prompt={"language": "es"},
            files=[{"type": "image", "url": "https://example.com/img.jpg"}],
            json_parser={"result": "string"},
        )

        assert len(request.metadata_filter) == 1
        assert request.parameter_prompt["language"] == "es"
        assert len(request.files) == 1
        assert request.json_parser == {"result": "string"}

    @pytest.mark.unit
    def test_missing_required_fields_raises_error(self):
        """Debe lanzar error para campos requeridos faltantes."""
        with pytest.raises(ValidationError):
            MessageRequest(agent_id="test")  # Falta conversation_id y query

    @pytest.mark.unit
    def test_empty_strings_allowed(self):
        """Debe permitir strings vacíos."""
        request = MessageRequest(agent_id="", conversation_id="", query="")

        assert request.agent_id == ""


class TestMetadataFilter:
    """Tests para MetadataFilter."""

    @pytest.mark.unit
    def test_create_filter(self):
        """Debe crear filtro correctamente."""
        filter = MetadataFilter(key="category", value="electronics")

        assert filter.key == "category"
        assert filter.value == "electronics"
        assert filter.evaluator == "="  # Default

    @pytest.mark.unit
    def test_custom_evaluator(self):
        """Debe aceptar evaluadores personalizados."""
        filter = MetadataFilter(key="price", value="100", evaluator=">")

        assert filter.evaluator == ">"

    @pytest.mark.unit
    def test_missing_key_raises_error(self):
        """Debe lanzar error si falta key."""
        with pytest.raises(ValidationError):
            MetadataFilter(value="test")


class TestAgentConfigResponse:
    """Tests para AgentConfigResponse."""

    @pytest.mark.unit
    def test_create_basic_config(self):
        """Debe crear configuración básica."""
        config = AgentConfigResponse(
            id=1,
            agent_id="test-agent",
            description="Test agent",
            prompt="You are helpful",
            provider_ai="openai",
            model_ai="gpt-4",
            preferences=AgentPreferences(),
        )

        assert config.id == 1
        assert config.agent_id == "test-agent"
        assert config.tools == []
        assert config.mcp_config is None

    @pytest.mark.unit
    def test_config_with_tools(self):
        """Debe crear configuración con herramientas."""
        config = AgentConfigResponse(
            id=1,
            agent_id="test-agent",
            description="Test",
            prompt="Prompt",
            provider_ai="openai",
            model_ai="gpt-4",
            preferences=AgentPreferences(),
            tools=[{"tool_name": "search", "description": "Search tool"}],
        )

        assert len(config.tools) == 1
        assert config.tools[0]["tool_name"] == "search"

    @pytest.mark.unit
    def test_config_with_mcp(self):
        """Debe crear configuración con MCP."""
        config = AgentConfigResponse(
            id=1,
            agent_id="test-agent",
            description="Test",
            prompt="Prompt",
            provider_ai="openai",
            model_ai="gpt-4",
            preferences=AgentPreferences(),
            mcp_config={"servers": [{"url": "http://localhost"}]},
        )

        assert config.mcp_config is not None
        assert "servers" in config.mcp_config


class TestAgentPreferences:
    """Tests para AgentPreferences."""

    @pytest.mark.unit
    def test_default_values(self):
        """Debe usar valores por defecto."""
        prefs = AgentPreferences()

        assert prefs.temperature == 0.7
        assert prefs.max_tokens == 1000
        assert prefs.top_p == 1.0
        assert prefs.extra_parameters is None

    @pytest.mark.unit
    def test_custom_values(self):
        """Debe aceptar valores personalizados."""
        prefs = AgentPreferences(
            temperature=0.5, max_tokens=2000, top_p=0.9, extra_parameters={"presence_penalty": 0.5}
        )

        assert prefs.temperature == 0.5
        assert prefs.max_tokens == 2000
        assert prefs.top_p == 0.9
        assert prefs.extra_parameters["presence_penalty"] == 0.5


class TestToolModels:
    """Tests para modelos de herramientas."""

    @pytest.mark.unit
    def test_create_property(self):
        """Debe crear Property."""
        prop = Property(name="query", description="Search query")

        assert prop.name == "query"
        assert prop.description == "Search query"

    @pytest.mark.unit
    def test_create_config(self):
        """Debe crear Config."""
        config = Config(
            properties=[Property(name="q", description="Query")],
            name="search",
            description="Search API",
            api="https://api.example.com/search",
            method="GET",
            body=None,
            headers=None,
            query_params={"q": "{q}"},
        )

        assert config.name == "search"
        assert len(config.properties) == 1
        assert config.method == "GET"

    @pytest.mark.unit
    def test_create_tool(self):
        """Debe crear Tool."""
        tool = Tool(
            id=1,
            tool_name="search",
            description="Search tool",
            config=Config(
                properties=[],
                name="search",
                description="Search",
                api="https://api.example.com",
                method="POST",
                body=None,
                headers=None,
                query_params=None,
            ),
        )

        assert tool.id == 1
        assert tool.tool_name == "search"


class TestRequestValidation:
    """Tests para validación de varios request models."""

    @pytest.mark.unit
    def test_message_request_serialization(self):
        """Debe serializar a dict correctamente."""
        request = MessageRequest(agent_id="test", conversation_id="conv", query="Hello")

        data = request.model_dump()

        assert data["agent_id"] == "test"
        assert data["conversation_id"] == "conv"
        assert data["query"] == "Hello"

    @pytest.mark.unit
    def test_agent_config_serialization(self):
        """Debe serializar AgentConfigResponse correctamente."""
        config = AgentConfigResponse(
            id=1,
            agent_id="test",
            description="Test",
            prompt="Prompt",
            provider_ai="openai",
            model_ai="gpt-4",
            preferences=AgentPreferences(),
        )

        data = config.model_dump()

        assert data["id"] == 1
        assert "preferences" in data
        assert data["preferences"]["temperature"] == 0.7
