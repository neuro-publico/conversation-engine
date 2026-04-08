"""Response DTOs for the new ads video Director Creative pipeline."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CinematicBeat(BaseModel):
    """One internal shot within a 15s branch (Phase 5.5 multi_prompt).

    Sent to Kling V3 Pro `image-to-video` as one element of the
    `multi_prompt` array. Each beat represents a distinct camera/action/
    lighting moment inside the same continuous clip — Kling handles the
    cuts internally.

    The full set of beats per branch (cinematic_beats_a or cinematic_beats_b)
    must sum to the branch duration (15s for combo, the full duration for
    non-combo). Validated end-to-end against the FAL spec on 2026-04-08.
    """

    prompt: str
    duration: str  # seconds as string, e.g. "5", per FAL enum


class VideoStudioDraftAcceptedResponse(BaseModel):
    """Returned immediately (202) when a draft is accepted for processing.

    The director runs in background. The ecommerce-service polls or waits for
    the callback (`callback_url` if provided in the request) to receive the
    final director_payload.
    """

    reference_id: str
    status: str = "directing"
    message: str = "Director Creative pipeline started."


class VideoStudioDraftReadyPayload(BaseModel):
    """The shape of the structured output the director must return.

    This mirrors the `responseSchema` we send to Gemini. Used for typing on
    the Python side after parsing the LLM response.

    Phase 5.5: cinematic_beats_a/b are the new multi-shot fields. They are
    OPTIONAL at the type level (so old prompts that don't emit them still
    parse), but the responseSchema makes cinematic_beats_a REQUIRED (and
    cinematic_beats_b required only when combo).

    All fields except `script_part_b`, `cinematic_camera_b`, `cinematic_prompt_b`,
    `cinematic_beats_b` are nullable for non-combo videos (5/10/15s single-clip).
    """

    selected_pattern_key: str
    selection_reasoning: str
    concept_visual_brief: str
    script_part_a: str
    script_part_b: Optional[str] = None
    ends_with_product_name: bool
    cinematic_camera_a: str
    cinematic_camera_b: Optional[str] = None
    cinematic_prompt_a: str
    cinematic_prompt_b: Optional[str] = None
    # Phase 5.5: optional multi-beat cinematics. When present, ecommerce
    # renders this branch as N internal beats via Kling V3 Pro multi_prompt.
    # When absent, ecommerce falls back to the legacy single-prompt path
    # with cinematic_prompt_a/b.
    cinematic_beats_a: Optional[List[CinematicBeat]] = None
    cinematic_beats_b: Optional[List[CinematicBeat]] = None
    viral_hook_first_3_seconds: str


class VideoStudioCallbackPayload(BaseModel):
    """Body sent to the `callback_url` when the pipeline finishes (or fails)."""

    status: str  # "success" | "error"
    reference_id: str
    director_payload: Optional[Dict[str, Any]] = None
    selected_pattern_key: Optional[str] = None
    error: Optional[str] = None
    error_step: Optional[str] = None  # "director" | "validation" | "media"
    metadata: Optional[Dict[str, str]] = None
