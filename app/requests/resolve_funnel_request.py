from pydantic import BaseModel


class ResolveFunnelRequest(BaseModel):
    product_name: str
    product_description: str 