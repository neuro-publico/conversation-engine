"""Response DTOs for the new ads video Director Creative pipeline."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


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

    All fields except `script_part_b`, `cinematic_camera_b`, `cinematic_prompt_b`
    are required. Those three are nullable for non-combo videos (5/10/15s).
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
