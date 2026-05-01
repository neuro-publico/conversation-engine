"""Scene Composer pipeline.

Single fast Gemini Flash call that resolves the ``setting_key`` +
``scene_brief`` for a preset-avatar + product pair. The ecommerce backend
calls this right before ``generateModelingImage`` so the composite render
matches the product's natural use context (tech → desk, food → kitchen,
fitness → gym) instead of inheriting whatever setting the preset was
originally created with.

Designed to be lightweight: flash model, thinking disabled, ~1k output
tokens. Typical call completes in ~4-8 seconds.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from app.externals.agent_config.agent_config_client import get_agent
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.externals.ai_direct.gemini_text import GeminiTextError, call_gemini_structured
from app.requests.scene_composer_request import SceneComposerRequest
from app.responses.scene_composer_response import SceneComposerResponse
from app.services.scene_composer_service_interface import SceneComposerServiceInterface

logger = logging.getLogger(__name__)


class SceneComposerError(Exception):
    def __init__(self, message: str, step: str, raw: Optional[str] = None):
        super().__init__(message)
        self.step = step
        self.raw = raw


VALID_SETTINGS = {
    "home_kitchen",
    "home_bathroom",
    "home_bedroom",
    "home_living_room",
    "home_student",
    "home_office",
    "gym",
    "office",
    "car",
    "cafe",
    "outdoor_patio",
    "business_retail",
    "business_trade",
}


class SceneComposerService(SceneComposerServiceInterface):
    async def run(self, request: SceneComposerRequest) -> SceneComposerResponse:
        t_start = time.monotonic()

        try:
            agent_config = await get_agent(
                AgentConfigRequest(
                    agent_id=request.agent_id,
                    query=request.product_name or "scene_composer",
                    parameter_prompt={},
                )
            )
        except Exception as e:
            raise SceneComposerError(
                f"Could not load agent_config for {request.agent_id}: {e}",
                step="agent_config_load",
            ) from e

        rendered_prompt = self._render_prompt(agent_config.prompt, request)
        response_schema = self._build_response_schema()

        user_message = (
            f"Pick the setting for product='{request.product_name or 'unspecified'}'. " f"Return ONLY the JSON."
        )

        # thinking disabled on flash for speed
        thinking_level: Optional[str] = None

        try:
            parsed, raw_response = await call_gemini_structured(
                model=agent_config.model_ai,
                system_prompt=rendered_prompt,
                user_message=user_message,
                response_schema=response_schema,
                temperature=agent_config.preferences.temperature,
                top_p=agent_config.preferences.top_p,
                max_output_tokens=agent_config.preferences.max_tokens,
                thinking_level=thinking_level,
            )
        except GeminiTextError as e:
            raise SceneComposerError(
                f"Gemini scene-composer call failed: {e}",
                step="composer",
                raw=e.raw,
            ) from e

        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        usage = (raw_response.get("usageMetadata") or {}) if isinstance(raw_response, dict) else {}

        # Defensive validation on setting_key. The agent is trained to pick
        # from a menu but if it hallucinates a key we clamp to a safe default.
        setting_key = parsed.get("setting_key", "home_living_room")
        if setting_key not in VALID_SETTINGS:
            logger.warning("[SCENE_COMPOSER] invalid setting_key '%s' — clamping to home_living_room", setting_key)
            setting_key = "home_living_room"

        scene_brief = parsed.get("scene_brief", "")
        if not scene_brief.strip():
            logger.warning("[SCENE_COMPOSER] empty scene_brief — falling back to safe default")
            scene_brief = "A lived-in home setting with natural light. Product held at chest level, label visible."

        logger.info(
            "[SCENE_COMPOSER] owner=%s product=%s setting=%s elapsed=%dms tokens=%s/%s reason=%s",
            request.owner_id,
            request.product_name,
            setting_key,
            elapsed_ms,
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
            (parsed.get("override_reason") or "")[:120],
        )

        return SceneComposerResponse(
            setting_key=setting_key,
            override_reason=parsed.get("override_reason"),
            scene_brief=scene_brief,
            outfit_description=parsed.get("outfit_description"),
            outfit_changed_vs_preset=parsed.get("outfit_changed_vs_preset"),
            negative_add=parsed.get("negative_add"),
            tokens_input=usage.get("promptTokenCount"),
            tokens_output=usage.get("candidatesTokenCount"),
            elapsed_ms=elapsed_ms,
            model_used=agent_config.model_ai,
        )

    def _render_prompt(self, template: str, request: SceneComposerRequest) -> str:
        variables: Dict[str, str] = {
            "product_name": request.product_name or "",
            "product_description": request.product_description or "",
            "product_image_url": request.product_image_url or "",
            "preset_setting_key": request.preset_setting_key or "",
            "sale_angle_name": request.sale_angle_name or "",
            "target_audience_description": request.target_audience_description or "",
            "language": request.language or "es",
        }
        rendered = template
        for k, v in variables.items():
            rendered = rendered.replace("{" + k + "}", v)
        return rendered

    def _build_response_schema(self) -> Dict[str, Any]:
        return {
            "type": "OBJECT",
            "properties": {
                "setting_key": {"type": "STRING"},
                "override_reason": {"type": "STRING"},
                "scene_brief": {"type": "STRING"},
                "outfit_description": {"type": "STRING"},
                "outfit_changed_vs_preset": {"type": "BOOLEAN"},
                "negative_add": {"type": "STRING"},
            },
            "required": ["setting_key", "scene_brief"],
        }
