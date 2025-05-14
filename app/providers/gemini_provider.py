import os

from langchain_google_genai import ChatGoogleGenerativeAI
from app.providers.ai_provider_interface import AIProviderInterface


class GeminiProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, max_tokens: int, top_p: int) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            google_api_key=os.getenv("GOOGLE_GEMINI_API_KEY")
        )

    def supports_interleaved_files(self) -> bool:
        return True
