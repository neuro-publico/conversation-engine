import base64
from typing import Optional

import aiohttp
import asyncio
import httpx
import base64

from app.configurations.config import REPLICATE_API_KEY, GOOGLE_GEMINI_API_KEY


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


async def google_image(prompt: str, file: Optional[str] = None) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GOOGLE_GEMINI_API_KEY}"

    parts = [{"text": prompt}]

    if file:
        parts.append({
            "inlineData": {
                "mimeType": "image/png",
                "data": file
            }
        })

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": {
            "responseModalities": ["Text", "Image"]
        }
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
                    return None
                else:
                    error_text = await response.text()
                    print(f"Error {response.status}: {error_text}")
                    response.raise_for_status()
    except Exception as e:
        print(f"Error al generar imagen: {str(e)}")
        raise Exception(f"Error al generar imagen: {str(e)}")
