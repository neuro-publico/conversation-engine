"""Direct Gemini text caller for the new ads video flow.

This module bypasses LangChain entirely and calls the Gemini REST API directly.
Why: LangChain wrappers (`ChatGoogleGenerativeAI`) do not expose the features we
need: native structured output via `responseSchema`, `thinkingConfig`,
`responseMimeType="application/json"`. Going direct lets us use them.

It follows the same session/retry patterns as `app/externals/images/image_client.py`
(which is the proven blueprint for direct provider calls in this repo).

Designed to be provider-agnostic at the call site: the caller passes provider name
(`gemini` here) and the function picks the right adapter. Future providers can be
added in this module (`anthropic_text.py`, `openai_text.py`) with the same shape.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Tuple

import aiohttp

from app.configurations.config import GOOGLE_GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Shared session for Gemini API calls (reuses TCP connections, mismo patrón
# que image_client._gemini_session).
_gemini_text_session: Optional[aiohttp.ClientSession] = None


async def _get_session() -> aiohttp.ClientSession:
    global _gemini_text_session
    if _gemini_text_session is None or _gemini_text_session.closed:
        _gemini_text_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=600),
            connector=aiohttp.TCPConnector(limit=10),
        )
    return _gemini_text_session


async def close_session() -> None:
    """Cierra la sesión compartida. Útil para scripts standalone (en el server
    FastAPI no hace falta porque la sesión persiste durante toda la vida del
    proceso). En producción se puede llamar desde un shutdown handler si se
    quiere ser estricto con el cleanup."""
    global _gemini_text_session
    if _gemini_text_session is not None and not _gemini_text_session.closed:
        await _gemini_text_session.close()
        _gemini_text_session = None


class GeminiTextError(Exception):
    """Raised when Gemini text generation fails after all retries."""

    def __init__(self, message: str, status: Optional[int] = None, raw: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.raw = raw


async def call_gemini_structured(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    response_schema: Dict[str, Any],
    temperature: float = 0.9,
    top_p: float = 0.95,
    max_output_tokens: int = 32768,
    thinking_level: Optional[str] = "High",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Call Gemini and force a JSON response that matches `response_schema`.

    Args:
        model: Gemini model id, e.g. "gemini-3.1-pro-preview" or "gemini-3-pro".
        system_prompt: The system instruction (already templated, no placeholders).
        user_message: The user message (kept short — most of the context goes in
            system_prompt).
        response_schema: JSON Schema dict the response must match. Gemini enforces
            the structure server-side with `responseSchema`.
        temperature: Sampling temperature.
        top_p: Nucleus sampling.
        max_output_tokens: Hard cap on output length.
        thinking_level: One of "Low" | "Medium" | "High" or None to disable. Only
            applies to flash/preview models that support `thinkingConfig`.

    Returns:
        A tuple `(parsed_json, raw_response)`. `parsed_json` is the JSON dict that
        Gemini returned (already validated against `response_schema`).
        `raw_response` is the full HTTP response body for auditing in `prompt_logs`.

    Raises:
        GeminiTextError: if all retries fail or the response cannot be parsed.
    """
    if not GOOGLE_GEMINI_API_KEY:
        raise GeminiTextError("GOOGLE_GEMINI_API_KEY is not set in env")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={GOOGLE_GEMINI_API_KEY}"
    )

    generation_config: Dict[str, Any] = {
        "temperature": temperature,
        "topP": top_p,
        "maxOutputTokens": max_output_tokens,
        "responseMimeType": "application/json",
        "responseSchema": response_schema,
    }

    if thinking_level and ("flash" in model.lower() or "preview" in model.lower()):
        # `thinkingConfig` solo lo soportan los modelos preview/flash. Para
        # modelos pro estables se ignora.
        generation_config["thinkingConfig"] = {"thinkingLevel": thinking_level}

    payload: Dict[str, Any] = {
        "systemInstruction": {"role": "system", "parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": generation_config,
    }

    headers = {"Content-Type": "application/json"}

    # Retry policy: 3 attempts, jitter exponencial corto (300ms, 900ms, 2.7s).
    # Mucho más eficiente que los 5 intentos × 5s del image_client viejo, que
    # rescataban menos del 5% según la telemetría real (prompt_logs).
    max_attempts = 3
    last_error: Optional[Exception] = None
    last_status: Optional[int] = None
    last_body: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                delay = 0.3 * (3 ** (attempt - 2))
                await asyncio.sleep(delay)

            session = await _get_session()
            async with session.post(url, headers=headers, json=payload) as response:
                last_status = response.status
                body_text = await response.text()
                last_body = body_text

                if response.status == 429:
                    raise GeminiTextError(
                        f"Gemini rate limit (429): {body_text[:300]}",
                        status=429,
                        raw=body_text,
                    )

                if response.status != 200:
                    raise GeminiTextError(
                        f"Gemini HTTP {response.status}: {body_text[:300]}",
                        status=response.status,
                        raw=body_text,
                    )

                try:
                    data = json.loads(body_text)
                except json.JSONDecodeError as je:
                    raise GeminiTextError(
                        f"Gemini response not JSON: {body_text[:300]}",
                        raw=body_text,
                    ) from je

                candidates = data.get("candidates", [])
                if not candidates:
                    prompt_feedback = data.get("promptFeedback", {})
                    raise GeminiTextError(
                        f"Gemini returned no candidates. promptFeedback={prompt_feedback}",
                        raw=body_text,
                    )

                candidate = candidates[0]
                finish_reason = candidate.get("finishReason", "UNKNOWN")
                content = candidate.get("content", {})
                parts = content.get("parts", [])

                if not parts:
                    raise GeminiTextError(
                        f"Gemini returned empty parts. finishReason={finish_reason}",
                        raw=body_text,
                    )

                # responseMimeType=application/json garantiza que la primera
                # part es texto JSON puro.
                text_part = next((p.get("text") for p in parts if "text" in p), None)
                if not text_part:
                    raise GeminiTextError(
                        f"Gemini returned no text part. finishReason={finish_reason}",
                        raw=body_text,
                    )

                try:
                    parsed = json.loads(text_part)
                except json.JSONDecodeError as je:
                    raise GeminiTextError(
                        f"Gemini text part is not valid JSON: {text_part[:300]}",
                        raw=body_text,
                    ) from je

                if not isinstance(parsed, dict):
                    raise GeminiTextError(
                        f"Gemini JSON output is not an object: {type(parsed).__name__}",
                        raw=body_text,
                    )

                logger.info(
                    "[GEMINI_TEXT] OK model=%s attempt=%d/%d finish=%s tokens_in=%s tokens_out=%s",
                    model,
                    attempt,
                    max_attempts,
                    finish_reason,
                    data.get("usageMetadata", {}).get("promptTokenCount"),
                    data.get("usageMetadata", {}).get("candidatesTokenCount"),
                )
                return parsed, data

        except GeminiTextError as e:
            last_error = e
            logger.warning(
                "[GEMINI_TEXT] attempt %d/%d failed (status=%s): %s",
                attempt,
                max_attempts,
                e.status,
                str(e)[:300],
            )
            # No tiene sentido reintentar errores de safety / content policy.
            if e.status in (400, 403):
                raise
        except Exception as e:
            last_error = e
            logger.warning(
                "[GEMINI_TEXT] attempt %d/%d unexpected error: %s",
                attempt,
                max_attempts,
                str(e)[:300],
            )

    # Después de todos los intentos.
    raise GeminiTextError(
        f"Gemini text call failed after {max_attempts} attempts. Last error: {last_error}",
        status=last_status,
        raw=last_body,
    )


async def call_gemini_freeform(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    conversation_history: Optional[list] = None,
    temperature: float = 0.7,
    max_output_tokens: int = 32768,
    thinking_level: Optional[str] = None,
) -> str:
    """Call Gemini for free-form text output (not JSON-constrained).

    Used for HTML section generation where the response is raw HTML, not
    structured JSON.  Supports multi-turn conversation via ``conversation_history``.

    Args:
        model: Gemini model id, e.g. ``"gemini-2.5-flash"``.
        system_prompt: System instruction (behaviour/role definition).
        user_message: The current user message (last turn).
        conversation_history: Optional list of prior turns, each a dict with
            ``{"role": "user"|"model", "text": "..."}``.
        temperature: Sampling temperature.
        max_output_tokens: Hard cap on output length.

    Returns:
        The raw text generated by Gemini (typically HTML).

    Raises:
        GeminiTextError: if all retries fail.
    """
    if not GOOGLE_GEMINI_API_KEY:
        raise GeminiTextError("GOOGLE_GEMINI_API_KEY is not set in env")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={GOOGLE_GEMINI_API_KEY}"
    )

    # Build contents array (history + current message)
    contents = []
    if conversation_history:
        for msg in conversation_history:
            contents.append(
                {
                    "role": msg["role"],
                    "parts": [{"text": msg["text"]}],
                }
            )
    contents.append(
        {
            "role": "user",
            "parts": [{"text": user_message}],
        }
    )

    generation_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    # Gemini 3.x thinking control. For deterministic HTML generation we use
    # "Low" — the default "High" can burn tens of thousands of tokens on
    # internal reasoning and hit the server timeout before emitting output.
    if thinking_level:
        generation_config["thinkingConfig"] = {"thinkingLevel": thinking_level}

    payload: Dict[str, Any] = {
        "systemInstruction": {"role": "system", "parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": generation_config,
    }

    headers = {"Content-Type": "application/json"}

    max_attempts = 5
    delay_after = 3
    last_error: Optional[Exception] = None
    last_status: Optional[int] = None
    last_body: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > delay_after:
                await asyncio.sleep(5)

            session = await _get_session()
            async with session.post(url, headers=headers, json=payload) as response:
                last_status = response.status
                body_text = await response.text()
                last_body = body_text

                if response.status == 429:
                    raise GeminiTextError(
                        f"Gemini rate limit (429): {body_text[:300]}",
                        status=429,
                        raw=body_text,
                    )

                if response.status != 200:
                    raise GeminiTextError(
                        f"Gemini HTTP {response.status}: {body_text[:300]}",
                        status=response.status,
                        raw=body_text,
                    )

                data = json.loads(body_text)
                candidates = data.get("candidates", [])
                if not candidates:
                    prompt_feedback = data.get("promptFeedback", {})
                    raise GeminiTextError(
                        f"Gemini no candidates. promptFeedback={prompt_feedback}",
                        raw=body_text,
                    )

                parts = candidates[0].get("content", {}).get("parts", [])
                text_parts = [p["text"] for p in parts if "text" in p]
                if not text_parts:
                    raise GeminiTextError(
                        f"Gemini returned no text. finishReason={candidates[0].get('finishReason')}",
                        raw=body_text,
                    )

                result = "\n".join(text_parts)
                logger.info(
                    "[GEMINI_FREEFORM] OK model=%s attempt=%d/%d tokens_in=%s tokens_out=%s",
                    model,
                    attempt,
                    max_attempts,
                    data.get("usageMetadata", {}).get("promptTokenCount"),
                    data.get("usageMetadata", {}).get("candidatesTokenCount"),
                )
                return result

        except GeminiTextError as e:
            last_error = e
            logger.warning(
                "[GEMINI_FREEFORM] attempt %d/%d failed (status=%s): %s",
                attempt,
                max_attempts,
                e.status,
                str(e)[:300],
            )
            if e.status in (400, 403):
                raise
        except Exception as e:
            last_error = e
            logger.warning(
                "[GEMINI_FREEFORM] attempt %d/%d unexpected: %s",
                attempt,
                max_attempts,
                str(e)[:300],
            )

    raise GeminiTextError(
        f"Gemini freeform call failed after {max_attempts} attempts. Last error: {last_error}",
        status=last_status,
        raw=last_body,
    )
