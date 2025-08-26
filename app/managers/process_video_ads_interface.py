from abc import ABC, abstractmethod
from app.requests.generate_video_request import GenerateAdScenesRequest
from typing import Dict, Any

class ProcessVideoAdsInterface(ABC):
    @abstractmethod
    async def publish(self, request: GenerateAdScenesRequest, ad_video_id: int) -> str:
        pass

    @abstractmethod
    async def listen_forever(self) -> None:
        pass

    @abstractmethod
    async def mark_in_progress(self, ad_video_id: int) -> None:
        pass

    @abstractmethod
    async def publish_scene(self, queue_name: str, ad_video_id: int, scene: Dict[str, Any]) -> str:
        pass
