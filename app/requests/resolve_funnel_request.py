from pydantic import BaseModel
from typing import Optional


class ResolveFunnelRequest(BaseModel):
    product_name: str
    product_description: str
    language: Optional[str] = "es" 