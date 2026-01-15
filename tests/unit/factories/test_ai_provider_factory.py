"""
Tests para AIProviderFactory.
Verifica la correcta instanciación de proveedores de IA.
"""

import pytest

from app.factories.ai_provider_factory import AIProviderFactory
from app.providers.ai_provider_interface import AIProviderInterface
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.deepseek_provider import DeepseekProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_provider import OpenAIProvider


class TestAIProviderFactory:
    """Tests para AIProviderFactory."""

    @pytest.mark.unit
    def test_get_openai_provider(self):
        """Debe retornar una instancia de OpenAIProvider para 'openai'."""
        provider = AIProviderFactory.get_provider("openai")

        assert provider is not None
        assert isinstance(provider, OpenAIProvider)
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_get_anthropic_provider(self):
        """Debe retornar una instancia de AnthropicProvider para 'claude'."""
        provider = AIProviderFactory.get_provider("claude")

        assert provider is not None
        assert isinstance(provider, AnthropicProvider)
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_get_gemini_provider(self):
        """Debe retornar una instancia de GeminiProvider para 'gemini'."""
        provider = AIProviderFactory.get_provider("gemini")

        assert provider is not None
        assert isinstance(provider, GeminiProvider)
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_get_deepseek_provider(self):
        """Debe retornar una instancia de DeepseekProvider para 'deepseek'."""
        provider = AIProviderFactory.get_provider("deepseek")

        assert provider is not None
        assert isinstance(provider, DeepseekProvider)
        assert isinstance(provider, AIProviderInterface)

    @pytest.mark.unit
    def test_invalid_provider_raises_error(self):
        """Debe lanzar ValueError para un proveedor no implementado."""
        with pytest.raises(ValueError) as exc_info:
            AIProviderFactory.get_provider("invalid_provider")

        assert "no está implementado" in str(exc_info.value)
        assert "invalid_provider" in str(exc_info.value)

    @pytest.mark.unit
    def test_empty_provider_raises_error(self):
        """Debe lanzar ValueError para un proveedor vacío."""
        with pytest.raises(ValueError) as exc_info:
            AIProviderFactory.get_provider("")

        assert "no está implementado" in str(exc_info.value)

    @pytest.mark.unit
    def test_case_sensitive_provider_names(self):
        """Los nombres de proveedores deben ser case-sensitive."""
        with pytest.raises(ValueError):
            AIProviderFactory.get_provider("OpenAI")

        with pytest.raises(ValueError):
            AIProviderFactory.get_provider("CLAUDE")

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "provider_name,expected_class",
        [
            ("openai", OpenAIProvider),
            ("claude", AnthropicProvider),
            ("gemini", GeminiProvider),
            ("deepseek", DeepseekProvider),
        ],
    )
    def test_all_providers_parametrized(self, provider_name, expected_class):
        """Test parametrizado para todos los proveedores válidos."""
        provider = AIProviderFactory.get_provider(provider_name)

        assert isinstance(provider, expected_class)
        assert isinstance(provider, AIProviderInterface)
