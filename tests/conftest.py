"""
Configuración global de pytest para el proyecto conversational-engine.
Contiene fixtures compartidas entre todos los tests.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

# ============================================================================
# Fixtures para Modelos de Datos
# ============================================================================


@pytest.fixture
def sample_message_request_data() -> Dict[str, Any]:
    """Datos de ejemplo para MessageRequest."""
    return {
        "agent_id": "test-agent",
        "conversation_id": "conv-123",
        "query": "Hello, how are you?",
        "metadata_filter": [],
        "parameter_prompt": {"language": "es"},
        "files": [],
        "json_parser": None,
    }


@pytest.fixture
def sample_agent_config_data() -> Dict[str, Any]:
    """Datos de ejemplo para AgentConfigResponse."""
    return {
        "id": 1,
        "agent_id": "test-agent",
        "description": "Test agent description",
        "prompt": "You are a helpful assistant.",
        "provider_ai": "openai",
        "model_ai": "gpt-4",
        "preferences": {"temperature": 0.7, "max_tokens": 1000, "top_p": 1.0, "extra_parameters": None},
        "tools": [],
        "mcp_config": None,
    }


@pytest.fixture
def sample_product_data() -> Dict[str, Any]:
    """Datos de ejemplo para un producto scrapeado."""
    return {
        "name": "Test Product",
        "description": "A test product description",
        "external_sell_price": "29.99",
        "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
    }


@pytest.fixture
def sample_amazon_product_data() -> Dict[str, Any]:
    """Datos de ejemplo de respuesta de Amazon."""
    return {
        "data": {
            "product_title": "Amazon Test Product",
            "product_description": "Product description from Amazon",
            "product_price": "$49.99",
            "product_photos": ["https://amazon.com/img1.jpg", "https://amazon.com/img2.jpg"],
            "product_variations_dimensions": ["Color", "Size"],
            "product_variations": {
                "Color": [{"value": "Red", "photo": "https://amazon.com/red.jpg"}],
                "Size": [{"value": "Large"}],
            },
            "all_product_variations": {},
        }
    }


@pytest.fixture
def sample_aliexpress_product_data() -> Dict[str, Any]:
    """Datos de ejemplo de respuesta de AliExpress."""
    return {
        "result": {
            "item": {
                "title": "AliExpress Test Product",
                "description": {"html": "<p>Product description</p>"},
                "images": ["//ae01.alicdn.com/img1.jpg"],
                "sku": {"def": {"promotionPrice": "15.99", "price": "19.99"}, "base": [], "props": []},
            }
        }
    }


# ============================================================================
# Fixtures para Mocks de Servicios Externos
# ============================================================================


@pytest.fixture
def mock_httpx_client():
    """Mock para httpx.AsyncClient."""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


@pytest.fixture
def mock_llm():
    """Mock para modelos de lenguaje LangChain."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="Test response"))
    return mock


@pytest.fixture
def mock_agent_config():
    """Mock para AgentConfigResponse."""
    from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse, AgentPreferences

    return AgentConfigResponse(
        id=1,
        agent_id="test-agent",
        description="Test agent",
        prompt="You are a helpful assistant.",
        provider_ai="openai",
        model_ai="gpt-4",
        preferences=AgentPreferences(temperature=0.7, max_tokens=1000, top_p=1.0, extra_parameters=None),
        tools=[],
        mcp_config=None,
    )


@pytest.fixture
def mock_conversation_manager():
    """Mock para ConversationManager."""
    mock = MagicMock()
    mock.get_conversation_history = MagicMock(return_value=[])
    mock.process_conversation = AsyncMock(return_value={"text": "Test response"})
    return mock


@pytest.fixture
def mock_message_service():
    """Mock para MessageService."""
    mock = MagicMock()
    mock.handle_message = AsyncMock(return_value={"text": "Test response"})
    mock.handle_message_json = AsyncMock(return_value={"result": "test"})
    mock.handle_message_with_config = AsyncMock(
        return_value={"message": {"text": "Test response"}, "agent_config": MagicMock()}
    )
    return mock


@pytest.fixture
def mock_fal_client():
    """Mock para FalClient."""
    mock = MagicMock()
    mock.tts_multilingual_v2 = AsyncMock(return_value={"audio_url": "https://example.com/audio.mp3"})
    mock.kling_image_to_video = AsyncMock(return_value={"video_url": "https://example.com/video.mp4"})
    mock.bytedance_omnihuman = AsyncMock(return_value={"video_url": "https://example.com/human.mp4"})
    return mock


# ============================================================================
# Fixtures para Testing de API
# ============================================================================


@pytest.fixture
def mock_request():
    """Mock para FastAPI Request."""
    mock = MagicMock()
    mock.headers = {"authorization": "Bearer test-token", "x-api-key": "test-api-key"}
    mock.state = MagicMock()
    mock.state.user_info = {"data": {"id": "user-123"}}
    return mock


# ============================================================================
# Fixtures para Imágenes y Archivos
# ============================================================================


@pytest.fixture
def sample_base64_image() -> str:
    """Base64 de una imagen de prueba pequeña (1x1 pixel PNG)."""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_html_content() -> str:
    """HTML de ejemplo para testing de scrapers."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Product</title>
        <script>console.log('test');</script>
        <style>.test { color: red; }</style>
    </head>
    <body>
        <h1 class="product-title">Test Product Name</h1>
        <div class="price">$29.99</div>
        <img src="https://example.com/img.jpg" alt="Product Image" />
        <p class="description">This is a test product description.</p>
    </body>
    </html>
    """


# ============================================================================
# Fixtures para Tools
# ============================================================================


@pytest.fixture
def sample_tool_config() -> Dict[str, Any]:
    """Configuración de ejemplo para una herramienta."""
    return {
        "tool_name": "test_tool",
        "description": "A test tool for testing purposes",
        "config": {
            "name": "test_tool",
            "description": "Test tool",
            "api": "https://api.example.com/test",
            "method": "POST",
            "properties": [
                {"name": "param1", "description": "First parameter"},
                {"name": "param2", "description": "Second parameter"},
            ],
            "body": {"param1": "{param1}", "param2": "{param2}"},
            "headers": [{"Content-Type": "application/json"}],
            "query_params": None,
        },
    }


# ============================================================================
# Fixtures de Configuración de Environment
# ============================================================================


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock de variables de entorno comunes."""
    env_vars = {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "GOOGLE_GEMINI_API_KEY": "test-gemini-key",
        "FAL_AI_API_KEY": "test-fal-key",
        "GOOGLE_VISION_API_KEY": "test-vision-key",
        "API_KEY": "test-api-key",
        "HOST_AGENT_CONFIG": "http://localhost:8000",
        "DEEP_SEEK_HOST": "http://localhost:11434",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars
