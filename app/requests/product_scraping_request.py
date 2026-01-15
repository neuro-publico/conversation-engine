from typing import Optional

from pydantic import BaseModel, HttpUrl


class ProductScrapingRequest(BaseModel):
    product_url: HttpUrl
    country: Optional[str] = "co"
