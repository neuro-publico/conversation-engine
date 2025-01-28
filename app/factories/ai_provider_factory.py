from app.providers.ai_provider_interface import AIProviderInterface
from app.providers.openai_provider import OpenAIProvider


class AIProviderFactory:
    @staticmethod
    def get_provider(provider_name: str) -> AIProviderInterface:
        providers = {
            "openai": OpenAIProvider()
        }

        if provider_name not in providers:
            raise ValueError(f"El proveedor de AI '{provider_name}' no está implementado")

        if provider_name == "openai":
            return OpenAIProvider()