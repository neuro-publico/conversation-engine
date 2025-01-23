from abc import ABC, abstractmethod
from app.requests.message_request import MessageRequest
from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse


class ConversationManagerInterface(ABC):
    @abstractmethod
    async def process_conversation(self, request: MessageRequest, agent_config: AgentConfigResponse) -> str:
        pass
