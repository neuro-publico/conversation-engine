from abc import abstractmethod, ABC

from app.requests.variation_image_request import VariationImageRequest


class ImageServiceInterface(ABC):
    @abstractmethod
    async def generate_variation_images(self, request: VariationImageRequest, owner_id: str):
        pass
