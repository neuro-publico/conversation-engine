"""Request DTO for the Avatar Strategist pipeline.

The Strategist is a one-shot agent that takes a product + its sales/audience
context and returns a multi-avatar campaign roster. Each avatar in the roster
is tied to a distinct sales angle (authority / identification / expertise /
etc — angles are SYNTHESIZED by the LLM, not picked from a fixed menu) and
carries its own fully-composed JSON prompt ready for Gemini Image or gpt-image-2.

Replaces the single-avatar ``avatar_director_v1`` when the caller wants a
ready-to-A/B-test campaign roster instead of one library entry.
"""

from typing import Optional

from pydantic import BaseModel


class AvatarStrategistRequest(BaseModel):
    """Brief for a multi-avatar campaign roster.

    All fields optional except ``owner_id`` — the strategist degrades
    gracefully when the caller only supplies the bare minimum (product_name
    + product_description). Richer context → sharper casting.
    """

    # Identification
    agent_id: str = "avatar_strategist_v1"
    owner_id: str

    # Product core (required in practice for useful output)
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_image_url: Optional[str] = None  # optionally passed multi-modal

    # Marketing brief (best-effort — strategist infers when missing)
    sale_angle_name: Optional[str] = None
    sale_angle_description: Optional[str] = None
    target_audience_description: Optional[str] = None
    target_audience_vibe: Optional[str] = None
    user_instruction: Optional[str] = None

    # Format / roster
    language: str = "es"
    num_variants: int = 3  # 2..6 reasonable; default 3 matches the manual reference test

    # Owner context (optional — lets the strategist pick region-appropriate ancestries)
    owner_country: Optional[str] = None
    owner_niche: Optional[str] = None

    seed: Optional[int] = None
