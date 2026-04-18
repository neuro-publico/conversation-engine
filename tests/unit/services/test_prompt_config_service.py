from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.prompt_config_service import PromptConfigService


@pytest.fixture(autouse=True)
def _isolate_state():
    """Reset cache and fallbacks before/after every test so they don't leak."""
    original_fallbacks = dict(PromptConfigService._fallbacks)
    PromptConfigService.invalidate()
    PromptConfigService._fallbacks.clear()
    yield
    PromptConfigService.invalidate()
    PromptConfigService._fallbacks.clear()
    PromptConfigService._fallbacks.update(original_fallbacks)


class TestRegisterFallback:

    def test_registers_fallback_for_agent_id(self):
        PromptConfigService.register_fallback("demo_agent", "demo content")
        assert PromptConfigService._fallbacks["demo_agent"] == "demo content"


class TestGet:

    async def test_uses_fallback_when_fetch_returns_none(self):
        PromptConfigService.register_fallback("demo_agent", "fallback value")
        with patch(
            "app.services.prompt_config_service.PromptConfigService._fetch",
            new=AsyncMock(return_value=None),
        ):
            result = await PromptConfigService.get("demo_agent")
        assert result == "fallback value"

    async def test_uses_agent_config_value_when_fetch_succeeds(self):
        PromptConfigService.register_fallback("demo_agent", "fallback value")
        with patch(
            "app.services.prompt_config_service.PromptConfigService._fetch",
            new=AsyncMock(return_value="remote content"),
        ):
            result = await PromptConfigService.get("demo_agent")
        assert result == "remote content"

    async def test_caches_value_across_calls(self):
        PromptConfigService.register_fallback("demo_agent", "fallback")
        mock = AsyncMock(return_value="cached content")
        with patch("app.services.prompt_config_service.PromptConfigService._fetch", new=mock):
            first = await PromptConfigService.get("demo_agent")
            second = await PromptConfigService.get("demo_agent")
        assert first == "cached content"
        assert second == "cached content"
        assert mock.await_count == 1

    async def test_invalidate_clears_cache_and_refetches(self):
        PromptConfigService.register_fallback("demo_agent", "fallback")
        mock = AsyncMock(side_effect=["first", "second"])
        with patch("app.services.prompt_config_service.PromptConfigService._fetch", new=mock):
            assert await PromptConfigService.get("demo_agent") == "first"
            PromptConfigService.invalidate("demo_agent")
            assert await PromptConfigService.get("demo_agent") == "second"
        assert mock.await_count == 2

    async def test_invalidate_all_clears_every_agent(self):
        PromptConfigService.register_fallback("a", "x")
        PromptConfigService.register_fallback("b", "y")
        mock = AsyncMock(side_effect=["ra", "rb", "ra2", "rb2"])
        with patch("app.services.prompt_config_service.PromptConfigService._fetch", new=mock):
            await PromptConfigService.get("a")
            await PromptConfigService.get("b")
            PromptConfigService.invalidate()
            await PromptConfigService.get("a")
            await PromptConfigService.get("b")
        assert mock.await_count == 4

    async def test_raises_when_no_fallback_and_fetch_fails(self):
        with patch(
            "app.services.prompt_config_service.PromptConfigService._fetch",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(RuntimeError, match="not available in agent-config"):
                await PromptConfigService.get("missing_agent")


class TestFetch:

    async def test_returns_prompt_from_agent_config_response(self):
        response = MagicMock()
        response.prompt = "system prompt text"
        with patch(
            "app.services.prompt_config_service.get_agent",
            new=AsyncMock(return_value=response),
        ):
            result = await PromptConfigService._fetch("demo_agent")
        assert result == "system prompt text"

    async def test_returns_none_on_http_exception(self):
        with patch(
            "app.services.prompt_config_service.get_agent",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            result = await PromptConfigService._fetch("demo_agent")
        assert result is None

    async def test_returns_none_on_empty_prompt(self):
        response = MagicMock()
        response.prompt = ""
        with patch(
            "app.services.prompt_config_service.get_agent",
            new=AsyncMock(return_value=response),
        ):
            result = await PromptConfigService._fetch("demo_agent")
        assert result is None

    async def test_returns_none_when_prompt_attribute_missing(self):
        # Pydantic models without `prompt` or unexpected type must not crash the caller.
        class Bad:
            pass

        with patch(
            "app.services.prompt_config_service.get_agent",
            new=AsyncMock(return_value=Bad()),
        ):
            result = await PromptConfigService._fetch("demo_agent")
        assert result is None
