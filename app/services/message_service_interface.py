from abc import abstractmethod, ABC

from app.requests.message_request import MessageRequest
from app.requests.recommend_product_request import RecommendProductRequest


class MessageServiceInterface(ABC):
    @abstractmethod
    async def handle_message(self, request: MessageRequest):
        pass

    @abstractmethod
    async def recommend_products(self, request: RecommendProductRequest):
        pass

    async def generate_pdf(self, request):
        pass