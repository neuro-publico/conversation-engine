from pydantic import BaseModel, HttpUrl
from typing import Optional


class ProductScrapingRequest(BaseModel):
    product_url: HttpUrl
    country: Optional[str] = "co"
