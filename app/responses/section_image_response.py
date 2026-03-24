from typing import List, Optional

from pydantic import BaseModel


class CtaButtonResponse(BaseModel):
    label: str
    coords: List[int]


class SectionImageResponse(BaseModel):
    s3_url: str
    cta_buttons: List[CtaButtonResponse] = []
