from typing import Any, Dict, Optional

from pydantic import BaseModel


class GenerateImageRequest(BaseModel):
    file: Optional[str] = None
    file_url: Optional[str] = None
    file_urls: Optional[list[str]] = None
    owner_id: Optional[str] = None
    prompt: Optional[str] = None
    agent_id: Optional[str] = None
    provider: Optional[str] = None
    model_ai: Optional[str] = None
    num_variations: int = 4
    parameter_prompt: Optional[Dict[str, Any]] = None
    extra_parameters: Optional[Dict[str, Any]] = None
    language: Optional[str] = "es"
