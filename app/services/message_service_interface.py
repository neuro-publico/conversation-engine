from abc import abstractmethod, ABC

from app.requests.copy_request import CopyRequest
from app.requests.message_request import MessageRequest
from app.requests.recommend_product_request import RecommendProductRequest
from app.requests.resolve_funnel_request import ResolveFunnelRequest
from app.requests.brand_context_resolver_request import BrandContextResolverRequest


class MessageServiceInterface(ABC):
    @abstractmethod
    async def handle_message(self, request: MessageRequest):
        pass

    @abstractmethod
    async def handle_message_json(self, request: MessageRequest):
        pass

    @abstractmethod
    async def generate_copies(self, request: CopyRequest):
        pass

    @abstractmethod
    async def recommend_products(self, request: RecommendProductRequest):
        pass

    async def generate_pdf(self, request):
        pass

    @abstractmethod
    async def resolve_funnel(self, request: ResolveFunnelRequest):
        pass

    @abstractmethod
    async def resolve_brand_context(self, request: BrandContextResolverRequest):
        pass

    @abstractmethod
    async def handle_message_with_config(self, request: MessageRequest):
        pass