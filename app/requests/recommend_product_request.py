from pydantic import BaseModel
from typing import Optional, List, Dict


class RecommendProductRequest(BaseModel):
    product_name: str
    product_description: str
    similar: Optional[bool] = False