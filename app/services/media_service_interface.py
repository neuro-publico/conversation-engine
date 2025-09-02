from abc import abstractmethod, ABC


class MediaServiceInterface(ABC):
    @abstractmethod
    def merge_video_audio(self, video_path: str, audio_path: str) -> str:
        pass

    @abstractmethod
    async def merge_video_audio_and_upload(self, video_path: str, audio_path: str, folder: str, filename: str) -> str:
        pass

    @abstractmethod
    def merge_videos(self, video_paths: list[str]) -> str:
        pass

    @abstractmethod
    async def merge_videos_and_upload(self, video_paths: list[str], folder: str, filename: str) -> str:
        pass