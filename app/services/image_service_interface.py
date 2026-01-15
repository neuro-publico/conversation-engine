from abc import ABC, abstractmethod

from app.requests.generate_image_request import GenerateImageRequest
from app.requests.variation_image_request import VariationImageRequest


class ImageServiceInterface(ABC):
    @abstractmethod
    async def generate_variation_images(self, request: VariationImageRequest, owner_id: str):
        pass

    @abstractmethod
    async def generate_images_from(self, request: GenerateImageRequest, owner_id: str):
        pass

    async def generate_images_from_agent(self, generate_image_request, owner_id):
        pass
