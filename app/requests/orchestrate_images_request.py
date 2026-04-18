from typing import List, Optional

from pydantic import BaseModel


class OrchestrateImagesRequest(BaseModel):
    """Analyze HTML and generate coherent image prompts for all placeholder images."""

    html_content: str
    image_instructions: Optional[str] = None

    # Product context
    product_name: str
    product_description: str = "Product"
    product_image_url: Optional[str] = None
    sale_angle_name: Optional[str] = None
    language: str = "es"

    owner_id: str


class OrchestratedImagePrompt(BaseModel):
    prompt: str
    aspect_ratio: str = "1:1"


class OrchestrateImagesResponse(BaseModel):
    prompts: List[OrchestratedImagePrompt]
