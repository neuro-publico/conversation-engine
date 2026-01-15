from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse
from app.factories.ai_provider_factory import AIProviderFactory
from app.managers.conversation_manager_interface import ConversationManagerInterface
from app.processors.agent_processor import AgentProcessor
from app.processors.mcp_processor import MCPProcessor
from app.processors.simple_processor import SimpleProcessor
from app.requests.message_request import MessageRequest
from app.tools.tool_generator import ToolGenerator


class ConversationManager(ConversationManagerInterface):
    def __init__(self):
        self.history_store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_history_length: int = 10

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        if conversation_id:
            return self.history_store[conversation_id]
        return []

    async def process_conversation(self, request: MessageRequest, agent_config: AgentConfigResponse) -> dict[str, Any]:
        ai_provider = AIProviderFactory.get_provider(agent_config.provider_ai)
        llm = ai_provider.get_llm(
            model=agent_config.model_ai,
            temperature=agent_config.preferences.temperature,
            max_tokens=agent_config.preferences.max_tokens,
            top_p=agent_config.preferences.top_p,
        )

        history = self.get_conversation_history(request.conversation_id)
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
            response_data = await processor.process(request, request.files, ai_provider.supports_interleaved_files())
        except Exception as e:
            if is_simple:
                response_data = await self._fallback_with_anthropic(request, agent_config, history)
            else:
                raise e

        if request.conversation_id:
            ai_response_content = response_data.get("text")
            if ai_response_content is None:
                ai_response_content = str(response_data)

            self._update_conversation_history(
                conversation_id=request.conversation_id,
                user_message_content=request.query,
                ai_response_content=ai_response_content,
            )

        return response_data

    def _update_conversation_history(
        self, conversation_id: str, user_message_content: str, ai_response_content: str
    ) -> None:
        if not conversation_id:
            return

        self.history_store[conversation_id].append({"role": "user", "content": user_message_content})
        self.history_store[conversation_id].append({"role": "assistant", "content": ai_response_content})

        current_conv_history = self.history_store[conversation_id]
        if len(current_conv_history) > self.max_history_length:
            self.history_store[conversation_id] = current_conv_history[-self.max_history_length :]

    async def _fallback_with_anthropic(
        self, request: MessageRequest, agent_config: AgentConfigResponse, history: list
    ) -> dict[str, Any]:
        anthropic_provider = AIProviderFactory.get_provider("claude")
        anthropic_llm = anthropic_provider.get_llm(
            model="claude-3-7-sonnet-20250219",
            temperature=agent_config.preferences.temperature,
            max_tokens=agent_config.preferences.max_tokens,
            top_p=agent_config.preferences.top_p,
        )

        processor = SimpleProcessor(anthropic_llm, agent_config.prompt, history)

        return await processor.process(request, request.files, anthropic_provider.supports_interleaved_files())
