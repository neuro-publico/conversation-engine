from abc import ABC, abstractmethod

from app.requests.clone_page_request import ClonePageRequest
from app.responses.clone_page_response import ClonePageResponse


class ClonePageServiceInterface(ABC):
    @abstractmethod
    async def clone_page(self, request: ClonePageRequest) -> ClonePageResponse:
        pass
