from abc import ABC, abstractmethod
from typing import Any, Optional
from app.models.ad import AdVideo


class AdVideoRepositoryInterface(ABC):
	@abstractmethod
	async def create_ad_video(self, model: AdVideo) -> dict[str, Any]:
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