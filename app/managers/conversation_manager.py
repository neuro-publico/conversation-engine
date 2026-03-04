import logging
import os
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

logger = logging.getLogger(__name__)


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
                response_data = await self._fallback_processing(request, agent_config, history)
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

    def _get_fallback_config(self, agent_config: AgentConfigResponse) -> dict:
        fc = {}
        if agent_config.metadata and "fallback_config" in agent_config.metadata:
            fc = agent_config.metadata["fallback_config"]

        return {
            "max_retries": fc.get("max_retries", int(os.getenv("FALLBACK_MAX_RETRIES", "1"))),
            "primary_fallback_provider": fc.get(
                "primary_fallback_provider", os.getenv("FALLBACK_PRIMARY_PROVIDER", "gemini")
            ),
            "primary_fallback_model": fc.get(
                "primary_fallback_model", os.getenv("FALLBACK_PRIMARY_MODEL", "gemini-flash-latest")
            ),
            "secondary_fallback_provider": fc.get(
                "secondary_fallback_provider", os.getenv("FALLBACK_SECONDARY_PROVIDER", "claude")
            ),
            "secondary_fallback_model": fc.get(
                "secondary_fallback_model", os.getenv("FALLBACK_SECONDARY_MODEL", "claude-sonnet-4-6")
            ),
        }

    async def _try_provider(
        self, provider_name: str, model: str, agent_config: AgentConfigResponse,
        request: MessageRequest, history: list
    ) -> dict[str, Any]:
        provider = AIProviderFactory.get_provider(provider_name)
        llm = provider.get_llm(
            model=model,
            temperature=agent_config.preferences.temperature,
            max_tokens=agent_config.preferences.max_tokens,
            top_p=agent_config.preferences.top_p,
        )
        processor = SimpleProcessor(llm, agent_config.prompt, history)
        return await processor.process(request, request.files, provider.supports_interleaved_files())

    async def _fallback_processing(
        self, request: MessageRequest, agent_config: AgentConfigResponse, history: list
    ) -> dict[str, Any]:
        fc = self._get_fallback_config(agent_config)

        # Retry with primary model
        max_retries = fc["max_retries"]
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Retry {attempt + 1}/{max_retries} with {agent_config.provider_ai}/{agent_config.model_ai}")
                return await self._try_provider(
                    agent_config.provider_ai, agent_config.model_ai, agent_config, request, history
                )
            except Exception as e:
                last_error = e
                logger.warning(f"Retry {attempt + 1}/{max_retries} failed: {e}")

        # Primary fallback
        try:
            logger.info(f"Primary fallback: {fc['primary_fallback_provider']}/{fc['primary_fallback_model']}")
            return await self._try_provider(
                fc["primary_fallback_provider"], fc["primary_fallback_model"],
                agent_config, request, history
            )
        except Exception as e:
            logger.warning(f"Primary fallback failed: {e}")

        # Secondary fallback
        try:
            logger.info(f"Secondary fallback: {fc['secondary_fallback_provider']}/{fc['secondary_fallback_model']}")
            return await self._try_provider(
                fc["secondary_fallback_provider"], fc["secondary_fallback_model"],
                agent_config, request, history
            )
        except Exception as e:
            logger.error(f"Secondary fallback also failed: {e}")
            raise last_error or e
