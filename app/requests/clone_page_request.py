from pydantic import BaseModel, HttpUrl


class ClonePageRequest(BaseModel):
    url: HttpUrl
