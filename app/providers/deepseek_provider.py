from langchain_community.llms.ollama import Ollama
from app.providers.ai_provider_interface import AIProviderInterface
from app.configurations.config import DEEP_SEEK_HOST


class DeepseekProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, max_tokens: int, top_p: float) -> Ollama:
        model_kwargs = {
            "top_p": top_p,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        return Ollama(
            model=model,
            base_url=DEEP_SEEK_HOST
            ##**model_kwargs
        )
