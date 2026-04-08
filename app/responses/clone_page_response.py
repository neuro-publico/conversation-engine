from typing import List, Optional

from pydantic import BaseModel


class ClonePageMetadata(BaseModel):
    original_url: str
    title: Optional[str] = None
    colors: List[str] = []
    fonts: List[str] = []


class ClonePageResponse(BaseModel):
    html: str
    images: List[str] = []
    metadata: ClonePageMetadata
