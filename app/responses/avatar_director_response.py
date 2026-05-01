"""Response DTO for the Avatar Director pipeline.

Returns the full avatar prompt JSON (loose typed as ``Dict[str, Any]`` so
the ecommerce backend can pass it verbatim to Gemini Nano Banana Pro
without re-parsing). Includes metadata for auditing + reproducibility.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class AvatarDirectorResponse(BaseModel):
    """Director output.

    ``prompt_json`` is the object that must be ``json.dumps``-ed and sent
    to the image model as the prompt. ``prompt_text`` is a human-readable
    string summary (optional, for logs/debug).
    """

    # The JSON the image model consumes. Loose typed because schema is
    # enforced upstream (Gemini response schema) and downstream consumers
    # serialize it directly.
    prompt_json: Dict[str, Any]

    # Metadata for debugging + analytics.
    selected_identity_name: Optional[str] = None
    selected_ancestry_label: Optional[str] = None
    selected_location_summary: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    elapsed_ms: Optional[int] = None
    seed_used: Optional[int] = None
    model_used: Optional[str] = None
