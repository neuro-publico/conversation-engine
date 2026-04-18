from typing import Dict, List, Optional

from pydantic import BaseModel


class SectionHtmlRequest(BaseModel):
    """Request to generate a new HTML section from a template + product data."""

    # Product
    product_name: str
    product_description: str = "Product"
    product_image_url: Optional[str] = None
    product_images: Optional[List[str]] = None

    # Pricing
    price: Optional[float] = None
    price_fake: Optional[float] = None
    price_formatted: Optional[str] = None
    price_fake_formatted: Optional[str] = None

    # Sales angle
    sale_angle_name: Optional[str] = None
    sale_angle_description: Optional[str] = None

    # Template & style
    template_html: Optional[str] = None
    content_rules: Optional[str] = None
    template_notes: Optional[str] = None
    copy_prompt: Optional[str] = None
    style_variables: Optional[Dict[str, str]] = None
    section_role: Optional[str] = None

    # Brand colors
    brand_colors: Optional[List[str]] = None

    # Language
    language: str = "es"

    # Product context (consolidated product info document)
    context: Optional[str] = None

    # Extra instructions
    user_instructions: Optional[str] = None

    # Tracking
    owner_id: str
