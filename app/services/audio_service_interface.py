from abc import ABC, abstractmethod

from app.requests.generate_audio_request import GenerateAudioRequest


class AudioServiceInterface(ABC):
    @abstractmethod
    async def generate_audio(self, request: GenerateAudioRequest):
        pass 