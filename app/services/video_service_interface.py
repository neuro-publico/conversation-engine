from abc import ABC, abstractmethod

from app.requests.generate_video_request import GenerateVideoRequest


class VideoServiceInterface(ABC):
    @abstractmethod
    async def generate_video(self, request: GenerateVideoRequest):
        pass
