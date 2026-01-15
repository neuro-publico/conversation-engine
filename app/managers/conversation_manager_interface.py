from abc import ABC, abstractmethod

from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse
from app.requests.message_request import MessageRequest


class ConversationManagerInterface(ABC):
    @abstractmethod
    async def process_conversation(self, request: MessageRequest, agent_config: AgentConfigResponse) -> str:
        pass
