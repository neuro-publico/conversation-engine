from typing import List, Optional

from pydantic import BaseModel


class SubImageItem(BaseModel):
    """A single image to generate within a section."""

    id: str  # Reference ID (e.g., "benefit_1_image")
    prompt: str  # Image generation prompt
    aspect_ratio: str = "1:1"
    context: Optional[str] = None  # Additional context (e.g., benefit text)


class GenerateSubImagesRequest(BaseModel):
    """Request to generate multiple sub-images for an HTML section."""

    images: List[SubImageItem]

    # Product reference
    product_name: str
    product_description: str = "Product"
    product_image_url: Optional[str] = None
    product_images: Optional[List[str]] = None

    # Context
    language: str = "es"
    sale_angle_name: Optional[str] = None
    brand_colors: Optional[List[str]] = None

    # Tracking
    owner_id: str
