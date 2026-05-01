"""Interface for the avatar strategist service."""

from abc import ABC, abstractmethod

from app.requests.avatar_strategist_request import AvatarStrategistRequest
from app.responses.avatar_strategist_response import AvatarStrategistResponse


class AvatarStrategistServiceInterface(ABC):
    @abstractmethod
    async def run(self, request: AvatarStrategistRequest) -> AvatarStrategistResponse:
        """Generate a recommended avatar roster for the requested product context."""
