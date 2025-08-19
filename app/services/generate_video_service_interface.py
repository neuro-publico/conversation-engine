from abc import ABC, abstractmethod
from app.requests.generate_video_request import GenerateVideoRequest, GenerateAdScenesRequest
from typing import Any, Optional


class GenerateVideoServiceInterface(ABC):
	@abstractmethod
	async def generate_ad_video(self, request: GenerateAdScenesRequest, owner_id: str) -> dict[str, Any]:
		...

	@abstractmethod
	async def list_ad_videos(self, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
		...

	@abstractmethod
	async def get_ad_video(self, ad_video_id: int) -> Optional[dict[str, Any]]:
		...

	@abstractmethod
	async def update_ad_video(self, ad_video_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
		...
