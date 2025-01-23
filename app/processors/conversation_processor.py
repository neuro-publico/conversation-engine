from typing import Dict, Any, List
from langchain_core.language_models import BaseChatModel


class ConversationProcessor:
    def __init__(self, llm: BaseChatModel, context: str, history: List[str]):
        self.llm = llm
        self.context = context
        self.history = history

    async def process(self, query: str) -> Dict[str, Any]:
        raise NotImplementedError 