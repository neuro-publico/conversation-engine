from langchain_anthropic import ChatAnthropic

from app.providers.ai_provider_interface import AIProviderInterface


class AnthropicProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, max_tokens: int) -> ChatAnthropic:
        return ChatAnthropic(model=model, temperature=temperature, max_tokens=max_tokens)

    def supports_interleaved_files(self) -> bool:
        return True
