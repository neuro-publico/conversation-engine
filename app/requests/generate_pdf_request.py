from pydantic import BaseModel


class GeneratePdfRequest(BaseModel):
    product_name: str
    product_description: str
    owner_id: str