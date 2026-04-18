import asyncio
import base64
import gc
import logging
import re
import time
import uuid
from typing import Dict, List, Optional

from app.db.audit_logger import log_prompt
from app.externals.callback.callback_client import post_callback
from app.externals.images.image_client import google_image_with_text, openai_image_edit
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.s3_upload_client import upload_file
from app.helpers.concurrency import get_image_semaphore
from app.helpers.image_compression_helper import compress_image_to_target
from app.helpers.request_tracker import RequestTracker
from app.requests.section_image_request import SectionImageRequest
from app.responses.section_image_response import CtaButtonResponse, SectionImageResponse
from app.services.prompt_config_service import PromptConfigService

logger = logging.getLogger(__name__)

PROMPT_AGENT_ID_SYSTEM = "section_image_system"
PROMPT_AGENT_ID_CTA_DETECTION = "section_image_cta_detection"

FALLBACK_SYSTEM_PROMPT = """You are an expert e-commerce landing page designer specializing in high-converting sales funnels for Latin American markets.

You will receive:
1. A prompt describing the section style and layout
2. A STYLE REFERENCE image (template) — match its layout, composition, typography, and visual style as closely as possible
3. A PRODUCT PHOTO — the REAL product that this landing page is selling
4. A SALES ANGLE that defines the communication strategy — adapt all copy, headlines, and messaging to match this angle

CRITICAL — TEMPLATE vs PRODUCT DISTINCTION:
- The STYLE REFERENCE image is a TEMPLATE that contains EXAMPLE/PLACEHOLDER products. These are NOT the real product.
- You MUST REPLACE every example product, placeholder image, and sample photo in the template with the REAL PRODUCT PHOTO provided.
- NEVER keep the template's example products in the final image. The only product visible must be the one from the PRODUCT PHOTO.

ABSOLUTE RULES:
- Every label, brand name, text on packaging, color, shape, and proportion of the REAL PRODUCT must be IDENTICAL to the provided photo
- Mobile-first vertical layout
- All text in the specified language
- Professional, high-quality, ready-to-use section with good legibility and well-positioned elements
- No mockup frames, browser windows, or device frames
- Create well-structured, well-diagrammed designs based on the reference template — clear visual hierarchy, readable text, and balanced element placement
- Adapt ALL text to the specific product — do NOT copy text from the template. Your priority is to communicate the product clearly and persuasively from the provided sales angle
- Adapt colors to match the real product's packaging colors automatically
- If brand colors are provided, they DEFINE the color identity — adapt the template's colors to these brand tones so all sections share a consistent look. Respect the template's light/dark logic (dark stays dark, light stays light) but in the brand's color tones
- If a sales angle is provided, ALL text (headlines, benefits, CTAs, badges) must align with that angle's tone and messaging
- If pricing is provided, use the EXACT formatted values — do not change currency symbols, decimal separators, or number format"""

EDIT_SYSTEM_PROMPT = """You are an expert e-commerce landing page designer. You are EDITING an existing section image.

You will receive:
1. The CURRENT SECTION IMAGE — this is the image you must modify
2. (Optional) A REFERENCE IMAGE — use as visual inspiration for the requested changes
3. (Optional) A PRODUCT PHOTO — the real product shown in this section. This is the real product — maintain its exact appearance.

EDITING RULES:
- Using the provided section image, apply ONLY the changes described in the user's instructions
- Keep everything else exactly the same, preserving the original style, lighting, composition, and layout
- Do NOT regenerate the image from scratch — this must be a targeted modification
- Do not alter the composition or add/remove elements unless explicitly requested
- If the section contains a real product photo, preserve its identity exactly — never redraw, reinterpret, or re-render it
- If a REFERENCE IMAGE is provided, use it as visual inspiration for the changes, but apply them to the EXISTING section
- The result should look like a natural evolution of the current section, not a completely new design
- Mobile-first vertical layout
- Professional, high-quality, ready-to-use section with good legibility and well-positioned elements
- If brand colors are provided, use them for any new or modified design elements
- If pricing is provided, use the EXACT formatted values — do not change currency symbols, decimal separators, or format"""

FALLBACK_CTA_DETECTION = """[INSTRUCCIÓN OBLIGATORIA DE TEXTO]
Primero responde en texto: ¿dónde vas a poner los botones CTA en la imagen? Escribe:
BOTONES:
- "texto del botón" en [ymin, xmin, ymax, xmax] coords 0-1000
Si no hay botones en este tipo de sección, escribe: BOTONES: ninguno
Solo detecta botones de acción (comprar, pedir, agregar al carrito). No detectes badges, labels o texto decorativo.
Después de escribir esto, genera la imagen."""

PromptConfigService.register_fallback(PROMPT_AGENT_ID_SYSTEM, FALLBACK_SYSTEM_PROMPT)
PromptConfigService.register_fallback(PROMPT_AGENT_ID_CTA_DETECTION, FALLBACK_CTA_DETECTION)


IMAGE_MODEL = "gemini-3.1-flash-image-preview"

class SectionImageService:

    async def preview_image_prompt(
        self, user_prompt: Optional[str] = None, image_format: Optional[str] = None
    ) -> dict:
        """Preview the full prompt that the AI receives for image generation. Read-only, no AI call.

        Resolves the system prompt via `PromptConfigService` so the preview reflects
        whatever is currently in agent-config (not the hardcoded fallback) — that's the
        whole point of the dynamic prompts rollout.
        """
        request = SectionImageRequest(
            product_name="[Nombre del producto]",
            product_description="[Descripción del producto]",
            language="[Idioma]",
            product_image_url="[URL imagen del producto]",
            template_image_url="[URL imagen de referencia del template]",
            image_format=image_format or "9:16",
            price_formatted="[Precio de venta formateado]",
            price_fake_formatted="[Precio original formateado]",
            sale_angle_name="[Ángulo de venta seleccionado]",
            sale_angle_description="[Descripción del ángulo de venta]",
            user_prompt=user_prompt or None,
            detect_cta_buttons=True,
            owner_id="preview",
            brand_colors=["[Color primario]", "[Color secundario]"],
        )

        full_prompt = await self._build_prompt(request)
        system_prompt = await PromptConfigService.get(PROMPT_AGENT_ID_SYSTEM)

        blocks = []
        if request.user_prompt and "user_prompt" in full_prompt:
            blocks.append("Prompt de imagen (del template)")
        if "Product name:" in full_prompt:
            blocks.append("Producto (nombre + descripción)")
        if "SALES ANGLE" in full_prompt:
            blocks.append("Ángulo de venta")
        if "PRICING" in full_prompt:
            blocks.append("Precios")
        if "BRAND COLORS" in full_prompt:
            blocks.append("Colores de marca")
        if "Language:" in full_prompt:
            blocks.append("Idioma")
        blocks.append("Imagen del producto (foto real)")
        blocks.append("Imagen de referencia (template)")

        return {
            "system_prompt": system_prompt,
            "user_prompt": full_prompt,
            "blocks": blocks,
            "models": {
                "image_generation": IMAGE_MODEL,
            },
            "temperature": 1.0,
        }

    async def generate_section_image(self, request: SectionImageRequest) -> SectionImageResponse:
        semaphore = get_image_semaphore()
        async with semaphore:
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
        prompt = await self._build_prompt(request)
        image_urls = self._collect_image_urls(request)
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

                asyncio.create_task(
                    log_prompt(
                        log_type="section_image",
                        prompt=prompt,
                        response_url=s3_url,
                        owner_id=request.owner_id,
                        model="gemini-3.1-flash-image-preview",
                        provider="gemini",
                        brand_colors=request.brand_colors,
                        status="success",
                        attempt_number=attempt,
                        elapsed_ms=int((time.monotonic() - t_start) * 1000),
                        metadata={"cta_buttons": len(cta_buttons), "image_format": request.image_format},
                    )
                )
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
                    del image_bytes  # noqa: F821
                except NameError:
                    pass

        # Fallback to OpenAI
        try:
            logger.info("Trying section image fallback: openai/gpt-image-1")
            fallback_prompt = await self._build_prompt(request, include_cta_instruction=False)
            image_bytes = await openai_image_edit(
                image_urls=image_urls,
                prompt=fallback_prompt,
                model_ia="gpt-image-1",
                extra_params=extra_params,
            )
            s3_url = await self._compress_and_upload(image_bytes, request)
            del image_bytes
            asyncio.create_task(
                log_prompt(
                    log_type="section_image",
                    prompt=fallback_prompt,
                    response_url=s3_url,
                    owner_id=request.owner_id,
                    model="gpt-image-1",
                    provider="openai",
                    status="fallback",
                    fallback_used=True,
                    elapsed_ms=int((time.monotonic() - t_start) * 1000),
                )
            )
            return SectionImageResponse(
                s3_url=s3_url,
                cta_buttons=[],
            )
        except Exception as e:
            logger.error(f"Section image fallback also failed: {e}")
            asyncio.create_task(
                log_prompt(
                    log_type="section_image",
                    prompt=prompt,
                    owner_id=request.owner_id,
                    status="error",
                    error_message=str(last_error),
                    elapsed_ms=int((time.monotonic() - t_start) * 1000),
                )
            )
            raise last_error

    async def _build_prompt(self, request: SectionImageRequest, include_cta_instruction: bool = True) -> str:
        if request.edit_mode:
            system_prompt = EDIT_SYSTEM_PROMPT
        else:
            system_prompt = await PromptConfigService.get(PROMPT_AGENT_ID_SYSTEM)

        parts = [system_prompt]

        if include_cta_instruction and request.detect_cta_buttons:
            cta_instruction = await PromptConfigService.get(PROMPT_AGENT_ID_CTA_DETECTION)
            parts.append(cta_instruction)

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

            return re.sub(r"[,.]00$", "", price_str) if price_str else price_str

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
            colors_block = f"""\nBRAND COLORS (extracted from the product — these define the color identity):
- Colors: {colors_str}

These colors MUST be used to determine the overall tone of the image — accents, buttons, highlights, borders, gradients. The template may have different colors, but you must ADAPT it to use these brand tones so all sections share a consistent visual identity. Respect the template's light/dark logic (if the template has a dark background, keep it dark but in these brand tones; if light, keep it light)."""
            parts.append(colors_block)

        if request.user_instructions:
            parts.append(f"\nAdditional instructions: {request.user_instructions}")

        return "\n\n".join(parts)

    def _collect_image_urls(self, request: SectionImageRequest) -> list[str]:
        urls = []
        if request.edit_mode:
            # Edit mode: current section first, then reference, then product
            if request.current_section_url:
                urls.append(request.current_section_url)
            if request.reference_image_url:
                urls.append(request.reference_image_url)
            if request.product_image_url:
                urls.append(request.product_image_url)
        else:
            # Creation mode: template first, then product
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

    async def generate_and_callback(
        self,
        request: SectionImageRequest,
        request_id: str,
        callback_url: str,
        callback_metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        try:
            response = await self.generate_section_image(request)
            payload = {
                "status": "success",
                "request_id": request_id,
                "s3_url": response.s3_url,
                "cta_buttons": [btn.model_dump() for btn in response.cta_buttons],
                "metadata": callback_metadata or {},
            }
        except Exception as e:
            logger.error(f"Async section image generation failed (request_id={request_id}): {type(e).__name__}: {e}")
            payload = {
                "status": "error",
                "request_id": request_id,
                "error": str(e) or "unknown",
                "error_type": type(e).__name__,
                "metadata": callback_metadata or {},
            }

        try:
            await post_callback(callback_url, payload)
            asyncio.create_task(
                log_prompt(
                    log_type="callback_result",
                    prompt=f"callback to {callback_url}",
                    owner_id=request.owner_id,
                    model="callback",
                    provider="httpx",
                    status="success",
                    metadata={"request_id": request_id, "payload_status": payload.get("status")},
                )
            )
        except Exception as e:
            logger.error(f"Callback failed for request_id={request_id}: {type(e).__name__}: {e}")
            asyncio.create_task(
                log_prompt(
                    log_type="callback_result",
                    prompt=f"callback to {callback_url}",
                    owner_id=request.owner_id,
                    model="callback",
                    provider="httpx",
                    status="error",
                    error_message=f"{type(e).__name__}: {e}",
                    metadata={"request_id": request_id},
                )
            )
