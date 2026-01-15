from typing import Optional

from pydantic import BaseModel, Field, validator


class VariationImageRequest(BaseModel):
    file: str
    num_variations: int = Field(default=3, ge=1, le=10)
    language: Optional[str] = "es"

    @validator("num_variations")
    def validate_variations(cls, v):
        if v > 10:
            raise ValueError("El número máximo de variaciones permitidas es 10")
        return v
