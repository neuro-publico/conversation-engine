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

    Phase 5.5: cinematic_beats_a/b are the multi-shot fields used by Kling
    V3 Pro `multi_prompt`. OPTIONAL at the type level so non-Kling styles
    (UGC with Seedance) parse without them.

    Phase 6: ugc_avatar_visual_brief, ugc_product_setup_brief,
    ugc_scene_a/b_description, ugc_voice_tone, ugc_voice_pace are the
    UGC-specific fields used by Seedance 2.0 reference-to-video. Also
    OPTIONAL so sassy/animated payloads (which don't emit them) parse
    without them.

    The responseSchema (built dynamically per style_id) enforces the right
    REQUIRED set per style — see `_build_response_schema` in
    `video_studio_service.py`.

    Nullable groups by branch type:
      - non-combo (5/10/15s single-clip): script_part_b, cinematic_camera_b,
        cinematic_prompt_b, cinematic_beats_b, ugc_scene_b_description.
      - non-Kling (UGC, podcast, modeling): cinematic_beats_a/b are not used.
      - non-UGC (sassy, animated): ugc_* fields are not used.
    """

    # ── Common fields (all styles) ──
    selected_pattern_key: str
    selection_reasoning: str
    script_part_a: str
    script_part_b: Optional[str] = None
    ends_with_product_name: bool
    viral_hook_first_3_seconds: str

    # ── Kling-style fields (sassy-object, animated-problem) ──
    # `concept_visual_brief` is the legacy single-image brief that ecommerce
    # wraps with the Pixar character HARD RULES. UGC does NOT use this field
    # — it uses ugc_avatar_visual_brief + ugc_product_setup_brief instead.
    concept_visual_brief: Optional[str] = None
    cinematic_camera_a: Optional[str] = None
    cinematic_camera_b: Optional[str] = None
    cinematic_prompt_a: Optional[str] = None
    cinematic_prompt_b: Optional[str] = None
    # Phase 5.5: optional multi-beat cinematics for Kling V3 Pro multi_prompt.
    # When present, ecommerce renders the branch as N internal beats. When
    # absent, ecommerce falls back to single-prompt cinematic_prompt_a/b.
    # Not emitted by UGC director (Seedance does not support multi_prompt).
    cinematic_beats_a: Optional[List[CinematicBeat]] = None
    cinematic_beats_b: Optional[List[CinematicBeat]] = None

    # ── Phase 6 UGC-style fields (ugc-testimonial via Seedance 2.0) ──
    # These describe the multi-image references (avatar + product + scene)
    # and the TTS voice for the UGC video. ecommerce reads them in
    # handleDraftReady to pre-generate the 3 base images via the existing
    # AIClient.generateImageDirectPrompt pipeline, then in
    # dispatchApprovedDraft to build the Seedance reference-to-video payload.
    #
    # All Optional at the type level. The responseSchema for ugc-testimonial
    # makes the relevant ones REQUIRED at the Gemini-output level.
    ugc_avatar_visual_brief: Optional[str] = None
    ugc_product_setup_brief: Optional[str] = None
    ugc_scene_a_description: Optional[str] = None
    ugc_scene_b_description: Optional[str] = None
    # voice_tone: warm | energetic | calm | excited | professional
    ugc_voice_tone: Optional[str] = None
    # voice_pace: slow | natural | fast
    ugc_voice_pace: Optional[str] = None

    # ── Phase 6 v2 — multi-shot visual briefs ──
    # The director now thinks in 3 distinct compositions instead of 1
    # so Seedance 2.0 has different visual material per fraction. ecommerce
    # generates 3 base images at preview time (portrait + scene_a + scene_b)
    # using image-to-image chaining (portrait acts as the identity anchor
    # for the two scene images, preserving the actor's face).
    #
    # Schema (all Optional at the type level, REQUIRED at gemini schema level
    # for ugc-testimonial — combo requires scene_b_*, non-combo allows null):
    #   - ugc_scene_a_visual_brief: STATIC composition for the Part A image.
    #     "Same person from the avatar brief, in [setting], holding/showing
    #      the product, candid expression, [framing]". Used to generate the
    #      starting frame of the Part A clip.
    #   - ugc_scene_b_visual_brief: STATIC composition for the Part B image.
    #     Can be face-FREE (close-up of hands applying product) when
    #     ugc_scene_b_includes_face is False — saves identity-drift risk
    #     and gives the Part B clip a true demonstration shot.
    #   - ugc_scene_b_includes_face: bool flag. The director decides based
    #     on the script_part_b: if it's a personal statement ("a las 2
    #     semanas yo...") → True. If it's a product callout ("y mirá lo
    #     cremoso") → False, and ecommerce generates Part B without
    #     chaining the portrait (cheaper, no identity-drift risk).
    ugc_scene_a_visual_brief: Optional[str] = None
    ugc_scene_b_visual_brief: Optional[str] = None
    ugc_scene_b_includes_face: Optional[bool] = None


class VideoStudioCallbackPayload(BaseModel):
    """Body sent to the `callback_url` when the pipeline finishes (or fails)."""

    status: str  # "success" | "error"
    reference_id: str
    director_payload: Optional[Dict[str, Any]] = None
    selected_pattern_key: Optional[str] = None
    error: Optional[str] = None
    error_step: Optional[str] = None  # "director" | "validation" | "media"
    metadata: Optional[Dict[str, str]] = None
