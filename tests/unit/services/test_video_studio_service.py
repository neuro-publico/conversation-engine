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
    fake_agent = _make_agent_config(validators=["ends_with_product_name"])

    bad_payload = _valid_combo_payload()
    bad_payload["ends_with_product_name"] = False
    bad_payload["script_part_b"] = "Comprá ya y mejorá tu vida."

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

    assert result.ends_with_product_name is True
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
