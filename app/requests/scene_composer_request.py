"""Request DTO for the Scene Composer.

Called once per draft when the caller wants to compose a preset-avatar (photo
locked) with a product. The agent picks the right setting for the product
and emits a compact scene_brief ready to feed into the image composition
prompt in the ecommerce backend.

Lightweight + fast by design — this runs on every draft, can't afford the
45-second latency of the multi-avatar strategist.
"""

from typing import Optional

from pydantic import BaseModel


class SceneComposerRequest(BaseModel):
    agent_id: str = "scene_composer_v1"
    owner_id: str

    # Product
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_image_url: Optional[str] = None

    # Preset avatar hint (the setting the preset was created with)
    preset_setting_key: Optional[str] = None

    # Optional marketing context
    sale_angle_name: Optional[str] = None
    target_audience_description: Optional[str] = None

    language: str = "es"
