from pydantic import BaseModel
from typing import Optional


class GenerateImageRequest(BaseModel):
    file: Optional[str] = None
    prompt: str
    num_variations: int = 4
