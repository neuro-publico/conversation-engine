from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AdsListenerInterface(ABC):
	@abstractmethod
	async def listen_forever(self) -> None:
		pass

	@abstractmethod
	async def handle_human_scene(self, scene: Dict[str, Any]) -> None:
		pass

	@abstractmethod
	async def handle_animated_scene(self, scene: Dict[str, Any]) -> None:
		pass 