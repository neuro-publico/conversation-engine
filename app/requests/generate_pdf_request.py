from pydantic import BaseModel
from typing import Optional


class GeneratePdfRequest(BaseModel):
    product_id: str
    product_name: str
    product_description: str
    language: str
    owner_id: str
    image_url: str
    title: str
    content: str
    force: Optional[bool] = False
