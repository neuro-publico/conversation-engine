from pydantic import BaseModel
from typing import List, Any, Optional, Dict


class GenerateAdScenesRequest(BaseModel):
    ad_text: str
    funnel_id: str

    @property
    def prompt(self) -> dict:
        return {"ad_text": self.ad_text}

class GenerateVideoRequest(BaseModel):
    ad_scenes: List[Any] | None = None
    input: Optional[Dict[str, Any]] = None
    scenes: Optional[List[Dict[str, Any]]] = None

    @property
    def prompt(self) -> dict:
        ad_scenes = self.ad_scenes
        if not ad_scenes and self.input and isinstance(self.input.get("scenes"), list):
            ad_scenes = self.input["scenes"]
        if not ad_scenes and isinstance(self.scenes, list):
            ad_scenes = self.scenes
        ad_scenes_str = ", ".join(str(item) for item in (ad_scenes or []))
        return {"ad_scenes": ad_scenes_str}
