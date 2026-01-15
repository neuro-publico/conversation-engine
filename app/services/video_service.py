from typing import Any, Dict

from fastapi import Depends, HTTPException

from app.externals.fal.fal_client import FalClient
from app.requests.generate_video_request import GenerateVideoRequest, VideoType
from app.services.video_service_interface import VideoServiceInterface


class VideoService(VideoServiceInterface):
    def __init__(self, fal_client: FalClient = Depends()):
        self.fal_client = fal_client

    async def generate_video(self, request: GenerateVideoRequest) -> Dict[str, Any]:
        content: Dict[str, Any] = request.content or {}

        try:
            if request.type == VideoType.animated_scene:
                prompt = content.get("prompt")
                image_url = content.get("image_url")
                if not prompt or not image_url:
                    raise HTTPException(
                        status_code=400, detail="Se requieren 'prompt' e 'image_url' en content para animated_scene"
                    )
                fal_webhook = content.get("fal_webhook")
                extra = {k: v for k, v in content.items() if k not in {"prompt", "image_url", "fal_webhook"}}
                return await self.fal_client.kling_image_to_video(
                    prompt=prompt, image_url=image_url, fal_webhook=fal_webhook, **extra
                )

            if request.type == VideoType.human_scene:
                image_url = content.get("image_url")
                audio_url = content.get("audio_url")
                if not image_url or not audio_url:
                    raise HTTPException(
                        status_code=400, detail="Se requieren 'image_url' y 'audio_url' en content para human_scene"
                    )
                fal_webhook = content.get("fal_webhook")
                extra = {k: v for k, v in content.items() if k not in {"image_url", "audio_url", "fal_webhook"}}
                return await self.fal_client.bytedance_omnihuman(
                    image_url=image_url, audio_url=audio_url, fal_webhook=fal_webhook, **extra
                )

            raise HTTPException(status_code=400, detail="Tipo de video no soportado")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error al llamar a FAL: {str(e)}")
