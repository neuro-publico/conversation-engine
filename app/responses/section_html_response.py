from pydantic import BaseModel


class SectionHtmlResponse(BaseModel):
    html_content: str
    model_used: str = ""
