"""
Tests for the AI-visibility logging additions in SectionImageService._do_generate:

1. `response_text` (Gemini raw text) is persisted on success, truncated to 10KB.
2. Each failed Gemini attempt emits its own `status=attempt_failed` log with
   error_message, attempt_number and per-attempt elapsed_ms.

Covered scenarios:
- Success on first attempt → 1 log (success) with response_text
- Retry path: fail-then-success → N attempt_failed logs + 1 success
- Full Gemini fail + OpenAI fallback works → 5 attempt_failed + 1 fallback
- Everything fails → 5 attempt_failed + 1 final error (preserved original behavior)
- response_text truncation (>10KB) and None/empty handling
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.requests.section_image_request import SectionImageRequest
from app.services.prompt_config_service import PromptConfigService
from app.services.section_image_service import SectionImageService


@pytest.fixture(autouse=True)
def _clean_prompt_cache():
    PromptConfigService.invalidate()
    yield
    PromptConfigService.invalidate()


@pytest.fixture(autouse=True)
def _force_fallback(monkeypatch):
    """Make PromptConfigService return None so services fall back to hardcoded defaults."""
    monkeypatch.setattr(
        "app.services.prompt_config_service.PromptConfigService._fetch",
        AsyncMock(return_value=None),
    )


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Skip real asyncio.sleep so the 5-retry path runs instantly in tests."""
    monkeypatch.setattr("app.services.section_image_service.asyncio.sleep", AsyncMock())


@pytest.fixture
def service():
    return SectionImageService()


@pytest.fixture
def base_request():
    return SectionImageRequest(
        product_name="Test product",
        product_description="A thing",
        language="es",
        product_image_url="https://example.com/product.jpg",
        template_image_url="https://example.com/tmpl.webp",
        image_format="9:16",
        price=100,
        price_fake=150,
        detect_cta_buttons=True,
        owner_id="owner-xyz",
    )


@pytest.fixture
def mock_log_prompt():
    """Patch log_prompt as AsyncMock — captures every kwargs synchronously on __call__."""
    with patch("app.services.section_image_service.log_prompt", new=AsyncMock()) as m:
        yield m


@pytest.fixture
def mock_upload():
    with patch.object(
        SectionImageService,
        "_compress_and_upload",
        new=AsyncMock(return_value="https://s3/fake.webp"),
    ):
        yield


# ------------------------------------------------------------------------------
# SUCCESS PATH — response_text is persisted
# ------------------------------------------------------------------------------


class TestResponseTextPersisted:
    """Cambio 1: log_prompt debe recibir response_text en el path de éxito."""

    @pytest.mark.asyncio
    async def test_success_first_attempt_logs_response_text(self, service, base_request, mock_log_prompt, mock_upload):
        gemini_text = 'BOTONES:\n- "COMPRAR AHORA" en [915, 200, 965, 800] coords 0-1000'
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(return_value=(b"imgbytes", gemini_text)),
        ):
            resp = await service._do_generate(base_request, time.monotonic())

        assert resp.s3_url == "https://s3/fake.webp"
        # exactly one log: success
        assert mock_log_prompt.call_count == 1
        kwargs = mock_log_prompt.call_args.kwargs
        assert kwargs["status"] == "success"
        assert kwargs["attempt_number"] == 1
        assert kwargs["response_text"] == gemini_text
        assert kwargs["log_type"] == "section_image"

    @pytest.mark.asyncio
    async def test_response_text_truncated_to_10kb(self, service, base_request, mock_log_prompt, mock_upload):
        # 15_000 chars, must be truncated to 10_000
        long_text = "X" * 15_000
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(return_value=(b"imgbytes", long_text)),
        ):
            await service._do_generate(base_request, time.monotonic())
        kwargs = mock_log_prompt.call_args.kwargs
        assert len(kwargs["response_text"]) == 10_000
        assert kwargs["response_text"] == "X" * 10_000

    @pytest.mark.asyncio
    async def test_response_text_none_becomes_empty_string(self, service, base_request, mock_log_prompt, mock_upload):
        # Edge: Gemini returns None as text (shouldn't blow up)
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(return_value=(b"imgbytes", None)),
        ):
            await service._do_generate(base_request, time.monotonic())
        kwargs = mock_log_prompt.call_args.kwargs
        assert kwargs["response_text"] == ""

    @pytest.mark.asyncio
    async def test_response_text_empty_string_passes_through(self, service, base_request, mock_log_prompt, mock_upload):
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(return_value=(b"imgbytes", "")),
        ):
            await service._do_generate(base_request, time.monotonic())
        kwargs = mock_log_prompt.call_args.kwargs
        assert kwargs["response_text"] == ""


# ------------------------------------------------------------------------------
# FAILED ATTEMPTS — each retry loss is logged individually
# ------------------------------------------------------------------------------


class TestAttemptFailedLogging:
    """Cambio 2: cada intento fallido emite su propio log `status=attempt_failed`."""

    @pytest.mark.asyncio
    async def test_retry_path_logs_each_failed_attempt_then_success(
        self, service, base_request, mock_log_prompt, mock_upload
    ):
        # Fail, fail, succeed
        side_effects = [
            Exception("Gemini no image in response. finishReason: STOP, text: BOTONES:"),
            Exception("Gemini empty parts. finishReason: STOP"),
            (b"imgbytes", "BOTONES: ninguno"),
        ]
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(side_effect=side_effects),
        ):
            await service._do_generate(base_request, time.monotonic())

        # 2 attempt_failed + 1 success = 3 total
        assert mock_log_prompt.call_count == 3
        statuses = [c.kwargs["status"] for c in mock_log_prompt.call_args_list]
        assert statuses == ["attempt_failed", "attempt_failed", "success"]

        # attempt_number correct
        attempts = [c.kwargs["attempt_number"] for c in mock_log_prompt.call_args_list]
        assert attempts == [1, 2, 3]

        # error_message captures real exception text
        assert "BOTONES:" in mock_log_prompt.call_args_list[0].kwargs["error_message"]
        assert "empty parts" in mock_log_prompt.call_args_list[1].kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_failed_attempts_have_elapsed_ms_and_provider(
        self, service, base_request, mock_log_prompt, mock_upload
    ):
        side_effects = [
            Exception("boom"),
            (b"imgbytes", ""),
        ]
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(side_effect=side_effects),
        ):
            await service._do_generate(base_request, time.monotonic())

        failed = mock_log_prompt.call_args_list[0].kwargs
        assert failed["status"] == "attempt_failed"
        assert failed["provider"] == "gemini"
        assert failed["model"] == "gemini-3.1-flash-image-preview"
        assert isinstance(failed["elapsed_ms"], int)
        assert failed["elapsed_ms"] >= 0
        # error_message is truncated to 1000
        assert len(failed["error_message"]) <= 1000

    @pytest.mark.asyncio
    async def test_error_message_truncation_cap_1000(self, service, base_request, mock_log_prompt, mock_upload):
        huge = "E" * 5000
        side_effects = [
            Exception(huge),
            (b"imgbytes", ""),
        ]
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(side_effect=side_effects),
        ):
            await service._do_generate(base_request, time.monotonic())
        assert len(mock_log_prompt.call_args_list[0].kwargs["error_message"]) == 1000

    @pytest.mark.asyncio
    async def test_all_gemini_attempts_fail_then_openai_fallback(
        self, service, base_request, mock_log_prompt, mock_upload
    ):
        # 5 Gemini failures, then OpenAI fallback works
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(side_effect=[Exception(f"boom-{i}") for i in range(5)]),
        ):
            with patch(
                "app.services.section_image_service.openai_image_edit",
                new=AsyncMock(return_value=b"openai-img"),
            ):
                resp = await service._do_generate(base_request, time.monotonic())

        assert resp.s3_url == "https://s3/fake.webp"

        # 5 attempt_failed + 1 fallback = 6
        assert mock_log_prompt.call_count == 6
        statuses = [c.kwargs["status"] for c in mock_log_prompt.call_args_list]
        assert statuses == ["attempt_failed"] * 5 + ["fallback"]

        # attempt numbers on the 5 failures are 1..5
        attempts = [c.kwargs["attempt_number"] for c in mock_log_prompt.call_args_list[:5]]
        assert attempts == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_all_gemini_fail_and_fallback_fail_preserves_error_behavior(
        self, service, base_request, mock_log_prompt, mock_upload
    ):
        """Both Gemini and OpenAI die: must still raise last_error AND log final error.
        Preexisting behavior must not regress — the final 'error' log was already there."""
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(side_effect=[Exception(f"boom-{i}") for i in range(5)]),
        ):
            with patch(
                "app.services.section_image_service.openai_image_edit",
                new=AsyncMock(side_effect=Exception("openai also down")),
            ):
                with pytest.raises(Exception, match="boom-4"):
                    await service._do_generate(base_request, time.monotonic())

        # 5 attempt_failed + 1 final error
        assert mock_log_prompt.call_count == 6
        statuses = [c.kwargs["status"] for c in mock_log_prompt.call_args_list]
        assert statuses == ["attempt_failed"] * 5 + ["error"]


# ------------------------------------------------------------------------------
# REGRESSION — fields that were there before must still be there
# ------------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Make sure we did NOT remove any previously-logged field."""

    @pytest.mark.asyncio
    async def test_success_log_still_has_all_prior_fields(self, service, base_request, mock_log_prompt, mock_upload):
        base_request.brand_colors = ["#FF0000", "#00FF00"]
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(return_value=(b"imgbytes", "BOTONES: ninguno")),
        ):
            await service._do_generate(base_request, time.monotonic())

        kwargs = mock_log_prompt.call_args.kwargs
        # fields that existed BEFORE our change — must stay
        assert kwargs["log_type"] == "section_image"
        assert kwargs["prompt"]  # non-empty
        assert kwargs["response_url"] == "https://s3/fake.webp"
        assert kwargs["owner_id"] == "owner-xyz"
        assert kwargs["model"] == "gemini-3.1-flash-image-preview"
        assert kwargs["provider"] == "gemini"
        assert kwargs["brand_colors"] == ["#FF0000", "#00FF00"]
        assert kwargs["status"] == "success"
        assert kwargs["attempt_number"] == 1
        assert isinstance(kwargs["elapsed_ms"], int)
        assert kwargs["metadata"] == {"cta_buttons": 0, "image_format": "9:16"}

    @pytest.mark.asyncio
    async def test_fallback_log_unchanged(self, service, base_request, mock_log_prompt, mock_upload):
        """The fallback path log signature wasn't touched. Must still carry the same keys."""
        with patch(
            "app.services.section_image_service.google_image_with_text",
            new=AsyncMock(side_effect=[Exception("x")] * 5),
        ):
            with patch(
                "app.services.section_image_service.openai_image_edit",
                new=AsyncMock(return_value=b"openai-img"),
            ):
                await service._do_generate(base_request, time.monotonic())

        fallback_call = mock_log_prompt.call_args_list[-1]
        k = fallback_call.kwargs
        assert k["status"] == "fallback"
        assert k["fallback_used"] is True
        assert k["model"] == "gpt-image-1"
        assert k["provider"] == "openai"
        assert k["response_url"] == "https://s3/fake.webp"
