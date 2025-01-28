from langchain_openai import ChatOpenAI
from app.providers.ai_provider_interface import AIProviderInterface


class OpenAIProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, max_tokens: int, top_p: float) -> ChatOpenAI:
        model_kwargs = {
            "top_p": top_p,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        return ChatOpenAI(
            model=model,
            ##**model_kwargs
        )
