"""Gemini text caller v2 — uses official `google-genai` SDK + Interactions API.

Replaces the direct REST calls in `gemini_text.py`. Benefits:
- Streaming (Server-Sent Events) avoids the ~60s server-side disconnect we
  hit with `generateContent` when thinking + output exceed that budget.
- Server-managed conversation state via `previous_interaction_id` (opt-in).
- Official SDK maintained by Google; the legacy `google-generativeai` is
  deprecated per the `gemini-skills` repo.

Same shape as the v1 functions so the services can swap imports with a
one-line change.

Docs:
  https://github.com/google-gemini/gemini-skills/blob/main/skills/gemini-interactions-api/SKILL.md
  https://ai.google.dev/gemini-api/docs/interactions
"""

import logging
import os
from typing import Any, Dict, List, Optional

from app.configurations.config import GOOGLE_GEMINI_API_KEY

logger = logging.getLogger(__name__)


class GeminiTextV2Error(Exception):
    """Raised when the v2 Gemini call fails after retries."""


def _get_client():
    """Lazy-construct the genai client so imports don't fail if the SDK is
    missing (lets us keep v1 working until v2 is fully validated).
    """
    # The SDK reads GOOGLE_API_KEY from the env; propagate our config name.
    if GOOGLE_GEMINI_API_KEY and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = GOOGLE_GEMINI_API_KEY
    from google import genai  # noqa: WPS433 — lazy import on purpose

    return genai.Client()


async def call_gemini_freeform_v2(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    max_output_tokens: int = 32768,
    thinking_level: Optional[str] = None,
    previous_interaction_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Free-form text generation via Interactions API with streaming.

    Args:
        model: Gemini model id (e.g. ``"gemini-3.1-pro-preview"``).
        system_prompt: System instruction.
        user_message: The current user turn.
        conversation_history: Optional list of prior turns (ignored if
            ``previous_interaction_id`` is provided — server keeps state then).
            Each item: ``{"role": "user"|"model", "text": "..."}``.
        temperature: Sampling temperature.
        max_output_tokens: Output cap.
        thinking_level: Lowercase string: ``"low"``, ``"medium"``, ``"high"``.
            For ``gemini-3.1-pro-preview`` only ``"low"`` and ``"high"`` apply
            (``"high"`` is the default and burns many thought tokens; use
            ``"low"`` for HTML generation to keep latency down).
        previous_interaction_id: If set, server resumes the conversation —
            do NOT also pass ``conversation_history``.

    Returns:
        ``{"text": str, "interaction_id": str, "usage": dict}``.

    Raises:
        GeminiTextV2Error: on failure.
    """
    client = _get_client()

    gen_cfg: Dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if thinking_level:
        gen_cfg["thinking_level"] = thinking_level

    # Build the input: when we pass previous_interaction_id the server has the
    # history; otherwise we inline the conversation as a list of turns.
    interaction_kwargs: Dict[str, Any] = {
        "model": model,
        "system_instruction": system_prompt,
        "generation_config": gen_cfg,
        "stream": True,
    }
    if previous_interaction_id:
        interaction_kwargs["previous_interaction_id"] = previous_interaction_id
        interaction_kwargs["input"] = user_message
    elif conversation_history:
        # Replay history as explicit input list; final turn is the user_message.
        inputs: List[Dict[str, Any]] = []
        for msg in conversation_history:
            inputs.append(
                {
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["text"]}],
                }
            )
        inputs.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": user_message}],
            }
        )
        interaction_kwargs["input"] = inputs
    else:
        interaction_kwargs["input"] = user_message

    try:
        stream = client.interactions.create(**interaction_kwargs)

        accumulated_text = ""
        interaction_id: Optional[str] = None
        usage: Optional[Dict[str, Any]] = None
        last_status: Optional[str] = None

        # The SDK's stream iterator is synchronous (yields from httpx SSE).
        # We iterate it directly — for FastAPI async handlers this is OK for
        # the current load but can be pushed to a thread if needed later.
        for chunk in stream:
            ev = getattr(chunk, "event_type", None)
            if ev == "content.delta":
                delta = getattr(chunk, "delta", None)
                if delta is None:
                    continue
                delta_type = getattr(delta, "type", None)
                if delta_type == "text":
                    accumulated_text += getattr(delta, "text", "")
            elif ev == "interaction.complete":
                final = getattr(chunk, "interaction", None)
                if final is not None:
                    interaction_id = getattr(final, "id", None)
                    usage_obj = getattr(final, "usage", None)
                    if usage_obj is not None:
                        # Convert to plain dict for logging.
                        usage = {
                            "total_tokens": getattr(usage_obj, "total_tokens", None),
                            "total_input_tokens": getattr(usage_obj, "total_input_tokens", None),
                            "total_output_tokens": getattr(usage_obj, "total_output_tokens", None),
                            "total_thought_tokens": getattr(usage_obj, "total_thought_tokens", None),
                        }
                    last_status = getattr(final, "status", None)
            elif ev == "error":
                err = getattr(chunk, "error", None)
                raise GeminiTextV2Error(f"Gemini stream error: {getattr(err, 'message', str(err))}")

        if not accumulated_text:
            raise GeminiTextV2Error(f"Empty response from Gemini. status={last_status} id={interaction_id}")

        return {
            "text": accumulated_text,
            "interaction_id": interaction_id,
            "usage": usage or {},
            "status": last_status,
        }

    except GeminiTextV2Error:
        raise
    except Exception as e:
        logger.exception("Gemini v2 freeform call failed")
        raise GeminiTextV2Error(f"{type(e).__name__}: {e}") from e
