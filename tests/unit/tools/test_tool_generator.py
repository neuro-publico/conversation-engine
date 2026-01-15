"""
Tests para ToolGenerator.
Verifica la generación dinámica de herramientas LangChain.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.tools import StructuredTool

from app.tools.tool_generator import ToolGenerator


class TestToolGenerator:
    """Tests para ToolGenerator."""

    @pytest.fixture
    def sample_tool_config(self):
        """Configuración de herramienta de ejemplo."""
        return {
            "tool_name": "search_products",
            "description": "Search for products in the catalog",
            "config": {
                "name": "search_products",
                "description": "Search products",
                "api": "https://api.example.com/products/search",
                "method": "GET",
                "properties": [
                    {"name": "query", "description": "Search query string"},
                    {"name": "category", "description": "Product category filter"},
                ],
                "body": None,
                "headers": [{"Authorization": "Bearer {token}"}],
                "query_params": {"q": "{query}", "cat": "{category}"},
            },
        }

    @pytest.fixture
    def multiple_tool_configs(self, sample_tool_config):
        """Múltiples configuraciones de herramientas."""
        return [
            sample_tool_config,
            {
                "tool_name": "get_weather",
                "description": "Get weather information",
                "config": {
                    "name": "get_weather",
                    "description": "Weather API",
                    "api": "https://api.weather.com/current",
                    "method": "GET",
                    "properties": [{"name": "city", "description": "City name"}],
                    "body": None,
                    "headers": None,
                    "query_params": {"city": "{city}"},
                },
            },
        ]

    # ========================================================================
    # Tests para generate_tools
    # ========================================================================

    @pytest.mark.unit
    def test_generate_tools_returns_list(self, sample_tool_config):
        """Debe retornar lista de StructuredTool."""
        tools = ToolGenerator.generate_tools([sample_tool_config])

        assert isinstance(tools, list)
        assert len(tools) == 1
        assert isinstance(tools[0], StructuredTool)

    @pytest.mark.unit
    def test_generate_tools_empty_list(self):
        """Debe retornar lista vacía para input vacío."""
        tools = ToolGenerator.generate_tools([])
        assert tools == []

        tools = ToolGenerator.generate_tools(None)
        assert tools == []

    @pytest.mark.unit
    def test_generate_tools_multiple(self, multiple_tool_configs):
        """Debe generar múltiples herramientas."""
        tools = ToolGenerator.generate_tools(multiple_tool_configs)

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "search_products" in tool_names
        assert "get_weather" in tool_names

    @pytest.mark.unit
    def test_generated_tool_has_correct_name(self, sample_tool_config):
        """La herramienta debe tener el nombre correcto."""
        tools = ToolGenerator.generate_tools([sample_tool_config])

        assert tools[0].name == "search_products"

    @pytest.mark.unit
    def test_generated_tool_has_correct_description(self, sample_tool_config):
        """La herramienta debe tener la descripción correcta."""
        tools = ToolGenerator.generate_tools([sample_tool_config])

        assert tools[0].description == "Search for products in the catalog"

    @pytest.mark.unit
    def test_generated_tool_has_args_schema(self, sample_tool_config):
        """La herramienta debe tener schema de argumentos."""
        tools = ToolGenerator.generate_tools([sample_tool_config])

        assert tools[0].args_schema is not None
        # Verificar que tiene los campos definidos
        schema_fields = tools[0].args_schema.model_fields
        assert "query" in schema_fields
        assert "category" in schema_fields

    # ========================================================================
    # Tests para create_tool_function
    # ========================================================================

    @pytest.mark.unit
    @patch("app.tools.tool_generator.BaseRequestor.execute_request")
    def test_create_tool_function_executes_request(self, mock_execute, sample_tool_config):
        """La función creada debe ejecutar el request."""
        mock_execute.return_value = {"products": []}

        tool_func = ToolGenerator.create_tool_function(sample_tool_config)
        result = tool_func(query="test", category="electronics")

        assert "tool_result" in result
        mock_execute.assert_called_once()

    @pytest.mark.unit
    @patch("app.tools.tool_generator.BaseRequestor.execute_request")
    def test_create_tool_function_passes_kwargs(self, mock_execute, sample_tool_config):
        """La función debe pasar los kwargs al request."""
        mock_execute.return_value = {"data": "result"}

        tool_func = ToolGenerator.create_tool_function(sample_tool_config)
        tool_func(query="laptop", category="computers")

        call_args = mock_execute.call_args
        kwargs = call_args[0][1]
        assert kwargs["query"] == "laptop"
        assert kwargs["category"] == "computers"

    # ========================================================================
    # Tests para schema de argumentos
    # ========================================================================

    @pytest.mark.unit
    def test_args_schema_field_descriptions(self, sample_tool_config):
        """Los campos del schema deben tener descripciones."""
        tools = ToolGenerator.generate_tools([sample_tool_config])

        schema = tools[0].args_schema
        query_field = schema.model_fields["query"]

        assert query_field.description == "Search query string"

    @pytest.mark.unit
    def test_args_schema_all_fields_required(self, sample_tool_config):
        """Todos los campos deben ser requeridos por defecto."""
        tools = ToolGenerator.generate_tools([sample_tool_config])

        schema = tools[0].args_schema
        for field_name, field_info in schema.model_fields.items():
            assert field_info.is_required()

    @pytest.mark.unit
    def test_args_schema_unique_model_name(self, multiple_tool_configs):
        """Cada schema debe tener nombre de modelo único."""
        tools = ToolGenerator.generate_tools(multiple_tool_configs)

        schema_names = [t.args_schema.__name__ for t in tools]
        assert len(schema_names) == len(set(schema_names))  # Todos únicos

    # ========================================================================
    # Tests para callable
    # ========================================================================

    @pytest.mark.unit
    def test_generated_tool_is_callable(self, sample_tool_config):
        """La herramienta generada debe ser callable."""
        tools = ToolGenerator.generate_tools([sample_tool_config])

        assert callable(tools[0].func)

    @pytest.mark.unit
    @patch("app.tools.tool_generator.BaseRequestor.execute_request")
    def test_tool_func_returns_dict(self, mock_execute, sample_tool_config):
        """La función de herramienta debe retornar dict."""
        mock_execute.return_value = {"status": "ok"}

        tools = ToolGenerator.generate_tools([sample_tool_config])
        result = tools[0].func(query="test", category="test")

        assert isinstance(result, dict)
        assert "tool_result" in result
