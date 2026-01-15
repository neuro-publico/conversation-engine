from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel


class ConversationProcessor:
    def __init__(self, llm: BaseChatModel, context: str, history: List[str]):
        self.llm = llm
        self.context = context
        self.history = history

    def _get_langsmith_config(self, request, processor_type: str, **extra_metadata) -> Dict[str, Any]:
        config = {
            "tags": [processor_type, f"agent_{request.agent_id}"],
            "metadata": {"agent_id": request.agent_id, "conversation_id": request.conversation_id, **extra_metadata},
        }
        return config

    async def process(
        self, query: str, files: Optional[List[Dict[str, str]]], supports_interleaved_files: bool
    ) -> Dict[str, Any]:
        raise NotImplementedError
