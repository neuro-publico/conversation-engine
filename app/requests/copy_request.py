from pydantic import BaseModel, Field, validator


class CopyRequest(BaseModel):
    prompt: str
