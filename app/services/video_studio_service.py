"""Director Creative pipeline for the new ads video flow.

Replaces the legacy 4-call independent flow (video_concept_* + video_script_*
+ ad_scene + video_scene_prompt) with a single Director Creative LLM call that
emits a complete structured plan in one shot:

  - selected_pattern_key + reasoning
  - concept_visual_brief
  - script_part_a + script_part_b (combo)
  - cinematic_camera_a/b
  - cinematic_prompt_a/b
  - viral_hook_first_3_seconds
  - ends_with_product_name (self-check)

Architecture decisions:

  1. **Reuses agent-config**. Calls AgentConfigClient.get_agent() to fetch the
     agent's prompt + provider + model + metadata. The agent's metadata is the
     "creative pattern library" — adding new patterns is just editing JSON in
     agent-config-front, no code changes.

  2. **Bypasses LangChain**. Once we have the agent_config, we render the prompt
     locally and call Gemini directly via app/externals/ai_direct/gemini_text.py.
     Why: LangChain wrappers don't expose responseSchema, thinkingConfig or
     prompt caching, which are critical for structured output.

  3. **Local prompt rendering**. The agent's prompt has placeholders like
     {product_name}, {creative_patterns_json}. agent-config server-side templating
     would need both the request fields AND the metadata, but it only sees
     parameter_prompt. So we render everything in Python with str.format_map +
     a defaultdict that preserves missing keys (no crashes if the agent prompt
     evolves).

  4. **Validators with self-correction loop**. After parsing, we run validators
     defined in metadata.video_studio.validators. If any fails, we re-call the
     LLM once more with corrective feedback. Hard cap of 2 attempts to avoid
     infinite loops.

  5. **Persists in prompt_logs**. Every LLM call (success, retry, error) goes
     to analytics.prompt_logs with log_type="video_director" and metadata
     containing draft_reference_id. No new audit table.

  6. **Provider-agnostic by design**. agent_config.provider_ai picks the
     adapter. Today only Gemini is wired (D4). To add Anthropic / OpenAI in
     the future, drop a new client in app/externals/ai_direct/ and route here.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from app.db.audit_logger import log_prompt
from app.externals.agent_config.agent_config_client import get_agent
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.externals.agent_config.responses.agent_config_response import AgentConfigResponse
from app.externals.ai_direct.gemini_text import GeminiTextError, call_gemini_structured
from app.externals.callback.callback_client import post_callback
from app.requests.video_studio_draft_request import VideoStudioDraftRequest
from app.responses.video_studio_draft_response import VideoStudioDraftReadyPayload
from app.services.video_studio_service_interface import VideoStudioServiceInterface

logger = logging.getLogger(__name__)


class VideoStudioError(Exception):
    """Raised when the Director Creative pipeline fails after retries."""

    def __init__(self, message: str, step: str, raw: Optional[str] = None):
        super().__init__(message)
        self.step = step
        self.raw = raw


# Cámaras válidas para los cinematic_camera_* — debe matchear el enum del system prompt.
_VALID_CAMERAS = {
    "ORBIT",
    "LOW_ANGLE_HERO",
    "DUTCH_ANGLE",
    "DOLLY_LATERAL",
    "HANDHELD",
    "WHIP_PAN",
    "CRASH_ZOOM",
}

# Verbos en mayúscula que cuentan como "acción física" para el validator
# min_actions_in_cinematic. Lista deliberadamente amplia.
_ACTION_VERBS_PATTERN = re.compile(
    r"\b("
    r"LUNGES?|JUMPS?|BOUNCES?|SPINS?|ROTATES?|LEANS?|STOMPS?|SHAKES?|SLAMS?|"
    r"SLIDES?|POINTS?|CROSSES?|THROWS?|ROLLS?|CLUTCHES?|ROCKS?|TREMBLES?|"
    r"WAVES?|PUSHES?|PULLS?|RAISES?|LOWERS?|TURNS?|TWISTS?|COLLAPSES?|"
    r"BURSTS?|SNAPS?|GRABS?|RUBS?|JABS?|TILTS?|CRASHES?|KICKS?|DROPS?"
    r")\b"
)


class _SafeFormatDict(dict):
    """Dict que devuelve `{key}` literal si la clave no existe.

    Permite renderizar templates con str.format_map sin crashear si el agente
    en agent-config evoluciona y agrega un placeholder nuevo que el código
    todavía no provee.
    """

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class VideoStudioService(VideoStudioServiceInterface):
    """Implementation of the Director Creative pipeline."""

    async def run_director(self, request: VideoStudioDraftRequest) -> VideoStudioDraftReadyPayload:
        t_start = time.monotonic()

        # 1. Cargar agent_config (incluye prompt + metadata.video_studio).
        try:
            agent_config = await get_agent(
                AgentConfigRequest(
                    agent_id=request.agent_id,
                    query=request.product_name,
                    parameter_prompt={},
                )
            )
        except Exception as e:
            logger.error("[VIDEO_STUDIO] failed to load agent_config %s: %s", request.agent_id, e)
            raise VideoStudioError(
                f"Could not load agent_config for {request.agent_id}: {e}",
                step="agent_config_load",
            ) from e

        studio_config = self._extract_studio_config(agent_config)
        creative_patterns = studio_config.get("creative_patterns", [])
        if not creative_patterns:
            raise VideoStudioError(
                f"Agent {request.agent_id} has no metadata.video_studio.creative_patterns. "
                f"Add the patterns in agent-config-front before running.",
                step="agent_config_validation",
            )

        active_patterns = [p for p in creative_patterns if p.get("active", True)]
        if not active_patterns:
            raise VideoStudioError(
                "All creative_patterns are inactive. Activate at least one in agent-config-front.",
                step="agent_config_validation",
            )

        # 2. Renderizar el prompt localmente con todas las variables.
        rendered_prompt = self._render_prompt(
            template=agent_config.prompt,
            request=request,
            active_patterns=active_patterns,
        )

        # 3. Construir el JSON Schema para structured output forzado.
        response_schema = self._build_response_schema(is_combo=request.is_combo)

        # 4. Llamada a Gemini direct con self-correction loop (max 2 intentos).
        validators = studio_config.get("validators", [])
        max_correction_attempts = 2
        last_validation_errors: List[str] = []
        feedback_addendum = ""
        parsed: Dict[str, Any] = {}
        raw_response: Dict[str, Any] = {}
        attempts_used = 0

        for correction_attempt in range(1, max_correction_attempts + 1):
            attempts_used = correction_attempt

            full_system_prompt = rendered_prompt + feedback_addendum
            user_message = (
                f"Generá el plan completo del video para el producto '{request.product_name}'. "
                f"Devolvé SOLO el JSON estructurado."
            )

            try:
                parsed, raw_response = await call_gemini_structured(
                    model=agent_config.model_ai,
                    system_prompt=full_system_prompt,
                    user_message=user_message,
                    response_schema=response_schema,
                    temperature=agent_config.preferences.temperature,
                    top_p=agent_config.preferences.top_p,
                    max_output_tokens=agent_config.preferences.max_tokens,
                    thinking_level="High",
                )
            except GeminiTextError as e:
                # Persistimos el error en prompt_logs antes de relanzar.
                asyncio.create_task(
                    log_prompt(
                        log_type="video_director",
                        prompt=full_system_prompt[:5000],
                        response_text=(e.raw or "")[:5000],
                        owner_id=request.owner_id,
                        agent_id=request.agent_id,
                        model=agent_config.model_ai,
                        provider="gemini",
                        status="error",
                        error_message=str(e),
                        attempt_number=correction_attempt,
                        elapsed_ms=int((time.monotonic() - t_start) * 1000),
                        metadata={
                            "draft_reference_id": request.reference_id,
                            "step_name": "director",
                            "style_id": request.style_id,
                        },
                    )
                )
                raise VideoStudioError(
                    f"Gemini director call failed: {e}",
                    step="director",
                    raw=e.raw,
                ) from e

            # 5. Validators sobre el output parseado.
            validation_errors = self._validate_payload(
                parsed=parsed,
                request=request,
                validators=validators,
            )

            if not validation_errors:
                # Éxito.
                asyncio.create_task(
                    log_prompt(
                        log_type="video_director",
                        prompt=full_system_prompt[:5000],
                        response_text=json.dumps(parsed)[:5000],
                        owner_id=request.owner_id,
                        agent_id=request.agent_id,
                        model=agent_config.model_ai,
                        provider="gemini",
                        status="success",
                        attempt_number=correction_attempt,
                        elapsed_ms=int((time.monotonic() - t_start) * 1000),
                        metadata={
                            "draft_reference_id": request.reference_id,
                            "step_name": "director",
                            "style_id": request.style_id,
                            "selected_pattern_key": parsed.get("selected_pattern_key"),
                            "tokens_input": (raw_response.get("usageMetadata", {}) or {}).get("promptTokenCount"),
                            "tokens_output": (raw_response.get("usageMetadata", {}) or {}).get("candidatesTokenCount"),
                        },
                    )
                )
                return VideoStudioDraftReadyPayload(**parsed)

            # Validación falló: armamos feedback explícito y reintentamos.
            last_validation_errors = validation_errors
            logger.warning(
                "[VIDEO_STUDIO] validation failed attempt=%d errors=%s",
                correction_attempt,
                validation_errors,
            )
            feedback_addendum = (
                "\n\n══════════════════════════════════\n"
                "CORRECCIÓN OBLIGATORIA — tu intento anterior falló estas validaciones:\n"
                + "\n".join(f"- {err}" for err in validation_errors)
                + "\n\nDevolvé el JSON corregido respetando TODAS las reglas. Cero excusas."
            )

            asyncio.create_task(
                log_prompt(
                    log_type="video_director",
                    prompt=full_system_prompt[:5000],
                    response_text=json.dumps(parsed)[:5000],
                    owner_id=request.owner_id,
                    agent_id=request.agent_id,
                    model=agent_config.model_ai,
                    provider="gemini",
                    status="validation_failed",
                    error_message="; ".join(validation_errors)[:1000],
                    attempt_number=correction_attempt,
                    elapsed_ms=int((time.monotonic() - t_start) * 1000),
                    metadata={
                        "draft_reference_id": request.reference_id,
                        "step_name": "director",
                        "style_id": request.style_id,
                        "validation_errors": validation_errors,
                    },
                )
            )

        # Si llegamos acá, los 2 intentos fallaron validación.
        raise VideoStudioError(
            f"Director output failed validation after {attempts_used} attempts: "
            f"{'; '.join(last_validation_errors)}",
            step="validation",
        )

    async def run_and_callback(self, request: VideoStudioDraftRequest) -> None:
        """Run the director and post the result to callback_url. Never raises."""
        try:
            payload = await self.run_director(request)
            cb_payload = {
                "status": "success",
                "reference_id": request.reference_id,
                "director_payload": payload.model_dump(),
                "selected_pattern_key": payload.selected_pattern_key,
                "metadata": request.callback_metadata or {},
            }
        except VideoStudioError as e:
            logger.error(
                "[VIDEO_STUDIO] pipeline failed reference_id=%s step=%s: %s",
                request.reference_id,
                e.step,
                e,
            )
            cb_payload = {
                "status": "error",
                "reference_id": request.reference_id,
                "error": str(e),
                "error_step": e.step,
                "metadata": request.callback_metadata or {},
            }
        except Exception as e:
            logger.error(
                "[VIDEO_STUDIO] unexpected error reference_id=%s: %s",
                request.reference_id,
                e,
                exc_info=True,
            )
            cb_payload = {
                "status": "error",
                "reference_id": request.reference_id,
                "error": f"unexpected: {e}",
                "error_step": "unknown",
                "metadata": request.callback_metadata or {},
            }

        if not request.callback_url:
            logger.info(
                "[VIDEO_STUDIO] no callback_url provided for reference_id=%s, skipping",
                request.reference_id,
            )
            return

        try:
            await post_callback(request.callback_url, cb_payload)
        except Exception as e:
            logger.error(
                "[VIDEO_STUDIO] callback POST failed for reference_id=%s: %s",
                request.reference_id,
                e,
            )

    # ─────────────────────────────────────────────────────────
    # Helpers privados
    # ─────────────────────────────────────────────────────────

    def _extract_studio_config(self, agent_config: AgentConfigResponse) -> Dict[str, Any]:
        """Lee `metadata.video_studio` del agente. Devuelve dict vacío si no existe."""
        meta = agent_config.metadata or {}
        return meta.get("video_studio", {}) or {}

    def _render_prompt(
        self,
        template: str,
        request: VideoStudioDraftRequest,
        active_patterns: List[Dict[str, Any]],
    ) -> str:
        """Renderiza el system prompt del agente con todas las variables locales.

        Usa str.format_map con un defaultdict que preserva placeholders missing
        para no romper si el agente evoluciona.
        """
        creative_patterns_json = json.dumps(
            active_patterns,
            ensure_ascii=False,
            indent=2,
        )

        variables = _SafeFormatDict(
            product_name=request.product_name or "",
            product_description=request.product_description or "",
            language=request.language or "es",
            duration=str(request.duration),
            is_combo="true" if request.is_combo else "false",
            sale_angle_name=request.sale_angle_name or "",
            sale_angle_description=request.sale_angle_description or "",
            target_audience_description=request.target_audience_description or "",
            target_audience_vibe=request.target_audience_vibe or "",
            user_instruction=request.user_instruction or "",
            creative_patterns_json=creative_patterns_json,
        )

        try:
            return template.format_map(variables)
        except Exception as e:
            logger.error("[VIDEO_STUDIO] template rendering failed: %s", e)
            raise VideoStudioError(
                f"Failed to render system prompt template: {e}",
                step="prompt_render",
            ) from e

    def _build_response_schema(self, is_combo: bool) -> Dict[str, Any]:
        """Construye el JSON Schema para responseSchema de Gemini.

        Required dinámico según si es combo o no:
          - Combo: script_part_b, cinematic_camera_b y cinematic_prompt_b son requeridos
          - No combo: pueden ser null
        """
        properties = {
            "selected_pattern_key": {"type": "STRING"},
            "selection_reasoning": {"type": "STRING"},
            "concept_visual_brief": {"type": "STRING"},
            "script_part_a": {"type": "STRING"},
            "script_part_b": {"type": "STRING", "nullable": True},
            "ends_with_product_name": {"type": "BOOLEAN"},
            "cinematic_camera_a": {
                "type": "STRING",
                "enum": list(_VALID_CAMERAS),
            },
            "cinematic_camera_b": {
                "type": "STRING",
                "enum": list(_VALID_CAMERAS),
                "nullable": True,
            },
            "cinematic_prompt_a": {"type": "STRING"},
            "cinematic_prompt_b": {"type": "STRING", "nullable": True},
            "viral_hook_first_3_seconds": {"type": "STRING"},
        }

        required = [
            "selected_pattern_key",
            "selection_reasoning",
            "concept_visual_brief",
            "script_part_a",
            "ends_with_product_name",
            "cinematic_camera_a",
            "cinematic_prompt_a",
            "viral_hook_first_3_seconds",
        ]
        if is_combo:
            required.extend(["script_part_b", "cinematic_camera_b", "cinematic_prompt_b"])

        return {
            "type": "OBJECT",
            "properties": properties,
            "required": required,
        }

    def _validate_payload(
        self,
        parsed: Dict[str, Any],
        request: VideoStudioDraftRequest,
        validators: List[str],
    ) -> List[str]:
        """Ejecuta los validators del metadata sobre el output parseado.

        Cada validator es un string del estilo `name` o `name:param`. Devuelve
        una lista de mensajes de error (vacía si todo pasó).
        """
        errors: List[str] = []

        for v in validators:
            if ":" in v:
                name, param = v.split(":", 1)
            else:
                name, param = v, None

            if name == "ends_with_product_name":
                target = (parsed.get("script_part_b") if request.is_combo else parsed.get("script_part_a")) or ""
                if request.product_name and request.product_name not in target:
                    errors.append(
                        f"ends_with_product_name: el script de cierre no contiene "
                        f"'{request.product_name}'. Está: '{target[:120]}...'"
                    )

            elif name == "camera_varies_between_scenes":
                if request.is_combo:
                    cam_a = parsed.get("cinematic_camera_a")
                    cam_b = parsed.get("cinematic_camera_b")
                    if cam_a and cam_b and cam_a == cam_b:
                        errors.append(
                            f"camera_varies_between_scenes: cinematic_camera_a y "
                            f"cinematic_camera_b son ambas '{cam_a}'. Tienen que ser distintas."
                        )

            elif name == "min_actions_in_cinematic":
                min_actions = int(param or "6")
                for branch_key in ("cinematic_prompt_a", "cinematic_prompt_b"):
                    txt = parsed.get(branch_key) or ""
                    if not txt:
                        continue
                    matches = _ACTION_VERBS_PATTERN.findall(txt)
                    distinct = len(set(m.upper() for m in matches))
                    if distinct < min_actions:
                        errors.append(
                            f"min_actions_in_cinematic: {branch_key} tiene "
                            f"{distinct} acciones distintas, mínimo {min_actions}."
                        )

            elif name == "max_words_part_a":
                max_w = int(param or "25")
                txt = parsed.get("script_part_a") or ""
                wc = len(txt.split())
                if wc > max_w:
                    errors.append(f"max_words_part_a: script_part_a tiene {wc} palabras, máximo {max_w}.")

            elif name == "max_words_part_b":
                if request.is_combo:
                    max_w = int(param or "25")
                    txt = parsed.get("script_part_b") or ""
                    wc = len(txt.split())
                    if wc > max_w:
                        errors.append(f"max_words_part_b: script_part_b tiene {wc} palabras, máximo {max_w}.")
            else:
                logger.warning("[VIDEO_STUDIO] unknown validator '%s' — skipping", name)

        return errors
