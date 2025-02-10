from pydantic import BaseModel


class S3UploadResponse(BaseModel):
    s3_url: str
