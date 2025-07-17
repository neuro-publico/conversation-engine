from pydantic import BaseModel
from typing import List


class BrandContextResolverRequest(BaseModel):
    websites_info: List

    @property
    def prompt(self) -> dict:
        websites_info_str = ", ".join(str(item) for item in self.websites_info)
        return {"websites_info": websites_info_str}
