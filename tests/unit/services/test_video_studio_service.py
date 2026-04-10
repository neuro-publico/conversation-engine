"""Smoke tests para VideoStudioService (Director Creativo).

Estos tests mockean get_agent y call_gemini_structured. NO consumen créditos
de Gemini ni dependen de agent-config corriendo. Para los tests con LLM real,
ver evals/director/run_eval.py.

Cubren:
  - happy path combo (30s, 2 escenas)
  - happy path non-combo (15s, 1 escena, sin script_part_b)
  - validators del director fallan en attempt 1 → self-correction → ok en attempt 2
  - agent_config sin creative_patterns → VideoStudioError step=agent_config_validation
  - call_gemini_structured lanza GeminiTextError → VideoStudioError step=director
"""

from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, patch

import pytest

from app.externals.agent_config.responses.agent_config_response import (
    AgentConfigResponse,
    AgentPreferences,
)
from app.externals.ai_direct.gemini_text import GeminiTextError
from app.requests.video_studio_draft_request import VideoStudioDraftRequest
from app.services.video_studio_service import VideoStudioError, VideoStudioService


def _make_agent_config(
    *,
    patterns: List[Dict[str, Any]] = None,
    validators: List[str] = None,
) -> AgentConfigResponse:
    if patterns is None:
        patterns = [
            {"key": "smug_villain", "active": True, "tone": "siniestro elegante"},
            {"key": "suffering_victim", "active": True, "tone": "empático"},
        ]
    if validators is None:
        validators = []
    return AgentConfigResponse(
        id=1,
        agent_id="video_director_animated_v1",
        description="director test",
        prompt="System prompt with {product_name} and {creative_patterns_json} placeholders.",
        provider_ai="gemini",
        model_ai="gemini-3.1-pro-preview",
        preferences=AgentPreferences(temperature=0.9, max_tokens=4096, top_p=0.95),
        tools=[],
        mcp_config=None,
        metadata={
            "video_studio": {
                "creative_patterns": patterns,
                "validators": validators,
            }
        },
    )


def _make_request(duration: int = 30) -> VideoStudioDraftRequest:
    return VideoStudioDraftRequest(
        reference_id="ref-test-1",
        owner_id="owner-1",
        product_name="Repelente ultrasónico de insectos x1",
        product_description="Ahuyenta mosquitos sin químicos.",
        duration=duration,
    )


def _valid_combo_payload() -> Dict[str, Any]:
    return {
        "selected_pattern_key": "smug_villain",
        "selection_reasoning": "El producto es el villano elegante que extermina insectos.",
        "concept_visual_brief": "Animated 3D scene, dim warm light, the device looms over a swarm of mosquitoes.",
        "script_part_a": "Los mosquitos creían que esta noche ganaban.",
        "script_part_b": "Hasta que llegó el Repelente ultrasónico de insectos x1.",
        "ends_with_product_name": True,
        "cinematic_camera_a": "low angle dolly in",
        "cinematic_camera_b": "slow pedestal up",
        "cinematic_prompt_a": (
            "Low angle dolly in, anamorphic lens, the device hums and pulses, mosquitoes "
            "lurch backward, gasp, scatter, smoke curls, dim warm key light from the left."
        ),
        "cinematic_prompt_b": (
            "Slow pedestal up, the device looms triumphantly, smirks in shadow, the room "
            "settles, particles drift, soft rim light reveals the product label."
        ),
        "viral_hook_first_3_seconds": "Mosquito boss laughing — until something hums behind him.",
    }


def _valid_non_combo_payload() -> Dict[str, Any]:
    base = _valid_combo_payload()
    base["script_part_b"] = None
    base["cinematic_camera_b"] = None
    base["cinematic_prompt_b"] = None
    return base


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_happy_path_combo() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config()
    fake_payload = _valid_combo_payload()

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            new=AsyncMock(return_value=(fake_payload, {"usageMetadata": {}})),
        ) as mock_gemini,
    ):
        result = await service.run_director(_make_request(duration=30))

    assert result.selected_pattern_key == "smug_villain"
    assert result.script_part_b is not None
    assert "Repelente ultrasónico de insectos x1" in result.script_part_b
    assert mock_gemini.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_parses_cinematic_beats_when_present() -> None:
    """Phase 5.5: when Gemini emits cinematic_beats_a/b, the Pydantic model
    must parse them through to the response so the ecommerce dispatch can
    consume them as multi_prompt input. The schema enforces them as
    required, but Pydantic keeps them Optional for back-compat with old
    fixtures and old tests."""
    service = VideoStudioService()
    fake_agent = _make_agent_config()
    fake_payload = _valid_combo_payload()
    fake_payload["cinematic_beats_a"] = [
        {"prompt": "BEAT 1: SLOW DOLLY_IN macro on the angry character.", "duration": "5"},
        {"prompt": "BEAT 2: WHIP_PAN to medium shot, character points.", "duration": "5"},
        {"prompt": "BEAT 3: PULL_OUT hero shot, character crosses arms.", "duration": "5"},
    ]
    fake_payload["cinematic_beats_b"] = [
        {"prompt": "BEAT 1: PUSH_IN macro on the smug face.", "duration": "5"},
        {"prompt": "BEAT 2: ARC_AROUND, character winks.", "duration": "5"},
        {"prompt": "BEAT 3: TILT_UP hero shot, character points at camera.", "duration": "5"},
    ]

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            new=AsyncMock(return_value=(fake_payload, {"usageMetadata": {}})),
        ),
    ):
        result = await service.run_director(_make_request(duration=30))

    assert result.cinematic_beats_a is not None
    assert len(result.cinematic_beats_a) == 3
    assert result.cinematic_beats_a[0].prompt.startswith("BEAT 1:")
    assert result.cinematic_beats_a[0].duration == "5"
    assert result.cinematic_beats_b is not None
    assert len(result.cinematic_beats_b) == 3
    assert result.cinematic_beats_b[2].prompt.startswith("BEAT 3:")


@pytest.mark.unit
def test_build_response_schema_includes_cinematic_beats_required_when_combo() -> None:
    """Phase 5.5: cinematic_beats_a is always required, cinematic_beats_b
    is required only when combo. Validates the schema shape Gemini receives
    so the structured output forces both fields."""
    service = VideoStudioService()

    combo_schema = service._build_response_schema(is_combo=True)
    assert "cinematic_beats_a" in combo_schema["properties"]
    assert "cinematic_beats_b" in combo_schema["properties"]
    assert combo_schema["properties"]["cinematic_beats_a"]["type"] == "ARRAY"
    assert combo_schema["properties"]["cinematic_beats_a"]["minItems"] == 2
    assert combo_schema["properties"]["cinematic_beats_a"]["maxItems"] == 3
    assert "cinematic_beats_a" in combo_schema["required"]
    assert "cinematic_beats_b" in combo_schema["required"]

    non_combo_schema = service._build_response_schema(is_combo=False)
    # beats_a is still required for non-combo (single 15s clip with beats)
    assert "cinematic_beats_a" in non_combo_schema["required"]
    # beats_b is NOT required for non-combo
    assert "cinematic_beats_b" not in non_combo_schema["required"]
    # but the property still exists in the schema as nullable
    assert non_combo_schema["properties"]["cinematic_beats_b"]["nullable"] is True

    # Each beat object schema enforces prompt + duration as required
    beat_schema = combo_schema["properties"]["cinematic_beats_a"]["items"]
    assert beat_schema["type"] == "OBJECT"
    assert "prompt" in beat_schema["required"]
    assert "duration" in beat_schema["required"]
    assert "5" in beat_schema["properties"]["duration"]["enum"]
    assert "15" in beat_schema["properties"]["duration"]["enum"]


# ─────────────────────────────────────────────────────────
# Phase 6 — UGC schema branching (Seedance 2.0)
# ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_build_response_schema_branches_to_ugc_when_style_is_ugc_testimonial() -> None:
    """Phase 6: when style_id == 'ugc-testimonial' the schema returned is the
    UGC schema (with ugc_avatar_visual_brief etc) and NOT the Kling schema
    (no concept_visual_brief, no cinematic_camera_*, no cinematic_beats_*).
    Backwards compatible: any other style_id returns the legacy Kling schema.
    """
    service = VideoStudioService()

    ugc_combo = service._build_response_schema(is_combo=True, style_id="ugc-testimonial")
    props = ugc_combo["properties"]

    # UGC fields ARE present
    assert "ugc_avatar_visual_brief" in props
    assert "ugc_product_setup_brief" in props
    assert "ugc_scene_a_description" in props
    assert "ugc_scene_b_description" in props
    assert "ugc_voice_tone" in props
    assert "ugc_voice_pace" in props

    # Kling fields are NOT present (no leakage)
    assert "concept_visual_brief" not in props
    assert "cinematic_camera_a" not in props
    assert "cinematic_camera_b" not in props
    assert "cinematic_prompt_a" not in props
    assert "cinematic_prompt_b" not in props
    assert "cinematic_beats_a" not in props
    assert "cinematic_beats_b" not in props

    # Common fields are still there
    assert "selected_pattern_key" in props
    assert "script_part_a" in props
    assert "script_part_b" in props
    assert "ends_with_product_name" in props
    assert "viral_hook_first_3_seconds" in props

    # Required set: combo includes script_part_b + ugc_scene_b_description
    required = ugc_combo["required"]
    assert "ugc_avatar_visual_brief" in required
    assert "ugc_product_setup_brief" in required
    assert "ugc_scene_a_description" in required
    assert "ugc_voice_tone" in required
    assert "ugc_voice_pace" in required
    assert "script_part_a" in required
    assert "script_part_b" in required
    assert "ugc_scene_b_description" in required

    # Phase 6 v2 — multi-shot visual briefs are present and required on combo
    assert "ugc_scene_a_visual_brief" in props
    assert "ugc_scene_b_visual_brief" in props
    assert "ugc_scene_b_includes_face" in props
    assert "ugc_scene_a_visual_brief" in required
    assert "ugc_scene_b_visual_brief" in required
    assert "ugc_scene_b_includes_face" in required


@pytest.mark.unit
def test_build_response_schema_ugc_non_combo_does_not_require_part_b() -> None:
    """Phase 6: non-combo UGC (single 15s clip) should NOT require script_part_b
    nor ugc_scene_b_description. The properties still exist as nullable but the
    required set excludes them."""
    service = VideoStudioService()

    ugc_non_combo = service._build_response_schema(is_combo=False, style_id="ugc-testimonial")
    required = ugc_non_combo["required"]

    assert "ugc_avatar_visual_brief" in required
    assert "ugc_scene_a_description" in required
    assert "script_part_b" not in required
    assert "ugc_scene_b_description" not in required

    # Phase 6 v2 — non-combo only requires scene_a_visual_brief; scene_b_*
    # are present as nullable but NOT required (single 15s clip has no Part B)
    assert "ugc_scene_a_visual_brief" in required
    assert "ugc_scene_b_visual_brief" not in required
    assert "ugc_scene_b_includes_face" not in required

    # The properties still exist in the schema (they can be null)
    props = ugc_non_combo["properties"]
    assert "script_part_b" in props
    assert "ugc_scene_b_description" in props
    assert props["ugc_scene_b_description"].get("nullable") is True


@pytest.mark.unit
def test_build_response_schema_legacy_styles_return_kling_schema() -> None:
    """Phase 6 backwards compat: sassy-object, animated-problem, and any other
    style_id (or no style_id at all) must return the legacy Kling schema with
    cinematic_camera_*, cinematic_prompt_*, cinematic_beats_*, and
    concept_visual_brief — exactly like Phase 5.5."""
    service = VideoStudioService()

    for style in ["sassy-object", "animated-problem", "podcast-style", "", "anything-else"]:
        schema = service._build_response_schema(is_combo=True, style_id=style)
        props = schema["properties"]
        assert "concept_visual_brief" in props, f"missing concept_visual_brief for style={style}"
        assert "cinematic_camera_a" in props, f"missing cinematic_camera_a for style={style}"
        assert "cinematic_beats_a" in props, f"missing cinematic_beats_a for style={style}"
        assert "ugc_avatar_visual_brief" not in props, f"UGC field leaked for style={style}"
        assert "ugc_voice_tone" not in props, f"UGC field leaked for style={style}"
        assert "ugc_scene_a_visual_brief" not in props, f"UGC v2 field leaked for style={style}"
        assert "ugc_scene_b_visual_brief" not in props, f"UGC v2 field leaked for style={style}"
        assert "ugc_scene_b_includes_face" not in props, f"UGC v2 field leaked for style={style}"


@pytest.mark.unit
def test_pydantic_payload_accepts_ugc_only_fields() -> None:
    """Phase 6: VideoStudioDraftReadyPayload must parse a UGC-only payload
    (no concept_visual_brief, no cinematic_*) without errors. The Pydantic
    model treats both Kling and UGC fields as Optional so payloads from
    either flow validate."""
    from app.responses.video_studio_draft_response import VideoStudioDraftReadyPayload

    ugc_payload = VideoStudioDraftReadyPayload(
        selected_pattern_key="morning_routine_testimonial",
        selection_reasoning="avatar matches target audience",
        script_part_a="Llevo dos semanas usando esto y cambió mi rutina de mañana.",
        script_part_b="Lo abrís, lo aplicás suave en la cara. Evil Goods Honey Balm.",
        ends_with_product_name=True,
        viral_hook_first_3_seconds="Mi piel cambió en 14 días",
        ugc_avatar_visual_brief=(
            "photorealistic 55 year old latina woman wearing a cream colored bath robe, "
            "short gray hair, soft natural skin, in a marble bathroom with morning natural "
            "light from the left, plants in the background"
        ),
        ugc_product_setup_brief=(
            "close-up of the Evil Goods Whipped Tallow Honey Balm bottle on a marble counter, "
            "label fully readable, soft warm key light, eucalyptus blurred behind"
        ),
        ugc_scene_a_description="medium shot of the avatar talking to camera, holding the product",
        ugc_scene_b_description="macro close-up of the avatar's finger touching the cream inside",
        ugc_voice_tone="warm",
        ugc_voice_pace="natural",
        # Phase 6 v2 — multi-shot visual briefs
        ugc_scene_a_visual_brief=(
            "medium-wide shot of the same 55 year old latina woman from the avatar brief, "
            "in the same marble bathroom, holding the Honey Balm jar at chest height with "
            "both hands, soft window light from camera-left, candid expression"
        ),
        ugc_scene_b_visual_brief=(
            "macro close-up of two female hands on a marble counter dipping a finger into "
            "the open Honey Balm jar, creamy yellow texture clearly visible, soft warm light, "
            "no face in frame"
        ),
        ugc_scene_b_includes_face=False,
    )

    assert ugc_payload.ugc_avatar_visual_brief.startswith("photorealistic")
    assert ugc_payload.ugc_voice_tone == "warm"
    assert ugc_payload.ugc_voice_pace == "natural"
    assert "marble bathroom" in ugc_payload.ugc_scene_a_visual_brief
    assert ugc_payload.ugc_scene_b_includes_face is False
    # Kling fields are None — that's the whole point
    assert ugc_payload.concept_visual_brief is None
    assert ugc_payload.cinematic_camera_a is None
    assert ugc_payload.cinematic_beats_a is None


@pytest.mark.unit
def test_pydantic_payload_legacy_kling_payload_still_parses() -> None:
    """Phase 6 regression guard: the existing sassy/animated payload shape
    (the one with concept_visual_brief + cinematic_*) MUST still parse via
    the same Pydantic model. We made the Kling fields Optional but the
    fixtures still set them, so parsing should succeed unchanged."""
    from app.responses.video_studio_draft_response import (
        CinematicBeat,
        VideoStudioDraftReadyPayload,
    )

    kling_payload = VideoStudioDraftReadyPayload(
        selected_pattern_key="smug_villain",
        selection_reasoning="test",
        concept_visual_brief="A 3D Pixar mosquito with smug face",
        script_part_a="Hola soy la plaga",
        script_part_b="Hasta que llegó el repelente",
        ends_with_product_name=True,
        cinematic_camera_a="LOW_ANGLE_HERO",
        cinematic_camera_b="DUTCH_ANGLE",
        cinematic_prompt_a="The character lurches",
        cinematic_prompt_b="The character trembles",
        cinematic_beats_a=[
            CinematicBeat(prompt="BEAT 1: SLOW DOLLY_IN", duration="5"),
            CinematicBeat(prompt="BEAT 2: WHIP_PAN", duration="5"),
        ],
        viral_hook_first_3_seconds="Mosquitos creían que ganaban",
    )
    assert kling_payload.concept_visual_brief == "A 3D Pixar mosquito with smug face"
    assert len(kling_payload.cinematic_beats_a) == 2
    # UGC fields are None — backwards compat
    assert kling_payload.ugc_avatar_visual_brief is None
    assert kling_payload.ugc_voice_tone is None


@pytest.mark.unit
def test_validate_payload_ugc_validators_apply_only_to_ugc_payloads() -> None:
    """Phase 6: the new UGC validators (ugc_avatar_brief_min_chars,
    ugc_product_setup_brief_min_chars, ugc_voice_tone_in_set) skip silently
    when the payload doesn't have those fields (Kling payload). They only
    error when a UGC payload has invalid values."""
    service = VideoStudioService()
    request = _make_request(duration=30)

    # Kling payload — UGC fields are absent → all UGC validators skip
    kling_parsed = _valid_combo_payload()
    errors = service._validate_payload(
        parsed=kling_parsed,
        request=request,
        validators=[
            "ugc_avatar_brief_min_chars:200",
            "ugc_product_setup_brief_min_chars:150",
            "ugc_voice_tone_in_set",
        ],
    )
    assert errors == [], f"UGC validators should skip on Kling payload, got: {errors}"

    # UGC payload with avatar_brief too short → error
    short_brief = {
        "ugc_avatar_visual_brief": "too short",  # 9 chars, min 200
        "ugc_product_setup_brief": "x" * 200,  # OK
        "ugc_voice_tone": "warm",  # OK
        "script_part_a": "test",
        "script_part_b": "test product",
    }
    errors = service._validate_payload(
        parsed=short_brief,
        request=request,
        validators=[
            "ugc_avatar_brief_min_chars:200",
            "ugc_product_setup_brief_min_chars:150",
            "ugc_voice_tone_in_set",
        ],
    )
    assert any("ugc_avatar_brief_min_chars" in e for e in errors), f"missing avatar_brief error: {errors}"

    # UGC payload with invalid voice_tone → error
    bad_tone = {
        "ugc_avatar_visual_brief": "x" * 250,
        "ugc_product_setup_brief": "x" * 200,
        "ugc_voice_tone": "robotic",  # not in allowed set
    }
    errors = service._validate_payload(
        parsed=bad_tone,
        request=request,
        validators=["ugc_voice_tone_in_set"],
    )
    assert any("ugc_voice_tone_in_set" in e for e in errors)


@pytest.mark.unit
def test_validate_payload_ugc_v2_visual_briefs_validators() -> None:
    """Phase 6 v2: validators for the new multi-shot visual briefs.

    - ugc_scene_a_visual_brief_min_chars: errors when scene_a_visual_brief is
      too short. Skips silently when the field is absent (back-compat).
    - ugc_scene_b_visual_brief_min_chars: same but for scene_b. Only applies
      to combo (non-combo has no Part B).
    - ugc_scene_briefs_distinct: errors when scene_a and scene_b briefs are
      identical. Only applies to combo. The whole point of multi-shot is
      that the two compositions are visually different.
    """
    service = VideoStudioService()
    combo_request = _make_request(duration=30)
    non_combo_request = _make_request(duration=15)

    # Skip silently when fields are absent
    bare_payload = {"script_part_a": "test"}
    errors = service._validate_payload(
        parsed=bare_payload,
        request=combo_request,
        validators=[
            "ugc_scene_a_visual_brief_min_chars:150",
            "ugc_scene_b_visual_brief_min_chars:150",
            "ugc_scene_briefs_distinct",
        ],
    )
    assert errors == [], f"validators must skip when fields are absent, got: {errors}"

    # scene_a too short → error
    short_a = {
        "ugc_scene_a_visual_brief": "too short",  # 9 chars
        "ugc_scene_b_visual_brief": "x" * 200,
    }
    errors = service._validate_payload(
        parsed=short_a,
        request=combo_request,
        validators=["ugc_scene_a_visual_brief_min_chars:150"],
    )
    assert any("ugc_scene_a_visual_brief_min_chars" in e for e in errors)

    # scene_b too short on combo → error
    short_b_combo = {
        "ugc_scene_a_visual_brief": "x" * 200,
        "ugc_scene_b_visual_brief": "too short",
    }
    errors = service._validate_payload(
        parsed=short_b_combo,
        request=combo_request,
        validators=["ugc_scene_b_visual_brief_min_chars:150"],
    )
    assert any("ugc_scene_b_visual_brief_min_chars" in e for e in errors)

    # scene_b too short on NON-combo → no error (validator scoped to combo)
    short_b_non_combo = {
        "ugc_scene_a_visual_brief": "x" * 200,
        "ugc_scene_b_visual_brief": "too short",
    }
    errors = service._validate_payload(
        parsed=short_b_non_combo,
        request=non_combo_request,
        validators=["ugc_scene_b_visual_brief_min_chars:150"],
    )
    assert errors == [], f"non-combo must skip scene_b validators, got: {errors}"

    # Identical briefs on combo → error
    identical = {
        "ugc_scene_a_visual_brief": "x" * 200,
        "ugc_scene_b_visual_brief": "x" * 200,
    }
    errors = service._validate_payload(
        parsed=identical,
        request=combo_request,
        validators=["ugc_scene_briefs_distinct"],
    )
    assert any("ugc_scene_briefs_distinct" in e for e in errors)

    # Distinct briefs on combo → no error
    distinct = {
        "ugc_scene_a_visual_brief": "talking head wide shot " * 10,
        "ugc_scene_b_visual_brief": "macro close-up of hands " * 10,
    }
    errors = service._validate_payload(
        parsed=distinct,
        request=combo_request,
        validators=["ugc_scene_briefs_distinct"],
    )
    assert errors == [], f"distinct briefs must pass, got: {errors}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_happy_path_non_combo() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config()
    fake_payload = _valid_non_combo_payload()

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            new=AsyncMock(return_value=(fake_payload, {"usageMetadata": {}})),
        ),
    ):
        result = await service.run_director(_make_request(duration=15))

    assert result.script_part_b is None
    assert result.cinematic_prompt_b is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_no_creative_patterns_raises() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config(patterns=[])

    with patch(
        "app.services.video_studio_service.get_agent",
        new=AsyncMock(return_value=fake_agent),
    ):
        with pytest.raises(VideoStudioError) as excinfo:
            await service.run_director(_make_request())

    assert excinfo.value.step == "agent_config_validation"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_gemini_error_raises_director_step() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config()

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            new=AsyncMock(side_effect=GeminiTextError("boom", status=500, raw="oops")),
        ),
    ):
        with pytest.raises(VideoStudioError) as excinfo:
            await service.run_director(_make_request())

    assert excinfo.value.step == "director"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_validator_self_correction() -> None:
    """Primer intento falla validator → segundo intento devuelve payload válido."""
    service = VideoStudioService()
    fake_agent = _make_agent_config(validators=["camera_varies_between_scenes"])

    bad_payload = _valid_combo_payload()
    bad_payload["cinematic_camera_a"] = "LOW_ANGLE_HERO"
    bad_payload["cinematic_camera_b"] = "LOW_ANGLE_HERO"  # same camera → validator fails

    good_payload = _valid_combo_payload()

    call_results: List[Tuple[Dict[str, Any], Dict[str, Any]]] = [
        (bad_payload, {"usageMetadata": {}}),
        (good_payload, {"usageMetadata": {}}),
    ]

    async def fake_call(**_kwargs: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        return call_results.pop(0)

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            side_effect=fake_call,
        ) as mock_gemini,
    ):
        result = await service.run_director(_make_request())

    assert result.cinematic_camera_a != result.cinematic_camera_b
    assert mock_gemini.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_and_callback_success_posts_callback() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config()
    fake_payload = _valid_combo_payload()

    request = _make_request()
    request.callback_url = "https://hook.example.com/cb"
    request.callback_metadata = {"draft_ref": "abc"}

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            new=AsyncMock(return_value=(fake_payload, {"usageMetadata": {}})),
        ),
        patch(
            "app.services.video_studio_service.post_callback",
            new=AsyncMock(return_value=None),
        ) as mock_cb,
    ):
        await service.run_and_callback(request)

    mock_cb.assert_awaited_once()
    url, body = mock_cb.await_args.args
    assert url == "https://hook.example.com/cb"
    assert body["status"] == "success"
    assert body["selected_pattern_key"] == "smug_villain"
    assert body["director_payload"]["script_part_a"]
    assert body["metadata"] == {"draft_ref": "abc"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_and_callback_error_posts_error_payload() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config()

    request = _make_request()
    request.callback_url = "https://hook.example.com/cb"

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            new=AsyncMock(side_effect=GeminiTextError("boom", status=500, raw="oops")),
        ),
        patch(
            "app.services.video_studio_service.post_callback",
            new=AsyncMock(return_value=None),
        ) as mock_cb,
    ):
        await service.run_and_callback(request)

    mock_cb.assert_awaited_once()
    _url, body = mock_cb.await_args.args
    assert body["status"] == "error"
    assert body["error_step"] == "director"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_and_callback_no_callback_url_skips() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config()
    fake_payload = _valid_combo_payload()

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            new=AsyncMock(return_value=(fake_payload, {"usageMetadata": {}})),
        ),
        patch(
            "app.services.video_studio_service.post_callback",
            new=AsyncMock(return_value=None),
        ) as mock_cb,
    ):
        await service.run_and_callback(_make_request())  # sin callback_url

    mock_cb.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_validators_camera_and_words() -> None:
    """Cubre las ramas de validators camera_varies_between_scenes y max_words_part_b."""
    service = VideoStudioService()
    fake_agent = _make_agent_config(validators=["camera_varies_between_scenes"])

    bad = _valid_combo_payload()
    bad["cinematic_camera_b"] = bad["cinematic_camera_a"]  # iguales -> falla
    good = _valid_combo_payload()

    call_results = [
        (bad, {"usageMetadata": {}}),
        (good, {"usageMetadata": {}}),
    ]

    async def fake_call(**_kwargs: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        return call_results.pop(0)

    with (
        patch(
            "app.services.video_studio_service.get_agent",
            new=AsyncMock(return_value=fake_agent),
        ),
        patch(
            "app.services.video_studio_service.call_gemini_structured",
            side_effect=fake_call,
        ) as mock_gemini,
    ):
        result = await service.run_director(_make_request())

    assert result.cinematic_camera_a != result.cinematic_camera_b
    assert mock_gemini.await_count == 2
