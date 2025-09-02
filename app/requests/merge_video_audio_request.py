from pydantic import BaseModel

class MergeVideoAudioRequest(BaseModel):
    video_url: str
    audio_url: str
    folder: str
    filename: str
    