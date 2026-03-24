import asyncio
import base64
import mimetypes
import os
from typing import Optional

import aiohttp
import httpx
import requests

from app.configurations import config
from app.configurations.config import GOOGLE_GEMINI_API_KEY, OPENAI_API_KEY, REPLICATE_API_KEY

# Shared session for Gemini API calls (reuses TCP connections)
_gemini_session: Optional[aiohttp.ClientSession] = None


async def _get_gemini_session() -> aiohttp.ClientSession:
    global _gemini_session
    if _gemini_session is None or _gemini_session.closed:
        _gemini_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120),
            connector=aiohttp.TCPConnector(limit=20),
        )
    return _gemini_session


async def generate_image_variation(
    image_url: str,
    prompt: str,
    aspect_ratio: str = "1:1",
    output_format: str = "webp",
    output_quality: int = 80,
    prompt_upsampling: bool = False,
    safety_tolerance: int = 2,
) -> bytes:
    payload = {
        "input": {
            "aspect_ratio": aspect_ratio,
            "image_prompt": image_url,
            "output_format": output_format,
            "output_quality": output_quality,
            "prompt": prompt,
            "prompt_upsampling": prompt_upsampling,
            "safety_tolerance": safety_tolerance,
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions",
            headers={"Authorization": f"Bearer {REPLICATE_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        ) as response:
            if response.status == 200 or response.status == 201:
                prediction_data = await response.json()

                while True:
                    async with session.get(
                        prediction_data["urls"]["get"], headers={"Authorization": f"Bearer {REPLICATE_API_KEY}"}
                    ) as status_response:
                        status_data = await status_response.json()
                        if status_data["status"] == "succeeded":
                            image_url = status_data["output"]
                            async with session.get(image_url) as img_response:
                                if img_response.status == 200:
                                    return await img_response.read()
                                else:
                                    raise Exception(f"Error downloading image: {img_response.status}")
                        elif status_data["status"] == "failed":
                            raise Exception("Image Generation Failed")

                        await asyncio.sleep(1)
            else:
                raise Exception(f"Error {response.status}: {await response.text()}")


def _build_image_part(image_base64: str, is_model_25: bool) -> dict:
    if is_model_25:
        return {"inlineData": {"mimeType": "image/jpeg", "data": image_base64}}
    return {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}


async def _fetch_and_encode_images(
    image_urls: list[str], is_model_25: bool, session: Optional[aiohttp.ClientSession] = None
) -> list[dict]:
    async def _fetch_one(fetch_session: aiohttp.ClientSession, image_url: str) -> Optional[dict]:
        try:
            async with fetch_session.get(image_url) as img_response:
                if img_response.status == 200:
                    image_bytes = await img_response.read()
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    return _build_image_part(image_base64, is_model_25)
        except Exception as e:
            print(f"Error al procesar imagen de {image_url}: {str(e)}")
        return None

    if session:
        # Use shared session, download in parallel
        results = await asyncio.gather(*[_fetch_one(session, url) for url in image_urls])
        return [r for r in results if r is not None]
    else:
        # Legacy: create new session (keeps google_image() unchanged)
        async with aiohttp.ClientSession() as fetch_session:
            results = await asyncio.gather(*[_fetch_one(fetch_session, url) for url in image_urls])
            return [r for r in results if r is not None]


def _build_generation_config(is_model_25: bool, aspect_ratio: str, image_size: str) -> dict:
    config = {"responseModalities": ["Text", "Image"]}
    if not is_model_25:
        config["imageConfig"] = {"aspectRatio": aspect_ratio, "imageSize": image_size}
    return config


async def google_image(
    image_urls: list[str], prompt: str, model_ia: Optional[str] = None, extra_params: Optional[dict] = None
) -> bytes:
    if extra_params is None:
        extra_params = {}

    # Use configured model if it's an image model, otherwise default
    # This preserves backward compat: existing agents with text model names
    # (e.g. "gemini-2.5-pro") will keep using the current default
    if model_ia and "image" in model_ia.lower():
        model_name = model_ia
    else:
        model_name = "gemini-3-pro-image-preview"

    is_model_25 = "2.5" in model_name
    aspect_ratio = extra_params.get("aspect_ratio", "1:1")
    image_size = extra_params.get("image_size", "1K")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GOOGLE_GEMINI_API_KEY}"

    parts = [{"text": prompt}]

    if image_urls:
        image_parts = await _fetch_and_encode_images(image_urls, is_model_25)
        parts.extend(image_parts)

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": _build_generation_config(is_model_25, aspect_ratio, image_size),
    }

    headers = {"Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    parts = data["candidates"][0]["content"]["parts"]

                    for part in parts:
                        if "inlineData" in part:
                            img_data_base64 = part["inlineData"]["data"]
                            img_bytes = base64.b64decode(img_data_base64)
                            return img_bytes

                    raise Exception("No se generó ninguna imagen en la respuesta de Google Gemini")
                else:
                    error_text = await response.text()
                    print(f"Error {response.status}: {error_text}")
                    response.raise_for_status()
    except Exception as e:
        print(f"Error al generar imagen con Google Gemini: {str(e)}")
        raise Exception(f"Error al generar imagen con Google Gemini: {str(e)}")


async def google_image_with_text(
    image_urls: list[str], prompt: str, model_ia: Optional[str] = None, extra_params: Optional[dict] = None
) -> tuple[bytes, str]:
    """Like google_image() but returns (image_bytes, text_response) instead of just image_bytes."""
    if extra_params is None:
        extra_params = {}

    default_model = os.environ.get("SECTION_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
    if model_ia and "image" in model_ia.lower():
        model_name = model_ia
    else:
        model_name = default_model

    is_model_25 = "2.5" in model_name
    is_flash = "flash" in model_name
    aspect_ratio = extra_params.get("aspect_ratio", "1:1")
    image_size = extra_params.get("image_size", "1K")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GOOGLE_GEMINI_API_KEY}"

    parts = [{"text": prompt}]

    if image_urls:
        session = await _get_gemini_session()
        image_parts = await _fetch_and_encode_images(image_urls, is_model_25, session=session)
        parts.extend(image_parts)

    gen_config = _build_generation_config(is_model_25, aspect_ratio, image_size)
    if is_flash:
        gen_config["thinkingConfig"] = {"thinkingLevel": "High"}

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": gen_config,
    }

    headers = {"Content-Type": "application/json"}

    try:
        session = await _get_gemini_session()
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 429:
                error_text = await response.text()
                raise Exception(f"Gemini rate limit (429): {error_text[:300]}")

            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Gemini HTTP {response.status}: {error_text[:300]}")

            data = await response.json()
            candidates = data.get("candidates", [])

            if not candidates:
                prompt_feedback = data.get("promptFeedback", {})
                raise Exception(f"Gemini no candidates. promptFeedback: {prompt_feedback}")

            candidate = candidates[0]
            finish_reason = candidate.get("finishReason", "UNKNOWN")
            content = candidate.get("content", {})
            resp_parts = content.get("parts", [])

            if not resp_parts:
                raise Exception(f"Gemini empty parts. finishReason: {finish_reason}")

            image_bytes = None
            text_parts = []
            for part in resp_parts:
                if "inlineData" in part:
                    image_bytes = base64.b64decode(part["inlineData"]["data"])
                elif "text" in part:
                    text_parts.append(part["text"])

            if image_bytes is None:
                raise Exception(f"Gemini no image in response. finishReason: {finish_reason}, text: {' '.join(text_parts)[:200]}")

            return image_bytes, "\n".join(text_parts)
    except Exception as e:
        print(f"Error google_image_with_text: {str(e)}")
        raise


async def openai_image_edit(
    image_urls: list[str], prompt: str, model_ia: Optional[str] = None, extra_params: Optional[dict] = None
) -> bytes:
    url = "https://api.openai.com/v1/images/edits"
    headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}
    data = aiohttp.FormData()

    async with aiohttp.ClientSession() as fetch_session:
        for image_url in image_urls:
            async with fetch_session.get(image_url) as img_response:
                if img_response.status == 200:
                    image_bytes = await img_response.read()
                    filename = os.path.basename(image_url)
                    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
                    data.add_field("image[]", image_bytes, filename=filename, content_type=content_type)

    prompt = (
        prompt
        + ". **escena completa visible, composición centrada, todos los elementos dentro del marco cuadrado, nada recortado en los bordes, composición completa**"
    )

    if extra_params is None:
        extra_params = {}

    size = extra_params.get("resolution", "1024x1024") or "1024x1024"

    data.add_field("size", size)
    data.add_field("prompt", prompt)
    data.add_field("model", model_ia or "gpt-image-1")
    data.add_field("n", "1")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if "data" in result and len(result["data"]) > 0 and "b64_json" in result["data"][0]:
                        b64_image = result["data"][0]["b64_json"]
                        image_bytes = base64.b64decode(b64_image)
                        return image_bytes
                    else:
                        raise Exception(f"Respuesta inesperada de la API de OpenAI: {result}")
                else:
                    error_text = await response.text()
                    print(f"Error {response.status}: {error_text}")
                    response.raise_for_status()
    except aiohttp.ClientError as e:
        print(f"Error red al generar imagen: {str(e)}")
        raise Exception(f"Error de red al llamar a OpenAI: {e}") from e
    except Exception as e:
        print(f"Error al generar imagen: {str(e)}")
        raise Exception(f"Error al editar imagen con OpenAI: {e}") from e
