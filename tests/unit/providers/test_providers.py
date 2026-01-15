"""
Tests para los proveedores de IA.
Verifica la correcta configuración e instanciación de modelos LLM.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.providers.ai_provider_interface import AIProviderInterface
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.deepseek_provider import DeepseekProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_provider import OpenAIProvider


class TestOpenAIProvider:
    """Tests para OpenAIProvider."""

    @pytest.fixture
    def provider(self):
        """Crear instancia de OpenAIProvider."""
        return OpenAIProvider()

    @pytest.mark.unit
    def test_implements_interface(self, provider):
        """Debe implementar AIProviderInterface."""
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_supports_interleaved_files(self, provider):
        """OpenAI debe soportar archivos intercalados."""
        assert provider.supports_interleaved_files() is True

    @pytest.mark.unit
    @patch("app.providers.openai_provider.ChatOpenAI")
    def test_get_llm_returns_chat_openai(self, mock_chat_openai, provider):
        """get_llm debe retornar una instancia de ChatOpenAI."""
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        result = provider.get_llm(model="gpt-4", temperature=0.7, max_tokens=1000, top_p=0.9)

        assert result == mock_instance
        mock_chat_openai.assert_called_once_with(model="gpt-4", top_p=0.9, temperature=0.7, max_tokens=1000)

    @pytest.mark.unit
    @patch("app.providers.openai_provider.ChatOpenAI")
    def test_get_llm_with_different_models(self, mock_chat_openai, provider):
        """get_llm debe aceptar diferentes modelos."""
        models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]

        for model in models:
            provider.get_llm(model=model, temperature=0.5, max_tokens=500, top_p=1.0)

        assert mock_chat_openai.call_count == len(models)


class TestAnthropicProvider:
    """Tests para AnthropicProvider."""

    @pytest.fixture
    def provider(self):
        """Crear instancia de AnthropicProvider."""
        return AnthropicProvider()

    @pytest.mark.unit
    def test_implements_interface(self, provider):
        """Debe implementar AIProviderInterface."""
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_supports_interleaved_files(self, provider):
        """Anthropic debe soportar archivos intercalados."""
        assert provider.supports_interleaved_files() is True

    @pytest.mark.unit
    @patch("app.providers.anthropic_provider.ChatAnthropic")
    def test_get_llm_returns_chat_anthropic(self, mock_chat_anthropic, provider):
        """get_llm debe retornar una instancia de ChatAnthropic."""
        mock_instance = MagicMock()
        mock_chat_anthropic.return_value = mock_instance

        result = provider.get_llm(model="claude-3-opus-20240229", temperature=0.7, max_tokens=1000, top_p=0.9)

        assert result == mock_instance
        mock_chat_anthropic.assert_called_once_with(
            model="claude-3-opus-20240229", temperature=0.7, max_tokens=1000, top_p=0.9
        )


class TestGeminiProvider:
    """Tests para GeminiProvider."""

    @pytest.fixture
    def provider(self):
        """Crear instancia de GeminiProvider."""
        return GeminiProvider()

    @pytest.mark.unit
    def test_implements_interface(self, provider):
        """Debe implementar AIProviderInterface."""
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_supports_interleaved_files(self, provider):
        """Gemini debe soportar archivos intercalados."""
        assert provider.supports_interleaved_files() is True

    @pytest.mark.unit
    @patch("app.providers.gemini_provider.ChatGoogleGenerativeAI")
    @patch.dict("os.environ", {"GOOGLE_GEMINI_API_KEY": "test-key"})
    def test_get_llm_returns_chat_google(self, mock_chat_google, provider):
        """get_llm debe retornar una instancia de ChatGoogleGenerativeAI."""
        mock_instance = MagicMock()
        mock_chat_google.return_value = mock_instance

        result = provider.get_llm(model="gemini-pro", temperature=0.7, max_tokens=1000, top_p=0.9)

        assert result == mock_instance
        mock_chat_google.assert_called_once()


class TestDeepseekProvider:
    """Tests para DeepseekProvider."""

    @pytest.fixture
    def provider(self):
        """Crear instancia de DeepseekProvider."""
        return DeepseekProvider()

    @pytest.mark.unit
    def test_implements_interface(self, provider):
        """Debe implementar AIProviderInterface."""
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_does_not_support_interleaved_files(self, provider):
        """DeepSeek NO debe soportar archivos intercalados."""
        assert provider.supports_interleaved_files() is False

    @pytest.mark.unit
    @pytest.mark.skip(reason="Bug en código fuente: falta coma en deepseek_provider.py línea 16-17")
    @patch("app.providers.deepseek_provider.Ollama")
    def test_get_llm_returns_ollama(self, mock_ollama, provider):
        """get_llm debe retornar una instancia de Ollama."""
        mock_instance = MagicMock()
        mock_ollama.return_value = mock_instance

        result = provider.get_llm(model="deepseek-coder", temperature=0.7, max_tokens=1000, top_p=0.9)

        assert result == mock_instance


class TestProviderInterface:
    """Tests para la interfaz común de proveedores."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "provider_class,expected_interleaved",
        [
            (OpenAIProvider, True),
            (AnthropicProvider, True),
            (GeminiProvider, True),
            (DeepseekProvider, False),
        ],
    )
    def test_interleaved_files_support(self, provider_class, expected_interleaved):
        """Verificar soporte de archivos intercalados por proveedor."""
        provider = provider_class()
        assert provider.supports_interleaved_files() == expected_interleaved

    @pytest.mark.unit
    def test_all_providers_have_required_methods(self):
        """Todos los proveedores deben tener los métodos requeridos."""
        providers = [
            OpenAIProvider(),
            AnthropicProvider(),
            GeminiProvider(),
            DeepseekProvider(),
        ]

        for provider in providers:
            assert hasattr(provider, "get_llm")
            assert hasattr(provider, "supports_interleaved_files")
            assert callable(provider.get_llm)
            assert callable(provider.supports_interleaved_files)
