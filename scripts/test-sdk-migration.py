#!/usr/bin/env python3
"""Compare v1 (raw HTTP generateContent) vs v2 (SDK Interactions + streaming).

Runs the same EDIT prompt against both and reports:
- Success / failure
- Duration
- Output size
- Finish/status
- Thought vs output tokens
- Whether the HTML closes properly (no mid-generation truncation)

Usage:
    cd conversation-engine
    source venv/bin/activate
    python scripts/test-sdk-migration.py
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# Allow importing app.* from this script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.externals.ai_direct.gemini_text import call_gemini_freeform  # noqa: E402
from app.externals.ai_direct.gemini_text_v2 import call_gemini_freeform_v2  # noqa: E402
from app.services.section_html_service import EDIT_SYSTEM_PROMPT  # noqa: E402

MODEL = "gemini-3.1-pro-preview"

# The HTML that broke in prod — 7393 bytes, 3 testimonios.
HTML_PATH = Path("/tmp/fluxi-poc/testimonios-72729.html")
INSTRUCTION = "agrega 5 testimonios más, osea en total 8"


def build_user_prompt(html: str, instruction: str) -> str:
    return f"""Product: Vitaluxe 1
Description: Colageno hidrolizado premium

CURRENT HTML:
{html}

USER INSTRUCTION: {instruction}

Return only the modified HTML, starting with <section and ending with </section>."""


def summarize(name: str, result: dict, duration: float, error: Exception | None):
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    if error:
        print(f"❌ FAILED after {duration:.1f}s: {type(error).__name__}: {error}")
        return
    text = result.get("text") or result.get("html") or ""
    print(f"✅ OK in {duration:.1f}s")
    print(f"  output length: {len(text)}")
    print(f"  testimonios (Comprador Verificado): {text.count('Comprador Verificado')}")
    print(f"  closes </section>: {'</section>' in text}")
    print(f"  ends: ...{text[-80:]!r}")
    usage = result.get("usage") or {}
    if usage:
        print(f"  usage: {usage}")


async def run_v1(html: str):
    t0 = time.monotonic()
    try:
        raw = await call_gemini_freeform(
            model=MODEL,
            system_prompt=EDIT_SYSTEM_PROMPT,
            user_message=build_user_prompt(html, INSTRUCTION),
            temperature=1.0,
            max_output_tokens=32768,
            thinking_level="Low",
        )
        elapsed = time.monotonic() - t0
        summarize("V1 (raw HTTP generateContent, streaming OFF)", {"text": raw}, elapsed, None)
    except Exception as e:
        elapsed = time.monotonic() - t0
        summarize("V1 (raw HTTP generateContent, streaming OFF)", {}, elapsed, e)


async def run_v2(html: str):
    t0 = time.monotonic()
    try:
        result = await call_gemini_freeform_v2(
            model=MODEL,
            system_prompt=EDIT_SYSTEM_PROMPT,
            user_message=build_user_prompt(html, INSTRUCTION),
            temperature=1.0,
            max_output_tokens=32768,
            thinking_level="low",
        )
        elapsed = time.monotonic() - t0
        summarize("V2 (SDK Interactions + streaming)", result, elapsed, None)
    except Exception as e:
        elapsed = time.monotonic() - t0
        summarize("V2 (SDK Interactions + streaming)", {}, elapsed, e)


async def main():
    if not HTML_PATH.exists():
        print(f"Need real-section HTML at {HTML_PATH}. Export from DB first.")
        sys.exit(2)
    html = HTML_PATH.read_text()
    print(f"Input HTML: {len(html)} bytes | instruction: {INSTRUCTION!r}\n")

    # Run sequentially so we can compare cleanly (and avoid Gemini rate-limit).
    await run_v2(html)   # test v2 first — this is the one we care about
    # Don't hammer v1 — it took 5 minutes to fail. Uncomment if needed:
    # await run_v1(html)


if __name__ == "__main__":
    asyncio.run(main())
