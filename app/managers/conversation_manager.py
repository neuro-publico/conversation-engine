from typing import Dict, Any, List
from app.managers.conversation_manager_interface import ConversationManagerInterface
from app.processors.agent_processor import AgentProcessor
from app.processors.simple_processor import SimpleProcessor
from app.requests.message_request import MessageRequest
from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse
from app.factories.ai_provider_factory import AIProviderFactory
from app.tools.tool_generator import ToolGenerator


class ConversationManager(ConversationManagerInterface):
    # TODO HISTORY
    def get_conversation_history(self, conversation_id: str) -> List[str]:
        return []

    async def process_conversation(self, request: MessageRequest, agent_config: AgentConfigResponse) -> dict[str, Any]:
        ai_provider = AIProviderFactory.get_provider(agent_config.provider_ai)
        llm = ai_provider.get_llm(
            model=agent_config.model_ai,
            temperature=agent_config.preferences.temperature,
            max_tokens=agent_config.preferences.max_tokens,
            top_p=agent_config.preferences.top_p
        )

        history = self.get_conversation_history(request.conversation_id) or []
        tools = ToolGenerator.generate_tools(agent_config.tools)

        processor = (
            AgentProcessor(llm, agent_config.prompt, history, tools)
            if tools
            else SimpleProcessor(llm, agent_config.prompt, history)
        )

        return await processor.process(request.query, request.files, ai_provider.supports_interleaved_files())
