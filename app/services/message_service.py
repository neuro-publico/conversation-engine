from app.externals.agent_config.agent_config_client import get_agent
from app.requests.message_request import MessageRequest
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.services.message_service_interface import MessageServiceInterface
from app.managers.conversation_manager_interface import ConversationManagerInterface
from fastapi import Depends


class MessageService(MessageServiceInterface):
    def __init__(self, conversation_manager: ConversationManagerInterface = Depends()):
        self.conversation_manager = conversation_manager

    async def handle_message(self, request: MessageRequest):
        data = AgentConfigRequest(
            agent_id=request.agent_id,
            query=request.query,
            metadata_filter=request.metadata_filter,
            parameter_prompt=request.parameter_prompt
        )

        agent_config = await get_agent(data)

        return await self.conversation_manager.process_conversation(
            request=request,
            agent_config=agent_config
        )
