from pydantic import BaseModel

class MergeVideosRequest(BaseModel):
    video_urls: list[str]
    folder: str
    filename: str
    