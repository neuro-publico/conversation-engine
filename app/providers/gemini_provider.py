import os

from langchain_google_genai import ChatGoogleGenerativeAI

from app.providers.ai_provider_interface import AIProviderInterface


class GeminiProvider(AIProviderInterface):
    def get_llm(self, model: str, temperature: float, max_tokens: int, top_p: int = None) -> ChatGoogleGenerativeAI:
        kwargs = {
            "model": model,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "google_api_key": os.getenv("GOOGLE_GEMINI_API_KEY"),
        }
        if top_p is not None:
            kwargs["top_p"] = top_p
        return ChatGoogleGenerativeAI(**kwargs)

    def supports_interleaved_files(self) -> bool:
        return True
