from abc import ABC, abstractmethod
from app.requests.generate_video_request import GenerateAdScenesRequest
from typing import Dict, Any

class ProcessVideoAdsInterface(ABC):
    @abstractmethod
    async def handle_human_scene(self, scene: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def handle_animated_scene(self, scene: Dict[str, Any]) -> None:
        pass