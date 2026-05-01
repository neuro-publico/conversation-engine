"""Interface for the avatar director service."""

from abc import ABC, abstractmethod

from app.requests.avatar_director_request import AvatarDirectorRequest
from app.responses.avatar_director_response import AvatarDirectorResponse


class AvatarDirectorServiceInterface(ABC):
    @abstractmethod
    async def run(self, request: AvatarDirectorRequest) -> AvatarDirectorResponse:
        """Generate one structured avatar prompt for the requested product context."""
