from pydantic import BaseModel, Field, validator


class DirectScrapeRequest(BaseModel):
    html: str
