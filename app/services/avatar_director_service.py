"""Avatar Director pipeline.

Single LLM call (Gemini 3.1 Pro with structured output) that composes a
narratively-coherent avatar hero-image JSON prompt from product + wizard
context. See ``agents/avatar_director_v1.json`` for the agent prompt and
``app/requests/avatar_director_request.py`` for the input contract.

Architecture notes:
  - Reuses the same agent-config infra as ``video_studio_service`` —
    ``get_agent()`` fetches prompt + model + preferences. Editing the
    agent prompt is just editing the JSON in agent-config-front, no
    redeploy.
  - Direct Gemini call (bypass LangChain) so we can use responseSchema
    + thinkingConfig. Schema pins the JSON shape the ecommerce backend
    expects; any drift from the agent prompt is caught at parse time.
  - Synchronous. Unlike ``video_studio_service`` which uses a callback
    because the video draft has multiple downstream steps, an avatar
    image is a single-round trip — no reason to push async complexity
    onto callers.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from app.externals.agent_config.agent_config_client import get_agent
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.externals.ai_direct.gemini_text import GeminiTextError, call_gemini_structured
from app.requests.avatar_director_request import AvatarDirectorRequest
from app.responses.avatar_director_response import AvatarDirectorResponse
from app.services.avatar_director_service_interface import AvatarDirectorServiceInterface

logger = logging.getLogger(__name__)


class AvatarDirectorError(Exception):
    """Raised when the Avatar Director pipeline fails."""

    def __init__(self, message: str, step: str, raw: Optional[str] = None):
        super().__init__(message)
        self.step = step
        self.raw = raw


class AvatarDirectorService(AvatarDirectorServiceInterface):
    """Single-call avatar prompt director."""

    async def run(self, request: AvatarDirectorRequest) -> AvatarDirectorResponse:
        t_start = time.monotonic()

        # 1. Load the agent (prompt + model + preferences).
        try:
            agent_config = await get_agent(
                AgentConfigRequest(
                    agent_id=request.agent_id,
                    query=request.product_name or "avatar",
                    parameter_prompt={},
                )
            )
        except Exception as e:
            logger.error("[AVATAR_DIRECTOR] failed to load agent_config %s: %s", request.agent_id, e)
            raise AvatarDirectorError(
                f"Could not load agent_config for {request.agent_id}: {e}",
                step="agent_config_load",
            ) from e

        # 2. Render the agent prompt with the caller's context.
        rendered_prompt = self._render_prompt(agent_config.prompt, request)

        # 3. Build the structured response schema (Gemini enforces this).
        response_schema = self._build_response_schema()

        # 4. One-shot call to Gemini.
        user_message = (
            f"Write the JSON avatar prompt now. Product: '{request.product_name or 'unspecified'}'. "
            f"Return ONLY the JSON."
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
            raise AvatarDirectorError(
                f"Gemini director call failed: {e}",
                step="director",
                raw=e.raw,
            ) from e

        elapsed_ms = int((time.monotonic() - t_start) * 1000)

        # 5. Summarize metadata for logs/UI.
        usage = (raw_response.get("usageMetadata") or {}) if isinstance(raw_response, dict) else {}
        character = parsed.get("character", {}) if isinstance(parsed, dict) else {}
        environment = parsed.get("environment", {}) if isinstance(parsed, dict) else {}

        identity_name = character.get("identity_name")
        ancestry = character.get("ancestry", "")
        # First 80 chars of ancestry description = label.
        ancestry_label = ancestry.split(".")[0] if ancestry else None
        location = environment.get("location", "")
        location_summary = location[:120] if location else None

        logger.info(
            "[AVATAR_DIRECTOR] owner=%s product=%s name=%s elapsed=%dms tokens_in=%s tokens_out=%s",
            request.owner_id,
            request.product_name,
            identity_name,
            elapsed_ms,
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
        )

        return AvatarDirectorResponse(
            prompt_json=parsed,
            selected_identity_name=identity_name,
            selected_ancestry_label=ancestry_label,
            selected_location_summary=location_summary,
            tokens_input=usage.get("promptTokenCount"),
            tokens_output=usage.get("candidatesTokenCount"),
            elapsed_ms=elapsed_ms,
            seed_used=request.seed,
            model_used=agent_config.model_ai,
        )

    # ─────────────────────────────────────────────────────────
    # helpers
    # ─────────────────────────────────────────────────────────

    def _render_prompt(self, template: str, request: AvatarDirectorRequest) -> str:
        """Substitute `{placeholder}` tokens in the agent prompt.

        Same explicit-replace approach as ``video_studio_service._render_prompt``
        to avoid ``str.format_map`` colliding with JSON braces in the prompt.
        """
        variables: Dict[str, str] = {
            "product_name": request.product_name or "",
            "product_description": request.product_description or "",
            "sale_angle_name": request.sale_angle_name or "",
            "sale_angle_description": request.sale_angle_description or "",
            "target_audience_description": request.target_audience_description or "",
            "target_audience_vibe": request.target_audience_vibe or "",
            "user_instruction": request.user_instruction or "",
            "language": request.language or "es",
            "wiz_gender": request.wiz_gender or "",
            "wiz_age_vibe": request.wiz_age_vibe or "",
            "wiz_ancestry": request.wiz_ancestry or "",
            "wiz_personality": request.wiz_personality or "",
            "wiz_location_context": request.wiz_location_context or "",
        }

        try:
            rendered = template
            for key, value in variables.items():
                rendered = rendered.replace("{" + key + "}", value)
            return rendered
        except Exception as e:
            logger.error("[AVATAR_DIRECTOR] template rendering failed: %s", e)
            raise AvatarDirectorError(
                f"Failed to render system prompt template: {e}",
                step="prompt_render",
            ) from e

    def _build_response_schema(self) -> Dict[str, Any]:
        """JSON schema for ``responseSchema`` (Gemini enforces at decode time).

        Loose-typed on leaves (all strings) because the agent prompt already
        tells the model the exact semantic for each field; we enforce SHAPE
        here, not VALUES. Any value-level validation (e.g. detect 'generic
        latina' markers in ``ancestry``) lives downstream.
        """
        string = {"type": "STRING"}
        obj = lambda properties, required: {
            "type": "OBJECT",
            "properties": properties,
            "required": required,
        }

        shot_props = {
            "type": string,
            "camera_statement": string,
            "camera_position": string,
            "camera_stability": string,
            "device": string,
            "focus_rule": string,
            "framing": string,
            "aspect_ratio": string,
            "image_quality": string,
        }
        character_props = {
            "identity_name": string,
            "age": string,
            "gender": string,
            "ancestry": string,
            "personality": string,
            "face_shape": string,
            "eye_shape": string,
            "eye_asymmetry": string,
            "eye_color": string,
            "eyebrows": string,
            "nose": string,
            "lips": string,
            "chin_jaw": string,
            "ears": string,
            "forehead": string,
            "cheeks": string,
            "skin_texture": string,
            "skin_imperfections": string,
            "skin_tone": string,
            "skin_shine": string,
            "hair_texture": string,
            "hair_length": string,
            "hair_color": string,
            "hair_realism": string,
            "clothing": string,
            "distinctive_identity_anchors": string,
        }
        hands_props = {
            "setup_rule": string,
            "left_hand": string,
            "right_hand": string,
            "hand_realism": string,
            "no_phone_in_hands_RULE": string,
        }
        performance_props = {
            "emotion_baseline": string,
            "position": string,
            "micro_expressions": string,
            "body_language": string,
            "authenticity_behaviors": string,
        }
        dialogue_props = {
            "accent": string,
            "tone": string,
            "line": string,
            "no_subtitles": string,
        }
        # environment has variant fields (desk_setup vs counter_setup, behind_her
        # vs behind_him). We accept any of them via nullable siblings.
        environment_props = {
            "location": string,
            "desk_setup_visible_at_frame_bottom": {"type": "STRING", "nullable": True},
            "counter_setup_visible_at_frame_bottom": {"type": "STRING", "nullable": True},
            "behind_her": {"type": "STRING", "nullable": True},
            "behind_him": {"type": "STRING", "nullable": True},
            "lighting": string,
            "background_sharpness": string,
            "background_imperfections": string,
            "ambient_audio": string,
            "no_music": string,
        }
        style_props = {
            "aesthetic": string,
            "color_grading": string,
            "lens_character": string,
        }
        technical_props = {
            "resolution": string,
            "duration_seconds": {"type": "INTEGER"},
            "fps": {"type": "INTEGER"},
            "audio_sync": string,
            "camera_movement": string,
        }

        return obj(
            properties={
                "shot": obj(shot_props, list(shot_props.keys())),
                "character": obj(character_props, list(character_props.keys())),
                "hands_and_product": obj(hands_props, list(hands_props.keys())),
                "performance": obj(performance_props, list(performance_props.keys())),
                "dialogue": obj(dialogue_props, list(dialogue_props.keys())),
                "environment": obj(
                    environment_props,
                    [
                        "location",
                        "lighting",
                        "background_sharpness",
                        "background_imperfections",
                        "ambient_audio",
                        "no_music",
                    ],
                ),
                "style": obj(style_props, list(style_props.keys())),
                "negative_prompt": string,
                "technical_specs": obj(technical_props, list(technical_props.keys())),
            },
            required=[
                "shot",
                "character",
                "hands_and_product",
                "performance",
                "dialogue",
                "environment",
                "style",
                "negative_prompt",
                "technical_specs",
            ],
        )
