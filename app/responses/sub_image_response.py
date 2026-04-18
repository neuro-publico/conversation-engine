from typing import Dict

from pydantic import BaseModel


class GenerateSubImagesResponse(BaseModel):
    """Maps image IDs to their generated S3 URLs."""

    images: Dict[str, str]  # { "benefit_1_image": "https://s3.../abc.jpg", ... }
    errors: Dict[str, str] = {}  # { "benefit_3_image": "Gemini rate limit" } if any failed
