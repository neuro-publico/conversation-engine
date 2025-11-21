import base64
import mimetypes
from typing import Optional
import os

import aiohttp
import asyncio
import httpx
import base64

import requests

from app.configurations import config
from app.configurations.config import REPLICATE_API_KEY, GOOGLE_GEMINI_API_KEY, OPENAI_API_KEY


async def generate_image_variation(
        image_url: str,
        prompt: str,
        aspect_ratio: str = "1:1",
        output_format: str = "webp",
        output_quality: int = 80,
        prompt_upsampling: bool = False,
        safety_tolerance: int = 2
) -> bytes:
    payload = {
        "input": {
            "aspect_ratio": aspect_ratio,
            "image_prompt": image_url,
            "output_format": output_format,
            "output_quality": output_quality,
            "prompt": prompt,
            "prompt_upsampling": prompt_upsampling,
            "safety_tolerance": safety_tolerance
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions",
                headers={
                    "Authorization": f"Bearer {REPLICATE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
        ) as response:
            if response.status == 200 or response.status == 201:
                prediction_data = await response.json()

                while True:
                    async with session.get(
                            prediction_data["urls"]["get"],
                            headers={"Authorization": f"Bearer {REPLICATE_API_KEY}"}
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
        return {
            "inlineData": {
                "mimeType": 'image/jpeg',
                "data": image_base64
            }
        }
    return {
        "inline_data": {
            "mime_type": 'image/jpeg',
            "data": image_base64
        }
    }


async def _fetch_and_encode_images(image_urls: list[str], is_model_25: bool) -> list[dict]:
    parts = []
    async with aiohttp.ClientSession() as fetch_session:
        for image_url in image_urls:
            try:
                async with fetch_session.get(image_url) as img_response:
                    if img_response.status == 200:
                        image_bytes = await img_response.read()
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        parts.append(_build_image_part(image_base64, is_model_25))
            except Exception as e:
                print(f"Error al procesar imagen de {image_url}: {str(e)}")
                continue
    return parts


def _build_generation_config(is_model_25: bool, aspect_ratio: str, image_size: str) -> dict:
    config = {"responseModalities": ["Text", "Image"]}
    if not is_model_25:
        config["imageConfig"] = {
            "aspectRatio": aspect_ratio,
            "imageSize": image_size
        }
    return config


async def google_image(image_urls: list[str], prompt: str, model_ia: Optional[str] = None, extra_params: Optional[dict] = None) -> bytes:
    if extra_params is None:
        extra_params = {}
    
    is_model_25 = model_ia and '2.5' in model_ia
    aspect_ratio = extra_params.get('aspect_ratio', '1:1')
    image_size = extra_params.get('image_size', '1K')
    
    model_name = 'gemini-2.5-flash-image-preview' if is_model_25 else 'gemini-3-pro-image-preview'
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GOOGLE_GEMINI_API_KEY}"

    parts = [{"text": prompt}]
    
    if image_urls:
        image_parts = await _fetch_and_encode_images(image_urls, is_model_25)
        parts.extend(image_parts)

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": _build_generation_config(is_model_25, aspect_ratio, image_size)
    }

    headers = {'Content-Type': 'application/json'}

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


async def openai_image_edit(image_urls: list[str], prompt: str, model_ia: Optional[str] = None, extra_params: Optional[dict] = None) -> bytes:
    url = "https://api.openai.com/v1/images/edits"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}"
    }
    data = aiohttp.FormData()

    async with aiohttp.ClientSession() as fetch_session:
        for image_url in image_urls:
            async with fetch_session.get(image_url) as img_response:
                if img_response.status == 200:
                    image_bytes = await img_response.read()
                    filename = os.path.basename(image_url)
                    content_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'
                    data.add_field(
                        'image[]',
                        image_bytes,
                        filename=filename,
                        content_type=content_type
                    )

    prompt = prompt + ". **escena completa visible, composición centrada, todos los elementos dentro del marco cuadrado, nada recortado en los bordes, composición completa**"

    if extra_params is None:
        extra_params = {}
    
    size = extra_params.get('resolution', '1024x1024') or '1024x1024'
    
    data.add_field('size', size)
    data.add_field('prompt', prompt)
    data.add_field('model', 'gpt-image-1')
    data.add_field('n', '1')

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
