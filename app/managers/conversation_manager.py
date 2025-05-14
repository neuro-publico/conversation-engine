from typing import Dict, Any, List, Tuple
from app.managers.conversation_manager_interface import ConversationManagerInterface
from app.processors.agent_processor import AgentProcessor
from app.processors.simple_processor import SimpleProcessor
from app.requests.message_request import MessageRequest
from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse
from app.factories.ai_provider_factory import AIProviderFactory
from app.tools.tool_generator import ToolGenerator
from app.processors.mcp_processor import MCPProcessor


class ConversationManager(ConversationManagerInterface):
    # TODO HISTORY
    def get_conversation_history(self, conversation_id: str) -> List:
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
        is_simple = False

        if agent_config.mcp_config:
            processor = MCPProcessor(llm, agent_config.prompt, history, agent_config.mcp_config)
        else:
            tools = ToolGenerator.generate_tools(agent_config.tools or [])
            if tools:
                processor = AgentProcessor(llm, agent_config.prompt, history, tools)
            else:
                processor = SimpleProcessor(llm, agent_config.prompt, history)
                is_simple = True

        try:
            response = await processor.process(request, request.files, ai_provider.supports_interleaved_files())
        except Exception as e:
            if is_simple:
                response = await self._fallback_with_anthropic(request, agent_config, history)
            else:
                raise e

        return response

    async def _fallback_with_anthropic(self, request: MessageRequest, agent_config: AgentConfigResponse, history: list) -> dict[str, Any]:
        anthropic_provider = AIProviderFactory.get_provider("claude")
        anthropic_llm = anthropic_provider.get_llm(
            model="claude-3-7-sonnet-20250219",
            temperature=agent_config.preferences.temperature,
            max_tokens=agent_config.preferences.max_tokens,
            top_p=agent_config.preferences.top_p
        )
        processor = SimpleProcessor(anthropic_llm, agent_config.prompt, history)
        
        return await processor.process(request, request.files, anthropic_provider.supports_interleaved_files())
