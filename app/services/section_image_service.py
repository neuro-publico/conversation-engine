import asyncio
import base64
import gc
import logging
import re
import time
import uuid
from typing import List

from app.externals.images.image_client import google_image_with_text, openai_image_edit
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.s3_upload_client import upload_file
from app.helpers.image_compression_helper import compress_image_to_target
from app.helpers.request_tracker import RequestTracker
from app.requests.section_image_request import SectionImageRequest
from app.responses.section_image_response import CtaButtonResponse, SectionImageResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert e-commerce landing page designer specializing in high-converting sales funnels for Latin American markets.

You will receive:
1. A prompt describing the section style and layout
2. A STYLE REFERENCE image (template) — match its layout, composition, typography, and visual style as closely as possible
3. A PRODUCT PHOTO — the REAL product that this landing page is selling
4. A SALES ANGLE that defines the communication strategy — adapt all copy, headlines, and messaging to match this angle

CRITICAL — TEMPLATE vs PRODUCT DISTINCTION:
- The STYLE REFERENCE image is a TEMPLATE that contains EXAMPLE/PLACEHOLDER products. These are NOT the real product.
- You MUST REPLACE every example product, placeholder image, and sample photo in the template with the REAL PRODUCT PHOTO provided.
- The REAL PRODUCT PHOTO must appear as-is — like a high-resolution photo cutout placed into the design.
- NEVER keep the template's example products in the final image. The only product visible must be the one from the PRODUCT PHOTO.

ABSOLUTE RULES:
- NEVER redraw, reinterpret, re-render, or artistically recreate the real product
- Every label, brand name, text on packaging, color, shape, and proportion of the REAL PRODUCT must be IDENTICAL to the provided photo
- This is a LANDING PAGE SECTION — it must look like part of a real e-commerce funnel, NOT a social media ad
- Mobile-first vertical layout
- All text in the specified language
- Professional, high-quality, ready-to-use section
- No mockup frames, browser windows, or device frames
- Adapt colors to match the real product's packaging colors automatically
- If brand colors are provided, use them as the primary reference for the design palette — buttons, accents, borders, and highlights should harmonize with these colors
- If a sales angle is provided, ALL text (headlines, benefits, CTAs, badges) must align with that angle's tone and messaging
- If pricing is provided, use the EXACT formatted values — do not change currency symbols, decimal separators, or number format"""

CTA_DETECTION_INSTRUCTION = """

[INSTRUCCIÓN OBLIGATORIA DE TEXTO]
Primero responde en texto: ¿dónde vas a poner los botones CTA en la imagen? Escribe:
BOTONES:
- "texto del botón" en [ymin, xmin, ymax, xmax] coords 0-1000
Si no hay botones en este tipo de sección, escribe: BOTONES: ninguno
Solo detecta botones de acción (comprar, pedir, agregar al carrito). No detectes badges, labels o texto decorativo.
Después de escribir esto, genera la imagen."""


class SectionImageService:

    async def generate_section_image(self, request: SectionImageRequest) -> SectionImageResponse:
        RequestTracker.custom_active += 1
        t_start = time.monotonic()
        RequestTracker.log("MEM", "START")

        try:
            return await self._do_generate(request, t_start)
        finally:
            elapsed = time.monotonic() - t_start
            RequestTracker.custom_active -= 1
            RequestTracker.log("MEM", "END", f"elapsed={elapsed:.1f}s")
            gc.collect()

    async def _do_generate(self, request: SectionImageRequest, t_start: float) -> SectionImageResponse:
        prompt = self._build_prompt(request)
        image_urls = self._collect_image_urls(request)
        print(f"[PROMPT-DEBUG] images={image_urls} prompt_length={len(prompt)}\n---PROMPT START---\n{prompt}\n---PROMPT END---", flush=True)

        extra_params = {
            "aspect_ratio": request.image_format,
            "image_size": "2K",
        }

        max_retries = 5
        delay_after = 3
        delay_seconds = 5
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                if attempt > delay_after:
                    await asyncio.sleep(delay_seconds)

                RequestTracker.log("MEM", f"PRE-GEMINI attempt={attempt}")

                image_bytes, text_response = await google_image_with_text(
                    image_urls=image_urls,
                    prompt=prompt,
                    extra_params=extra_params,
                )

                RequestTracker.log(
                    "MEM",
                    f"POST-GEMINI",
                    f"image_size={len(image_bytes)//1024}KB elapsed={time.monotonic()-t_start:.1f}s",
                )

                cta_buttons = self._parse_cta_buttons(text_response) if request.detect_cta_buttons else []
                del text_response
                s3_url = await self._compress_and_upload(image_bytes, request)
                del image_bytes

                RequestTracker.log("MEM", "POST-UPLOAD")

                return SectionImageResponse(
                    s3_url=s3_url,
                    cta_buttons=cta_buttons,
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Section image attempt {attempt}/{max_retries} failed: {type(e).__name__}: {str(e) or repr(e)}"
                )
                try:
                    del image_bytes
                except NameError:
                    pass

        # Fallback to OpenAI
        try:
            logger.info("Trying section image fallback: openai/gpt-image-1")
            fallback_prompt = self._build_prompt(request, include_cta_instruction=False)
            image_bytes = await openai_image_edit(
                image_urls=image_urls,
                prompt=fallback_prompt,
                model_ia="gpt-image-1",
                extra_params=extra_params,
            )
            s3_url = await self._compress_and_upload(image_bytes, request)
            del image_bytes
            return SectionImageResponse(
                s3_url=s3_url,
                cta_buttons=[],
            )
        except Exception as e:
            logger.error(f"Section image fallback also failed: {e}")
            raise last_error

    def _build_prompt(self, request: SectionImageRequest, include_cta_instruction: bool = True) -> str:
        parts = [SYSTEM_PROMPT]

        if include_cta_instruction and request.detect_cta_buttons:
            parts.append(CTA_DETECTION_INSTRUCTION)

        if request.user_prompt:
            parts.append(request.user_prompt)

        parts.append(f"\nProduct name: {request.product_name}")
        parts.append(f"Product description: {request.product_description}")
        parts.append(f"Language: {request.language}")

        if request.sale_angle_name:
            angle_block = (
                f"\nSALES ANGLE (this determines the communication tone and messaging for ALL text in the image):"
            )
            angle_block += f"\n- Angle: {request.sale_angle_name}"
            if request.sale_angle_description:
                angle_block += f"\n- Description: {request.sale_angle_description}"
            angle_block += f"\n- Adapt headlines, benefits, CTAs, and all copy to match this sales angle"
            parts.append(angle_block)

        def _clean_price(price_str: str) -> str:
            """Remove trailing ,00 or .00 decimals only at END (e.g. $ 140.000,00 → $ 140.000)"""
            import re
            return re.sub(r'[,.]00$', '', price_str) if price_str else price_str

        if request.price_formatted:
            price_block = "\nPRICING (use these EXACT formatted values wherever the template shows prices — do NOT change the format or currency):"
            if request.price_fake_formatted:
                price_block += f"\n- Original price (show crossed out): {_clean_price(request.price_fake_formatted)}"
            price_block += f"\n- Sale price (show large and prominent): {_clean_price(request.price_formatted)}"
            parts.append(price_block)
        elif request.price is not None:
            price_block = "\nPRICING (use these exact values wherever the template shows prices):"
            if request.price_fake is not None:
                price_block += f"\n- Original price (show crossed out): ${request.price_fake:,.0f}"
            price_block += f"\n- Sale price (show large and prominent): ${request.price:,.0f}"
            parts.append(price_block)

        if request.brand_colors and len(request.brand_colors) > 0:
            colors_str = ", ".join(request.brand_colors)
            colors_block = f"""\nBRAND COLORS (reference palette extracted from the product):
- Colors: {colors_str}

Use these as a color reference to create visual harmony between the section and the product. The design should feel like it belongs to the same brand, but you have creative freedom to choose contrast, backgrounds, and accents that work best for each specific section layout."""
            parts.append(colors_block)

        if request.user_instructions:
            parts.append(f"\nAdditional instructions: {request.user_instructions}")

        return "\n\n".join(parts)

    def _collect_image_urls(self, request: SectionImageRequest) -> list[str]:
        urls = []
        if request.template_image_url:
            urls.append(request.template_image_url)
        if request.product_image_url:
            urls.append(request.product_image_url)
        return urls

    def _parse_cta_buttons(self, text: str) -> List[CtaButtonResponse]:
        if not text or "BOTONES:" not in text:
            return []

        after_botones = text.split("BOTONES:")[-1][:50].strip().lower()
        if after_botones.startswith("ninguno") or after_botones.startswith("none"):
            return []

        buttons = []
        pattern = r'-\s*"([^"]+)"\s*en\s*\[(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]'
        for match in re.finditer(pattern, text):
            label = match.group(1)
            coords = [int(match.group(i)) for i in range(2, 6)]
            if all(0 <= c <= 1000 for c in coords) and coords[2] > coords[0] and coords[3] > coords[1]:
                buttons.append(CtaButtonResponse(label=label, coords=coords))

        return buttons

    async def _compress_and_upload(self, image_bytes: bytes, request: SectionImageRequest) -> str:
        loop = asyncio.get_event_loop()
        compressed_b64 = await loop.run_in_executor(
            None, lambda: compress_image_to_target(image_bytes, target_kb=request.target_kb, max_width=1080)
        )
        unique_id = uuid.uuid4().hex[:8]
        folder = f"creatives/sections/{request.owner_id}"
        file_name = f"section_{unique_id}"

        result = await upload_file(
            S3UploadRequest(
                file=compressed_b64,
                folder=folder,
                filename=file_name,
            )
        )
        return result.s3_url
