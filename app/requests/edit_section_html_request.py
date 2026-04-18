from typing import Dict, List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class EditSectionHtmlRequest(BaseModel):
    """Request to edit an existing HTML section via chat instruction."""

    # Current section HTML
    current_html: str

    # User's edit instruction
    instruction: str

    # Product context
    product_name: str
    product_description: str = "Product"

    # Conversation history for multi-turn
    conversation_history: Optional[List[ChatMessage]] = None

    # Style
    style_variables: Optional[Dict[str, str]] = None
    brand_colors: Optional[List[str]] = None

    # Image generation context (used when the edit introduces new placehold.co
    # images — passed through to the orchestrator + sub-image generator so
    # new images stay coherent with the template/funnel style).
    product_image_url: Optional[str] = None
    product_images: Optional[List[str]] = None
    image_instructions: Optional[str] = None
    sale_angle_name: Optional[str] = None

    # Language
    language: str = "es"

    # Tracking
    owner_id: str


class TemplateGenerateRequest(BaseModel):
    """Request for the Template Studio: create/iterate template HTML via chat."""

    instruction: str
    conversation_history: Optional[List[ChatMessage]] = None
