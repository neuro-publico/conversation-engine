"""Avatar Strategist pipeline.

One LLM call (Gemini 3.1 Pro, structured output) that takes a product +
its sales/audience context and returns a multi-avatar campaign roster.
Each avatar in the roster is paired with a distinct sales angle and carries
its own fully-composed JSON prompt ready for the image model.

Design mirrors ``avatar_director_service`` (same agent-config flow, same
Gemini call helper), but the response schema is multi-item instead of
single-item. One strategist call = roster of N avatars. The ecommerce
backend then loops and hits the image model per entry.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from app.externals.agent_config.agent_config_client import get_agent
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.externals.ai_direct.gemini_text import GeminiTextError, call_gemini_structured
from app.requests.avatar_strategist_request import AvatarStrategistRequest
from app.responses.avatar_strategist_response import AvatarEntry, AvatarStrategistResponse
from app.services.avatar_strategist_service_interface import AvatarStrategistServiceInterface

logger = logging.getLogger(__name__)


class AvatarStrategistError(Exception):
    """Raised when the Avatar Strategist pipeline fails."""

    def __init__(self, message: str, step: str, raw: Optional[str] = None):
        super().__init__(message)
        self.step = step
        self.raw = raw


class AvatarStrategistService(AvatarStrategistServiceInterface):
    """Multi-avatar campaign roster generator."""

    async def run(self, request: AvatarStrategistRequest) -> AvatarStrategistResponse:
        t_start = time.monotonic()

        # 1. Load agent
        try:
            agent_config = await get_agent(
                AgentConfigRequest(
                    agent_id=request.agent_id,
                    query=request.product_name or "avatar_strategist",
                    parameter_prompt={},
                )
            )
        except Exception as e:
            logger.error("[AVATAR_STRATEGIST] failed to load agent %s: %s", request.agent_id, e)
            raise AvatarStrategistError(
                f"Could not load agent_config for {request.agent_id}: {e}",
                step="agent_config_load",
            ) from e

        # 2. Render system prompt
        rendered_prompt = self._render_prompt(agent_config.prompt, request)

        # 3. Build structured response schema
        num_variants = max(1, min(6, request.num_variants or 3))
        response_schema = self._build_response_schema(num_variants)

        # 4. One-shot Gemini call
        user_message = (
            f"Write the JSON campaign roster NOW. Product: '{request.product_name or 'unspecified'}'. "
            f"Number of avatars: {num_variants}. Return ONLY the JSON."
        )

        thinking_level: Optional[str] = None
        try:
            prefs = getattr(agent_config, "preferences", None)
            if prefs is not None:
                thinking_level = (
                    getattr(prefs, "thinking_level", None)
                    if not isinstance(prefs, dict)
                    else prefs.get("thinking_level")
                )
        except Exception:
            thinking_level = None
        effective_thinking_level = thinking_level if thinking_level else "High"

        try:
            parsed, raw_response = await call_gemini_structured(
                model=agent_config.model_ai,
                system_prompt=rendered_prompt,
                user_message=user_message,
                response_schema=response_schema,
                temperature=agent_config.preferences.temperature,
                top_p=agent_config.preferences.top_p,
                max_output_tokens=agent_config.preferences.max_tokens,
                thinking_level=effective_thinking_level,
            )
        except GeminiTextError as e:
            raise AvatarStrategistError(
                f"Gemini strategist call failed: {e}",
                step="strategist",
                raw=e.raw,
            ) from e

        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        usage = (raw_response.get("usageMetadata") or {}) if isinstance(raw_response, dict) else {}

        # 5. Parse the roster
        avatars_raw = parsed.get("avatars", []) if isinstance(parsed, dict) else []
        avatars = []
        for a in avatars_raw:
            try:
                avatars.append(
                    AvatarEntry(
                        angle_name=a.get("angle_name", "unknown_angle"),
                        angle_category=a.get("angle_category"),
                        angle_description=a.get("angle_description"),
                        suggested_dialogue_line=a.get("suggested_dialogue_line"),
                        target_viewer_segment=a.get("target_viewer_segment"),
                        prompt_json=a.get("prompt_json", {}),
                    )
                )
            except Exception as e:
                logger.warning("[AVATAR_STRATEGIST] avatar entry parse warn: %s", e)

        logger.info(
            "[AVATAR_STRATEGIST] owner=%s product=%s roster=%d elapsed=%dms tokens_in=%s tokens_out=%s",
            request.owner_id,
            request.product_name,
            len(avatars),
            elapsed_ms,
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
        )

        return AvatarStrategistResponse(
            product_analysis=parsed.get("product_analysis") if isinstance(parsed, dict) else None,
            avatars=avatars,
            tokens_input=usage.get("promptTokenCount"),
            tokens_output=usage.get("candidatesTokenCount"),
            elapsed_ms=elapsed_ms,
            model_used=agent_config.model_ai,
        )

    # ─────────────────────────────────────────────────────────
    # helpers
    # ─────────────────────────────────────────────────────────

    def _render_prompt(self, template: str, request: AvatarStrategistRequest) -> str:
        """Placeholder substitution (explicit replace, not ``format_map``)."""
        variables: Dict[str, str] = {
            "product_name": request.product_name or "",
            "product_description": request.product_description or "",
            "product_image_url": request.product_image_url or "",
            "sale_angle_name": request.sale_angle_name or "",
            "sale_angle_description": request.sale_angle_description or "",
            "target_audience_description": request.target_audience_description or "",
            "target_audience_vibe": request.target_audience_vibe or "",
            "user_instruction": request.user_instruction or "",
            "language": request.language or "es",
            "num_variants": str(request.num_variants or 3),
            "owner_country": request.owner_country or "",
            "owner_niche": request.owner_niche or "",
        }

        try:
            rendered = template
            for key, value in variables.items():
                rendered = rendered.replace("{" + key + "}", value)
            return rendered
        except Exception as e:
            raise AvatarStrategistError(
                f"Failed to render system prompt template: {e}",
                step="prompt_render",
            ) from e

    def _build_response_schema(self, num_variants: int) -> Dict[str, Any]:
        """Structured output schema. Loose-typed leaves — we enforce SHAPE.

        The ``prompt_json`` leaf is left as an untyped OBJECT so the LLM has
        freedom to include the same fields the director emits. Downstream
        consumers (ecommerce backend, image model) don't need to validate
        structure — they serialize the object as a string and hand it off.
        """
        string = {"type": "STRING"}

        product_analysis = {
            "type": "OBJECT",
            "properties": {
                "pain_or_outcome": string,
                "real_buyer_description": string,
                "conversion_aha_moment": string,
                "regional_markers_detected": {"type": "ARRAY", "items": string},
            },
            "required": ["pain_or_outcome", "real_buyer_description"],
        }

        # prompt_json uses a minimal shape hint — Gemini structured output
        # demands SOMETHING, but we want the model free to include the full
        # director-level detail. So we list the top-level sections it must
        # emit without pinning nested fields. (Gemini's structured schema
        # treats absent nested properties as free-form strings/objects.)
        prompt_json_shape = {
            "type": "OBJECT",
            "properties": {
                "image_type": string,
                "shot": {"type": "OBJECT", "properties": {"type": string}, "required": []},
                "character": {
                    "type": "OBJECT",
                    "properties": {"identity_name": string, "age": string, "gender": string},
                    "required": ["identity_name", "age", "gender"],
                },
                "pose_and_hands": {"type": "OBJECT", "properties": {}, "required": []},
                "environment": {
                    "type": "OBJECT",
                    "properties": {"location": string},
                    "required": ["location"],
                },
                "style": {"type": "OBJECT", "properties": {}, "required": []},
                "negative_prompt": string,
                "technical_specs": {"type": "OBJECT", "properties": {}, "required": []},
            },
            "required": ["character", "environment", "negative_prompt"],
        }

        avatar_item = {
            "type": "OBJECT",
            "properties": {
                "angle_name": string,
                "angle_category": string,
                "angle_description": string,
                "suggested_dialogue_line": string,
                "target_viewer_segment": string,
                "prompt_json": prompt_json_shape,
            },
            "required": ["angle_name", "prompt_json"],
        }

        return {
            "type": "OBJECT",
            "properties": {
                "product_analysis": product_analysis,
                "avatars": {
                    "type": "ARRAY",
                    "items": avatar_item,
                    "minItems": num_variants,
                    "maxItems": num_variants,
                },
            },
            "required": ["avatars"],
        }
