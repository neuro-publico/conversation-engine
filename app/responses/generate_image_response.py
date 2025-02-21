from typing import List

from pydantic import BaseModel

from app.externals.google_vision.responses.vision_analysis_response import VisionAnalysisResponse


class GenerateImageResponse(BaseModel):
    original_url: str
    generated_urls: List[str]
    generated_prompt: str
    vision_analysis: VisionAnalysisResponse
