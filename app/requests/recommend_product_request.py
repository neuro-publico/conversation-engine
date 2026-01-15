from typing import Dict, List, Optional

from pydantic import BaseModel


class RecommendProductRequest(BaseModel):
    product_name: str
    product_description: str
    similar: Optional[bool] = False
