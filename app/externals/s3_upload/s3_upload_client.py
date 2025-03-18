import httpx
from app.configurations.config import S3_UPLOAD_API
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.externals.s3_upload.responses.s3_upload_response import S3UploadResponse


async def upload_file(request: S3UploadRequest) -> S3UploadResponse:
    headers = {
        "Content-Type": "application/json"
    }
    
    # Configuración de tiempos de espera más largos (3 minutos)
    timeout = httpx.Timeout(timeout=180.0, connect=60.0)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                S3_UPLOAD_API,
                headers=headers,
                json=request.dict()
            )
            response.raise_for_status()
            return S3UploadResponse(**response.json())
    except Exception as e:
        print(f"Error al cargar archivo a S3: {str(e)}")
        raise Exception(f"Error al cargar archivo a S3: {str(e)}")
