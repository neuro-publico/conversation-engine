from app.services.generate_video_service_interface import GenerateVideoServiceInterface
from app.requests.generate_video_request import GenerateVideoRequest, GenerateAdScenesRequest
import json
from typing import Any, Optional

from app.repositories.ad_video_repository import AdVideoRepository
from app.db import init_models
from app.managers.process_video_ads import ProcessVideoAds


class GenerateVideoService(GenerateVideoServiceInterface):
    def __init__(self):
        self.repository = AdVideoRepository()
        self.process_manager = ProcessVideoAds()
        
    # Repository-backed methods
    async def generate_ad_video(self, request: GenerateAdScenesRequest, owner_id: str) -> dict[str, Any]:
        await init_models()
        print("generate_ad_video_service")
        videoInfo = await self.repository.create_ad_video(request, owner_id)
        # Publisher: encola el trabajo
        await self.process_manager.publish(request, videoInfo["id"])
        return videoInfo

    async def list_ad_videos(self, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
        return await self.repository.list_ad_videos(owner_id)

    async def get_ad_video(self, ad_video_id: int) -> Optional[dict[str, Any]]:
        return await self.repository.get_ad_video(ad_video_id)

    async def update_ad_video(self, ad_video_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        return await self.repository.update_ad_video(ad_video_id, data)