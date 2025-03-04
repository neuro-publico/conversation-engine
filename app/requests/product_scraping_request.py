from pydantic import BaseModel, HttpUrl


class ProductScrapingRequest(BaseModel):
    product_url: HttpUrl
