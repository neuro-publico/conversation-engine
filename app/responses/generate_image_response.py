from typing import List

from pydantic import BaseModel


class GenerateImageResponse(BaseModel):
    original_url: str
    generated_urls: List[str]
    generated_prompt: str
