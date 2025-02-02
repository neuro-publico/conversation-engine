from typing import List

from pydantic import BaseModel


class RecommendProductResponse(BaseModel):
    ai_response: dict
    products: List[dict]
