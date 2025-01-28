from langchain.chat_models import ChatAnthropic
from app.providers.ai_provider_interface import AIProviderInterface


class AnthropicProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, max_tokens: int, top_p: int) -> ChatAnthropic:
        return ChatAnthropic(
            model=model,
            #temperature=temperature,
            #max_tokens=max_tokens,
            #top_p=top_p
        )
