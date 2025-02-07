import httpx
from app.configurations.config import S3_UPLOAD_API
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.responses.s3_upload_response import S3UploadResponse


async def upload_file(request: S3UploadRequest) -> S3UploadResponse:
    headers = {
        'Content-Type': 'application/json',
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            S3_UPLOAD_API,
            headers=headers,
            json=request.dict()
        )
        response.raise_for_status()

        return S3UploadResponse(**response.json())
