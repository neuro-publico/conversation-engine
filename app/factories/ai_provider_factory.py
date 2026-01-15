from app.providers.ai_provider_interface import AIProviderInterface
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.deepseek_provider import DeepseekProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_provider import OpenAIProvider


class AIProviderFactory:
    @staticmethod
    def get_provider(provider_name: str) -> AIProviderInterface:
        if provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "claude":
            return AnthropicProvider()
        elif provider_name == "deepseek":
            return DeepseekProvider()
        elif provider_name == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(f"El proveedor de AI '{provider_name}' no está implementado")
