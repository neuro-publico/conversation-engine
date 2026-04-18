"""Service for generating sub-element images within HTML sections.

Follows the same patterns as ``section_image_service.py``:
- Direct Gemini API calls (no LangChain)
- Retry with backoff + OpenAI fallback
- Semaphore for concurrency control
- S3 upload with compression
- Audit logging

The key difference from the old agent-based approach: modern Gemini models
with thinking (``thinkingConfig: High``) generate better images in ONE call
than the old two-step process (LLM generates prompt → image model generates
image). The thinking replaces the prompt-generation agent entirely.

Model: ``gemini-3.1-flash-image-preview`` (same as section_image_service).
"""

import asyncio
import gc
import logging
import os
import time
import uuid
from typing import Optional

from app.db.audit_logger import log_prompt
from app.externals.images.image_client import google_image_with_text, openai_image_edit
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.s3_upload_client import upload_file
from app.helpers.concurrency import get_image_semaphore
from app.helpers.image_compression_helper import compress_image_to_target
from app.helpers.request_tracker import RequestTracker
from app.requests.sub_image_request import GenerateSubImagesRequest, SubImageItem
from app.responses.sub_image_response import GenerateSubImagesResponse

logger = logging.getLogger(__name__)

# Constants for transparency (read by preview endpoints)
SUB_IMAGE_MODEL = os.environ.get("SUB_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
SUB_IMAGE_FALLBACK_MODEL = os.environ.get("SUB_IMAGE_FALLBACK_MODEL", "gpt-image-1")
SUB_IMAGE_FALLBACK_PROVIDER = "openai"
SUB_IMAGE_MAX_RETRIES = 5
SUB_IMAGE_DELAY_AFTER_ATTEMPT = 3
SUB_IMAGE_RETRY_DELAY_SECONDS = 5

SUB_IMAGE_PROMPT_TEMPLATE = """You are generating a specific image element for an e-commerce landing page section.

CONTEXT:
- Product: {product_name}
- Description: {product_description}
- Language: {language}
{angle_block}
{colors_block}
{context_block}

IMAGE INSTRUCTIONS:
{prompt}

RULES:
- The image must be professional, clean, and ready for a real landing page
- Use the provided product photos as style/color reference
- Match the product's visual identity (colors, mood, tone)
- Mobile-optimized: must look good at small sizes
- No text in the image unless the prompt specifically asks for it
- High quality, well-lit, balanced composition"""


class SubImageService:
    """Generates sub-element images for HTML sections."""

    async def generate_sub_images(self, request: GenerateSubImagesRequest) -> GenerateSubImagesResponse:
        """Generate all requested images in parallel with concurrency control."""
        t_start = time.monotonic()
        semaphore = get_image_semaphore()

        # Collect product image URLs for reference
        ref_urls = []
        if request.product_images:
            ref_urls = request.product_images[:3]
        elif request.product_image_url:
            ref_urls = [request.product_image_url]

        # Generate all images in parallel (max 5 concurrent)
        tasks = [self._generate_one(item, request, ref_urls, semaphore) for item in request.images]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build response
        images = {}
        errors = {}
        for item, result in zip(request.images, results):
            if isinstance(result, Exception):
                errors[item.id] = f"{type(result).__name__}: {str(result)[:200]}"
                logger.error(f"Sub-image {item.id} failed: {result}")
            else:
                images[item.id] = result

        elapsed = int((time.monotonic() - t_start) * 1000)
        asyncio.create_task(
            log_prompt(
                log_type="sub_images",
                prompt=f"{len(request.images)} images requested",
                owner_id=request.owner_id,
                model="gemini-3.1-flash-image-preview",
                provider="gemini",
                status="success" if not errors else "partial",
                elapsed_ms=elapsed,
                metadata={
                    "total": len(request.images),
                    "success": len(images),
                    "failed": len(errors),
                },
            )
        )

        return GenerateSubImagesResponse(images=images, errors=errors)

    async def _generate_one(
        self,
        item: SubImageItem,
        request: GenerateSubImagesRequest,
        ref_urls: list[str],
        semaphore: asyncio.Semaphore,
    ) -> str:
        """Generate a single sub-image with retry, fallback, and concurrency control."""
        async with semaphore:
            RequestTracker.custom_active += 1
            t_start = time.monotonic()

            try:
                prompt = self._build_prompt(item, request)
                extra_params = {
                    "aspect_ratio": item.aspect_ratio,
                    "image_size": "1K",
                }

                # Retry with backoff (same pattern as section_image_service)
                max_retries = SUB_IMAGE_MAX_RETRIES
                delay_after = SUB_IMAGE_DELAY_AFTER_ATTEMPT
                last_error = None

                for attempt in range(1, max_retries + 1):
                    try:
                        if attempt > delay_after:
                            await asyncio.sleep(SUB_IMAGE_RETRY_DELAY_SECONDS)

                        image_bytes, _ = await google_image_with_text(
                            image_urls=ref_urls,
                            prompt=prompt,
                            extra_params=extra_params,
                        )

                        s3_url = await self._compress_and_upload(image_bytes, request.owner_id)
                        del image_bytes

                        asyncio.create_task(
                            log_prompt(
                                log_type="sub_image",
                                prompt=prompt[:500],
                                response_url=s3_url,
                                owner_id=request.owner_id,
                                model="gemini-3.1-flash-image-preview",
                                provider="gemini",
                                status="success",
                                attempt_number=attempt,
                                elapsed_ms=int((time.monotonic() - t_start) * 1000),
                                metadata={"image_id": item.id},
                            )
                        )
                        return s3_url

                    except Exception as e:
                        last_error = e
                        logger.warning(
                            f"Sub-image {item.id} attempt {attempt}/{max_retries} failed: "
                            f"{type(e).__name__}: {str(e)[:200]}"
                        )
                        try:
                            del image_bytes
                        except NameError:
                            pass

                # Fallback to OpenAI
                try:
                    logger.info(
                        f"Sub-image {item.id} fallback: {SUB_IMAGE_FALLBACK_PROVIDER}/{SUB_IMAGE_FALLBACK_MODEL}"
                    )
                    image_bytes = await openai_image_edit(
                        image_urls=ref_urls,
                        prompt=prompt,
                        model_ia=SUB_IMAGE_FALLBACK_MODEL,
                        extra_params=extra_params,
                    )
                    s3_url = await self._compress_and_upload(image_bytes, request.owner_id)
                    del image_bytes

                    asyncio.create_task(
                        log_prompt(
                            log_type="sub_image",
                            prompt=prompt[:500],
                            response_url=s3_url,
                            owner_id=request.owner_id,
                            model="gpt-image-1",
                            provider="openai",
                            status="fallback",
                            elapsed_ms=int((time.monotonic() - t_start) * 1000),
                            metadata={"image_id": item.id},
                        )
                    )
                    return s3_url

                except Exception as e:
                    logger.error(f"Sub-image {item.id} fallback also failed: {e}")
                    raise last_error  # type: ignore[misc]

            finally:
                RequestTracker.custom_active -= 1
                gc.collect()

    def _build_prompt(self, item: SubImageItem, request: GenerateSubImagesRequest) -> str:
        angle_block = ""
        if request.sale_angle_name:
            angle_block = f"- Sales angle: {request.sale_angle_name}"

        colors_block = ""
        if request.brand_colors:
            colors_block = f"- Brand colors: {', '.join(request.brand_colors)}"

        context_block = ""
        if item.context:
            context_block = f"- Element context: {item.context}"

        return SUB_IMAGE_PROMPT_TEMPLATE.format(
            product_name=request.product_name,
            product_description=request.product_description,
            language=request.language,
            angle_block=angle_block,
            colors_block=colors_block,
            context_block=context_block,
            prompt=item.prompt,
        )

    async def _compress_and_upload(self, image_bytes: bytes, owner_id: str) -> str:
        loop = asyncio.get_event_loop()
        compressed_b64 = await loop.run_in_executor(
            None, lambda: compress_image_to_target(image_bytes, target_kb=120, max_width=800)
        )
        unique_id = uuid.uuid4().hex[:8]
        folder = f"creatives/sections/{owner_id}"
        file_name = f"sub_{unique_id}"

        result = await upload_file(
            S3UploadRequest(
                file=compressed_b64,
                folder=folder,
                filename=file_name,
            )
        )
        return result.s3_url
