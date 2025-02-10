from pydantic import BaseModel


class S3UploadRequest(BaseModel):
    file: str
    folder: str
    filename: str
