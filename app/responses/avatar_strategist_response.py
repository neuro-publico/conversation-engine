"""Response DTO for the Avatar Strategist.

Returns the product analysis + a roster of N avatar entries, each with its
sales angle, a suggested dialogue line, and the full ``prompt_json`` ready
to hand to the image model.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AvatarEntry(BaseModel):
    angle_name: str
    angle_category: Optional[str] = None
    angle_description: Optional[str] = None
    suggested_dialogue_line: Optional[str] = None
    target_viewer_segment: Optional[str] = None
    prompt_json: Dict[str, Any]


class AvatarStrategistResponse(BaseModel):
    product_analysis: Optional[Dict[str, Any]] = None
    avatars: List[AvatarEntry]

    # Observability
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    elapsed_ms: Optional[int] = None
    model_used: Optional[str] = None
