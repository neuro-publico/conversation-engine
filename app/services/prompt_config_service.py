"""
Reads AI prompts (like SYSTEM_PROMPT, CTA_DETECTION_INSTRUCTION) from the
agent-config service so they can be edited at runtime without a code deploy.

The agent-config service already owns `agent_configs` (with versioning via
`prompt_versions`) — this module simply reuses that infrastructure for
prompts that don't belong to a specific agent execution but to the
hardcoded behavior of conversation-engine services.

Behavior:
- In-memory TTL cache per `agent_id` (process-local; each CE pod refreshes
  independently within CACHE_TTL_SECONDS).
- On any fetch error (network, 404, invalid payload), returns a fallback
  hardcoded at import-time by the consumer. Never raises if a fallback is
  registered.
- asyncio.Lock per class to avoid cache stampede when multiple concurrent
  requests miss the cache simultaneously.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

from app.externals.agent_config.agent_config_client import get_agent
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest

logger = logging.getLogger(__name__)


class PromptConfigService:
    CACHE_TTL_SECONDS: float = 60.0

    _cache: Dict[str, Tuple[str, float]] = {}
    _fallbacks: Dict[str, str] = {}
    _lock = asyncio.Lock()

    @classmethod
    def register_fallback(cls, agent_id: str, content: str) -> None:
        cls._fallbacks[agent_id] = content

    @classmethod
    def invalidate(cls, agent_id: Optional[str] = None) -> None:
        if agent_id is None:
            cls._cache.clear()
        else:
            cls._cache.pop(agent_id, None)

    @classmethod
    async def get(cls, agent_id: str) -> str:
        now = time.monotonic()
        cached = cls._cache.get(agent_id)
        if cached and now - cached[1] < cls.CACHE_TTL_SECONDS:
            return cached[0]

        async with cls._lock:
            cached = cls._cache.get(agent_id)
            if cached and time.monotonic() - cached[1] < cls.CACHE_TTL_SECONDS:
                return cached[0]

            content = await cls._fetch(agent_id)
            if content is None:
                fallback = cls._fallbacks.get(agent_id)
                if fallback is None:
                    raise RuntimeError(
                        f"AI prompt '{agent_id}' not available in agent-config and no fallback registered"
                    )
                logger.warning(f"Using fallback for AI prompt agent_id={agent_id}")
                return fallback

            cls._cache[agent_id] = (content, time.monotonic())
            return content

    @staticmethod
    async def _fetch(agent_id: str) -> Optional[str]:
        try:
            response = await get_agent(AgentConfigRequest(agent_id=agent_id, query=""))
        except Exception as e:
            logger.warning(f"agent-config fetch failed for agent_id={agent_id}: {type(e).__name__}: {e}")
            return None

        prompt = getattr(response, "prompt", None)
        if not isinstance(prompt, str) or not prompt:
            logger.warning(f"agent-config returned empty prompt for agent_id={agent_id}")
            return None
        return prompt
