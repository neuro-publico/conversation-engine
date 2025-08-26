from app.services.generate_video_service_interface import GenerateVideoServiceInterface
from app.requests.generate_video_request import GenerateVideoRequest, GenerateAdScenesRequest
import json
from typing import Any, Optional

from app.repositories.ad_video_repository import AdVideoRepository
from app.db import init_models
from app.managers.process_video_ads import ProcessVideoAds
from app.services.message_service import MessageService
from app.requests.message_request import MessageRequest
from fastapi import Depends
from app.services.message_service_interface import MessageServiceInterface
from app.managers.process_video_ads_interface import ProcessVideoAdsInterface
from app.repositories.ad_video_repository_interface import AdVideoRepositoryInterface

class GenerateVideoService(GenerateVideoServiceInterface):
    def __init__(self, repository: AdVideoRepositoryInterface = Depends(AdVideoRepository), process_manager: ProcessVideoAdsInterface = Depends(ProcessVideoAds), message_service: MessageServiceInterface = Depends(MessageService)): 
        self.repository = repository
        self.process_manager = process_manager
        self.message_service = message_service
        
        
    # Repository-backed methods
    async def generate_ad_video(self, request: GenerateAdScenesRequest, owner_id: str) -> dict[str, Any]:
        await init_models()

        msg_request = MessageRequest(
            query=".",
            agent_id="ad_scene",
            parameter_prompt={
                "ad_text": request.ad_text
            },
            json_parser={
                "sort": "number",
                "type": "string",
                "content": {
                    "dialogue": "string",
                    "image": "string",
                    "prompt": "string"
                }
            },
            conversation_id="",
            metadata_filter=None
        )

        # Get scenes from AI
        scenes = await self.message_service.handle_message_json(msg_request)

        # Persist video record
        video_info = await self.repository.create_ad_video(request, owner_id)
        ad_video_id = video_info["id"]

        # Classify and enqueue scenes
        for scene in scenes or []:
            scene_type = (scene or {}).get("type")
            if scene_type == "human_scene":
                queue = "generate_human_video"
            elif scene_type == "animated_scene":
                queue = "generate_animated_image_video"
            else:
                continue
            await self.process_manager.publish_scene(queue, ad_video_id, scene)

        return {"status": "ENQUEUED", "ad_video_id": ad_video_id, "message_result": scenes}

    async def list_ad_videos(self, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
        return await self.repository.list_ad_videos(owner_id)

    async def get_ad_video(self, ad_video_id: int) -> Optional[dict[str, Any]]:
        return await self.repository.get_ad_video(ad_video_id)

    async def update_ad_video(self, ad_video_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        return await self.repository.update_ad_video(ad_video_id, data)