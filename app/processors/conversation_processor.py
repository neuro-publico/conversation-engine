from typing import Dict, Any, List, Optional
from langchain_core.language_models import BaseChatModel


class ConversationProcessor:
    def __init__(self, llm: BaseChatModel, context: str, history: List[str]):
        self.llm = llm
        self.context = context
        self.history = history

    async def process(self, query: str, files: Optional[List[Dict[str, str]]], supports_interleaved_files: bool) -> Dict[str, Any]:
        raise NotImplementedError
