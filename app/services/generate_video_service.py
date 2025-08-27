from app.services.generate_video_service_interface import GenerateVideoServiceInterface
from app.requests.generate_video_request import GenerateVideoRequest, GenerateAdScenesRequest
import json
from typing import Any, Optional

from app.repositories.ad_video_repository import AdVideoRepository
from app.db import init_models
from app.services.message_service import MessageService
from app.requests.message_request import MessageRequest
from app.models.ad import AdVideo
from fastapi import Depends
from app.services.message_service_interface import MessageServiceInterface
from app.managers.process_video_ads_interface import ProcessVideoAdsInterface
from app.repositories.ad_video_repository_interface import AdVideoRepositoryInterface
from app.mappers.ad_video_mapper import map_request_to_ad_video
from app.producers.ads_producer_interface import AdsProducerInterface
from app.producers.ads_producer import AdsProducer

class GenerateVideoService(GenerateVideoServiceInterface):
    def __init__(self, repository: AdVideoRepositoryInterface = Depends(AdVideoRepository), ads_producer: AdsProducerInterface = Depends(AdsProducer), message_service: MessageServiceInterface = Depends(MessageService)): 
        self.repository = repository
        self.ads_producer = ads_producer
        self.message_service = message_service
        
    async def generate_ad_video(self, request: GenerateAdScenesRequest, owner_id: str) -> dict[str, Any]:
        await init_models()
        scenes = await self._build_scenes(request)
        ad_video_id = await self._persist_ad_video_and_get_id(request, owner_id, scenes)
        await self._enqueue_scenes(ad_video_id, scenes)
        return {"status": "ENQUEUED", "ad_video_id": ad_video_id, "scenes": scenes}

    # Repository-backed methods
    async def list_ad_videos(self, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
        return await self.repository.list_ad_videos(owner_id)

    async def get_ad_video(self, ad_video_id: int) -> Optional[dict[str, Any]]:
        return await self.repository.get_ad_video(ad_video_id)

    async def update_ad_video(self, ad_video_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        return await self.repository.update_ad_video(ad_video_id, data)
    
    async def create_ad_video(self, model: AdVideo) -> dict[str, Any]:
        return await self.repository.create_ad_video(model)
    
    # Helpers privados
    async def _build_scenes(self, request: GenerateAdScenesRequest) -> list[dict[str, Any]]:
        return await self.get_scenes(request.ad_text)

    async def _persist_ad_video_and_get_id(self, request: GenerateAdScenesRequest, owner_id: str, scenes: list[dict[str, Any]]) -> int:
        model = map_request_to_ad_video(request, owner_id, scenes)
        video_info = await self.create_ad_video(model)
        return int(video_info["id"])

    async def _enqueue_scenes(self, ad_video_id: int, scenes: list[dict[str, Any]]) -> None:
        for scene in scenes or []:
            scene_type = (scene or {}).get("type")
            if scene_type == "human_scene":
                queue = "generate_human_video"
            elif scene_type == "animated_scene":
                queue = "generate_animated_image_video"
            else:
                continue
            await self.ads_producer.publish_scene(queue, ad_video_id, scene)

    async def get_scenes(self, ad_text: str) -> list[dict[str, Any]]:
        msg_request = MessageRequest(
            query=".",
            agent_id="ad_scene",
            parameter_prompt={
                "ad_text": ad_text
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

        return await self.message_service.handle_message_json(msg_request)