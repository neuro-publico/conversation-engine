import asyncio
import json
import logging
import re
from typing import Tuple

import aiohttp
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from app.configurations.config import URL_SCRAPER_LAMBDA
from app.requests.clone_page_request import ClonePageRequest
from app.responses.clone_page_response import ClonePageMetadata, ClonePageResponse
from app.services.clone_page_service_interface import ClonePageServiceInterface

logger = logging.getLogger(__name__)

CLONE_MODEL = "claude-sonnet-4-5-20250514"
CLONE_MAX_TOKENS = 32000

CLONE_PROMPT = """You are an elite frontend engineer specialized in replicating web pages with pixel-perfect precision.
Your goal is to produce a single self-contained HTML document that is visually indistinguishable from the provided screenshot.

## INPUTS
- **HTML source**: The raw HTML of the page (provided as text below).
- **Screenshot**: A full-page capture of the rendered page (provided as an image).

## PHASE 1 — RECONNAISSANCE (analyze before coding)

From the HTML source, extract:
- All image URLs (src, srcset, data-src, background-image). Convert relative URLs to absolute using the base domain.
- Font families and Google Fonts links.
- CSS variables, colors, border-radius values.
- The exact vertical order of all sections.

From the screenshot, verify:
- Section order from top to bottom.
- Background colors per section.
- Text content (copy it literally, never translate or summarize).
- Button styles (filled, outline, ghost).
- Layout patterns (centered, grid, full-width).

## PHASE 2 — CONSTRUCTION

Generate a single HTML document with these rules:

**Structure**: All CSS in a single `<style>` tag in the `<head>`. No external CSS files. No JavaScript unless strictly needed for visual behavior (e.g., carousel). Semantic HTML5 tags.

**Images**: Use the REAL absolute URLs extracted from the HTML source. Never use placeholders. Add `loading="lazy"` for images below the fold. Always include a descriptive `alt` attribute.

**Typography**: Copy the exact font-stack from the original. If it uses Google Fonts, include the `<link>` in `<head>`. Respect font-weight, font-size, and line-height.

**Colors**: Define all colors as CSS variables in `:root`. Extract exact values from the HTML/CSS source.

**Buttons**: Replicate all CTA variants with correct border-radius, padding, font-size. Add `transition: all 0.2s ease` for hover states.

**Navbar**: `position: sticky; top: 0; z-index: 9999`. Replicate exact structure. If it has blur/transparency, implement with `backdrop-filter`.

**Responsive**: Add breakpoints at 1200px, 1024px, 768px, 480px. On mobile: vertical stacks, full-width images, typography reduced ~20%.

## PHASE 3 — OUTPUT FORMAT

Return a JSON object with this exact structure (no markdown fences, no explanation, ONLY the JSON):

{
  "html": "<the complete self-contained HTML document as a single string>",
  "images": ["absolute-url-1", "absolute-url-2"],
  "metadata": {
    "title": "page title from <title> or main heading",
    "colors": ["#hex1", "#hex2", "#hex3"],
    "fonts": ["Font Family 1", "Font Family 2"]
  }
}

CRITICAL RULES:
- Return ONLY valid JSON. No text before or after the JSON.
- The "html" field must contain the COMPLETE HTML document (<!DOCTYPE html> through </html>).
- Every text must be copied literally from the source — never invent, translate, or summarize.
- Every image must use a real absolute URL from the source.
- The page must be responsive and work on mobile."""


class ClonePageService(ClonePageServiceInterface):
    async def clone_page(self, request: ClonePageRequest) -> ClonePageResponse:
        url = str(request.url)
        logger.info("Cloning page: %s", url)

        try:
            html_source, screenshot_base64 = await self._scrape_page(url)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error("Network error scraping %s: %s", url, e)
            raise HTTPException(status_code=502, detail=f"Failed to reach scraper service: {e}")

        try:
            clone_result = await self._generate_clone(html_source, screenshot_base64, url)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("AI clone generation failed for %s: %s", url, e)
            raise HTTPException(status_code=500, detail=f"AI clone generation failed: {e}")

        if "html" not in clone_result:
            raise HTTPException(status_code=500, detail="AI response missing 'html' key")

        return ClonePageResponse(
            html=clone_result["html"],
            images=clone_result.get("images", []),
            metadata=ClonePageMetadata(
                original_url=url,
                title=clone_result.get("metadata", {}).get("title"),
                colors=clone_result.get("metadata", {}).get("colors", []),
                fonts=clone_result.get("metadata", {}).get("fonts", []),
            ),
        )

    async def _scrape_page(self, url: str) -> Tuple[str, str]:
        payload = {"url": url, "take_screenshot": True}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                URL_SCRAPER_LAMBDA,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("Scraper returned status %d for %s: %s", response.status, url, error_text)
                    raise HTTPException(status_code=400, detail=f"Error scraping page: {error_text}")

                data = await response.json()
                html_content = data.get("content", "")
                screenshot = data.get("screenshot", "")

                if not html_content:
                    raise HTTPException(status_code=400, detail="Scraper returned empty HTML")
                if not screenshot:
                    raise HTTPException(status_code=400, detail="Scraper returned no screenshot")

                return html_content, screenshot

    async def _generate_clone(self, html_source: str, screenshot_base64: str, url: str) -> dict:
        llm = ChatAnthropic(model=CLONE_MODEL, temperature=0.2, max_tokens=CLONE_MAX_TOKENS, top_p=1)

        truncated_html = html_source[:80000]

        content = [
            {"type": "text", "text": f"{CLONE_PROMPT}\n\n## HTML SOURCE (from {url}):\n\n{truncated_html}"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{screenshot_base64}"},
            },
        ]

        response = await llm.ainvoke([HumanMessage(content=content)])
        return self._parse_response(response.content)

    def _parse_response(self, response_text: str) -> dict:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*(.*?)```", response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise HTTPException(status_code=500, detail="Failed to parse AI clone response as JSON")
