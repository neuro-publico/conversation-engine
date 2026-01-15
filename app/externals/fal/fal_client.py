import urllib.parse
from typing import Any, Dict, Optional

import httpx

from app.configurations.config import FAL_AI_API_KEY


class FalClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or FAL_AI_API_KEY

    async def _post(self, path: str, payload: Dict[str, Any], fal_webhook: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("FAL_AI_API_KEY no configurada")

        base_url = f"https://queue.fal.run/{path}"
        if fal_webhook:
            query = f"fal_webhook={urllib.parse.quote_plus(fal_webhook)}"
            url = f"{base_url}?{query}"
        else:
            url = base_url

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def tts_multilingual_v2(self, text: str, fal_webhook: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        payload = {"text": text}
        payload.update(kwargs)
        return await self._post("fal-ai/elevenlabs/tts/multilingual-v2", payload, fal_webhook)

    async def bytedance_omnihuman(
        self, image_url: str, audio_url: str, fal_webhook: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        payload = {"image_url": image_url, "audio_url": audio_url}
        payload.update(kwargs)
        return await self._post("fal-ai/bytedance/omnihuman", payload, fal_webhook)

    async def kling_image_to_video(
        self, prompt: str, image_url: str, fal_webhook: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        payload = {"prompt": prompt, "image_url": image_url}
        payload.update(kwargs)
        return await self._post("fal-ai/kling-video/v2/master/image-to-video", payload, fal_webhook)
