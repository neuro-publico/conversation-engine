from typing import Optional

from pydantic import BaseModel


class SectionImageRequest(BaseModel):
    product_name: str
    product_description: str = "Product"
    language: str = "es"
    product_image_url: str
    template_image_url: Optional[str] = None
    image_format: str = "9:16"
    price: Optional[float] = None
    price_fake: Optional[float] = None
    user_prompt: Optional[str] = None
    user_instructions: Optional[str] = None
    detect_cta_buttons: bool = True
    owner_id: str
    target_kb: int = 500
