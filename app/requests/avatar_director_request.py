"""Request DTO for the Avatar Director pipeline.

The Avatar Director is an LLM-based agent that composes a narratively-coherent
JSON prompt for a single LATAM UGC avatar (hero image). It replaces the
template+random Kotlin generator — where we were shipping Frankenstein
combinations of anatomical/clothing/location pools that didn't tell one story —
with a single LLM call that uses the full product context (product, sale_angle,
audience, vibe, user_instruction) PLUS wizard choices (ancestry, personality,
setting) to write ONE person with coordinated clothing + location + identity
anchors (like the Mariana / Andrés / Valeria reference exemplars).

Output: a JSON prompt ready to pass as the `prompt` string to Gemini Nano
Banana Pro for image generation.
"""

from typing import Optional

from pydantic import BaseModel


class AvatarDirectorRequest(BaseModel):
    """Brief for a single avatar hero-image prompt.

    Mirrors the placeholders consumed by the `avatar_director_v1` agent
    system prompt. All fields optional except `agent_id` and `owner_id` —
    defaults are applied in the service when a field is blank.
    """

    # Identification
    agent_id: str = "avatar_director_v1"
    owner_id: str

    # Product context (same fields the video director already reads; passing
    # them through keeps the avatar coherent with the video brief)
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    sale_angle_name: Optional[str] = None
    sale_angle_description: Optional[str] = None
    target_audience_description: Optional[str] = None
    target_audience_vibe: Optional[str] = None
    user_instruction: Optional[str] = None
    language: str = "es"

    # Wizard choices — treat as seeds. Missing → director infers from context.
    wiz_gender: Optional[str] = None
    wiz_age_vibe: Optional[str] = None
    wiz_ancestry: Optional[str] = None
    wiz_personality: Optional[str] = None
    wiz_location_context: Optional[str] = None

    # Reproducibility. When None, the caller can re-issue the same request
    # and get a different avatar (temperature high). When set, the director
    # is asked to converge to the same output.
    seed: Optional[int] = None
