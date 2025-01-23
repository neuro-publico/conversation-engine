from abc import ABC, abstractmethod
from typing import Any, Protocol


class BaseChatModel(Protocol):
    """Protocol for chat models"""
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class AIProviderInterface(ABC):
    @abstractmethod
    def get_llm(self, model: str, temperature: float, max_tokens: int, top_p: float) -> BaseChatModel:
        """
        Retorna el modelo de lenguaje configurado
        """
        pass
