from pydantic import BaseModel
from typing import Optional, Dict, Any


class GenerateAudioRequest(BaseModel):
    text: str
    content: Optional[Dict[str, Any]] = None 