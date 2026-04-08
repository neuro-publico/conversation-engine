"""Request DTO for the new ads video Director Creative pipeline."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class VideoStudioDraftRequest(BaseModel):
    """Brief that the ecommerce-service sends to start a video draft.

    The Director Creative LLM uses these fields to choose a creative pattern
    and emit the full plan (concept brief, scripts, cinematic prompts).

    Fields explicitly mapped to placeholders in the agent's system prompt:
        - product_name → {product_name}
        - product_description → {product_description}
        - language → {language}
        - duration → {duration}
        - is_combo → {is_combo}
        - sale_angle_name → {sale_angle_name}
        - sale_angle_description → {sale_angle_description}
        - target_audience_description → {target_audience_description}
        - target_audience_vibe → {target_audience_vibe}
        - user_instruction → {user_instruction}

    The agent_id defaults to `video_director_animated_v1`. Other styles will
    use other agent_ids (e.g. `video_director_sassy_v1`) once we extend the
    flow to those styles in Phase 5.
    """

    # Identification
    reference_id: str
    owner_id: str
    agent_id: str = "video_director_animated_v1"

    # Product
    product_id: Optional[str] = None
    product_name: str
    product_description: str = ""
    product_image_url: Optional[str] = None

    # Format
    language: str = "es"
    duration: int = 30
    style_id: str = "animated-problem"

    # Sales angle (opcional, viene de Narrative si existe)
    sale_angle_name: Optional[str] = None
    sale_angle_description: Optional[str] = None

    # Target audience (opcional, viene del frontend)
    target_audience_description: Optional[str] = None
    target_audience_vibe: Optional[str] = None

    # User instruction (opcional)
    user_instruction: Optional[str] = None

    # Phase 6 — Avatar config para UGC (sin uso para sassy/animated).
    # Diccionario libre con los campos del avatar wizard del frontend:
    # gender, age_range, skin_tone, hair, hair_color, vibe, setting.
    # El director Gemini de UGC los lee del template prompt vía
    # placeholders {ugc_avatar_*}. Optional para back-compat con
    # llamadas existentes de sassy/animated que NO mandan este field.
    avatar_config: Optional[Dict[str, Any]] = None

    # Async callback
    callback_url: Optional[str] = None
    callback_metadata: Optional[Dict[str, str]] = None

    @property
    def is_combo(self) -> bool:
        return self.duration == 30

    @property
    def is_ugc(self) -> bool:
        """True para los estilos que usan Seedance 2.0 (UGC + futuros)."""
        return self.style_id == "ugc-testimonial"
