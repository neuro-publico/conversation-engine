from abc import ABC, abstractmethod
from typing import Any


class AdsProducerInterface(ABC):
	@abstractmethod
	async def publish_scene(self, queue_name: str, ad_video_id: int, scene: dict[str, Any]) -> str:
		pass

	@abstractmethod
	def get_or_create_queue_url(self, queue_name: str) -> str:
		pass 