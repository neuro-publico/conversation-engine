from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel

class VideoType(str, Enum):
    human_scene = "human_scene"
    animated_scene = "animated_scene"

class GenerateVideoRequest(BaseModel):
    type: VideoType
    content: Optional[Dict[str, Any]] = None
