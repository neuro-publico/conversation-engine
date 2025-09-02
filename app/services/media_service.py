import base64
import tempfile
from io import BytesIO
from moviepy.editor import VideoFileClip, AudioFileClip
from app.services.media_service_interface import MediaServiceInterface
from app.externals.s3_upload.s3_upload_client import upload_file
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from moviepy.editor import VideoFileClip, concatenate_videoclips


class MediaService(MediaServiceInterface):
    def __init__(self):
        pass
    

    def merge_video_audio(self, video_path: str, audio_path: str) -> str:

        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)

        audio = audio.subclip(0, video.duration)

        final_video = video.set_audio(audio)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as temp_file:
            final_video.write_videofile(
                temp_file.name,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )
            
            temp_file.seek(0)
            video_bytes = temp_file.read()

        video_base64 = base64.b64encode(video_bytes).decode("utf-8")

        return video_base64
    

    

    async def merge_video_audio_and_upload(self, video_path: str, audio_path: str, folder: str, filename: str) -> str:
        """
        Une video + audio, sube el resultado a S3 y devuelve el s3_url.
        """
        video_base64 = self.merge_video_audio(video_path, audio_path)
        result = await upload_file(
            S3UploadRequest(
                file=video_base64,
                folder=folder,
                filename=filename
            )
        )
        return result.s3_url
    
    def merge_videos(self, video_paths: list[str]) -> str:
        clips = [VideoFileClip(path) for path in video_paths]

        final_video = concatenate_videoclips(clips, method="compose")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as temp_file:
            final_video.write_videofile(
                temp_file.name,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )
            
            temp_file.seek(0)
            video_bytes = temp_file.read()

        video_base64 = base64.b64encode(video_bytes).decode("utf-8")

        return video_base64
    
    async def merge_videos_and_upload(self, video_paths: list[str], folder: str, filename: str) -> str:
        video_base64 = self.merge_videos(video_paths)
        result = await upload_file(
            S3UploadRequest(
                file=video_base64,
                folder=folder,
                filename=filename
            )
        )
        return result.s3_url   