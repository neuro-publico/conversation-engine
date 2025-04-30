from typing import List, Optional

from pydantic import BaseModel

from app.externals.google_vision.responses.vision_analysis_response import VisionAnalysisResponse


class GenerateImageResponse(BaseModel):
    original_url: Optional[str]
    original_urls: Optional[list[str]]
    generated_urls: List[str]
    generated_prompt: str
    vision_analysis: Optional[VisionAnalysisResponse] = None
