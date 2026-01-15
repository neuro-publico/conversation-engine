from typing import Optional

from pydantic import BaseModel


class AliexpressSearchRequest(BaseModel):
    q: str
    page: Optional[int] = 1
    sort: Optional[str] = "default"
