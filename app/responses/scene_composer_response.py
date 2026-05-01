"""Response DTO for the Scene Composer."""

from typing import Optional

from pydantic import BaseModel


class SceneComposerResponse(BaseModel):
    setting_key: str
    override_reason: Optional[str] = None
    scene_brief: str
    # Phase 6 V4h (Apr 22 2026) — outfit adaptation: when the preset's
    # original clothing (e.g. a casual student hoodie) doesn't fit the
    # product's scene (e.g. gym context), the composer emits an outfit
    # override that the ecommerce backend injects into the composition
    # prompt with explicit "keep face/hair/identity markers, adapt only
    # clothing" instructions. Optional — when ``outfit_changed_vs_preset``
    # is false the preset clothing is preserved as-is.
    outfit_description: Optional[str] = None
    outfit_changed_vs_preset: Optional[bool] = None
    negative_add: Optional[str] = None

    # Observability
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    elapsed_ms: Optional[int] = None
    model_used: Optional[str] = None
