from typing import Any, Dict, Optional

from pydantic import BaseModel


class GenerateAudioRequest(BaseModel):
    text: str
    content: Optional[Dict[str, Any]] = None
