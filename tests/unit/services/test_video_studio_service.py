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
    validators: List[Dict[str, Any]] = None,
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

    with patch(
        "app.services.video_studio_service.get_agent",
        new=AsyncMock(return_value=fake_agent),
    ), patch(
        "app.services.video_studio_service.call_gemini_structured",
        new=AsyncMock(return_value=(fake_payload, {"usageMetadata": {}})),
    ) as mock_gemini:
        result = await service.run_director(_make_request(duration=30))

    assert result.selected_pattern_key == "smug_villain"
    assert result.script_part_b is not None
    assert "Repelente ultrasónico de insectos x1" in result.script_part_b
    assert mock_gemini.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_happy_path_non_combo() -> None:
    service = VideoStudioService()
    fake_agent = _make_agent_config()
    fake_payload = _valid_non_combo_payload()

    with patch(
        "app.services.video_studio_service.get_agent",
        new=AsyncMock(return_value=fake_agent),
    ), patch(
        "app.services.video_studio_service.call_gemini_structured",
        new=AsyncMock(return_value=(fake_payload, {"usageMetadata": {}})),
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

    with patch(
        "app.services.video_studio_service.get_agent",
        new=AsyncMock(return_value=fake_agent),
    ), patch(
        "app.services.video_studio_service.call_gemini_structured",
        new=AsyncMock(side_effect=GeminiTextError("boom", status=500, raw="oops")),
    ):
        with pytest.raises(VideoStudioError) as excinfo:
            await service.run_director(_make_request())

    assert excinfo.value.step == "director"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_director_validator_self_correction() -> None:
    """Primer intento falla validator → segundo intento devuelve payload válido."""
    service = VideoStudioService()
    fake_agent = _make_agent_config(
        validators=[{"name": "ends_with_product_name"}],
    )

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

    with patch(
        "app.services.video_studio_service.get_agent",
        new=AsyncMock(return_value=fake_agent),
    ), patch(
        "app.services.video_studio_service.call_gemini_structured",
        side_effect=fake_call,
    ) as mock_gemini:
        result = await service.run_director(_make_request())

    assert result.ends_with_product_name is True
    assert mock_gemini.await_count == 2
