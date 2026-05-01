"""Interface for the scene composer service."""

from abc import ABC, abstractmethod

from app.requests.scene_composer_request import SceneComposerRequest
from app.responses.scene_composer_response import SceneComposerResponse


class SceneComposerServiceInterface(ABC):
    @abstractmethod
    async def run(self, request: SceneComposerRequest) -> SceneComposerResponse:
        """Pick the most believable filming scene for an avatar/product pair."""
