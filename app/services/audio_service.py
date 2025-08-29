from typing import Any, Dict

from fastapi import Depends, HTTPException

from app.requests.generate_audio_request import GenerateAudioRequest
from app.services.audio_service_interface import AudioServiceInterface
from app.externals.fal.fal_client import FalClient


class AudioService(AudioServiceInterface):
    def __init__(self, fal_client: FalClient = Depends()):
        self.fal_client = fal_client

    async def generate_audio(self, request: GenerateAudioRequest) -> Dict[str, Any]:
        if not request.text:
            raise HTTPException(status_code=400, detail="Falta 'text'")

        content = request.content or {}
        fal_webhook = content.get("fal_webhook")
        extra = {k: v for k, v in content.items() if k not in {"fal_webhook"}}

        try:
            return await self.fal_client.tts_multilingual_v2(text=request.text, fal_webhook=fal_webhook, **extra)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error al llamar a FAL: {str(e)}") 