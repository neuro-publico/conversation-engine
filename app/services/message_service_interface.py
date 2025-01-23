from abc import abstractmethod, ABC

from app.requests.message_request import MessageRequest


class MessageServiceInterface(ABC):
    @abstractmethod
    async def handle_message(self, request: MessageRequest):
        pass
