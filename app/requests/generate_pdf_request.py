from pydantic import BaseModel


class GeneratePdfRequest(BaseModel):
    product_id: str
    product_name: str
    product_description: str
    language: str
    owner_id: str
