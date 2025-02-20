from app.configurations.config import (
    AGENT_IMAGE_VARIATIONS,
    STABILITY_API_KEY,
    STABILITY_API_URL
)
from app.externals.s3_upload.responses.s3_upload_response import S3UploadResponse
from app.requests.message_request import MessageRequest
from app.requests.variation_image_request import VariationImageRequest
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.responses.generate_image_response import GenerateImageResponse
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service_interface import MessageServiceInterface
from app.externals.s3_upload.s3_upload_client import upload_file
from fastapi import Depends
import asyncio
import aiohttp
import base64
import uuid
from dotenv import load_dotenv

load_dotenv()


class ImageService(ImageServiceInterface):
    def __init__(self, message_service: MessageServiceInterface = Depends()):
        self.message_service = message_service
        self.stability_api_key = STABILITY_API_KEY
        self.stability_api_url = STABILITY_API_URL

    async def _upload_to_s3(self, image_base64: str, index: int, owner_id: str) -> S3UploadResponse:
        unique_id = uuid.uuid4().hex[:8]
        file_name = f"variation_{index}_{unique_id}"

        return await upload_file(
            S3UploadRequest(
                file=image_base64,
                folder=f"{owner_id}/products/variations",
                filename=file_name
            )
        )

    async def _generate_single_variation(self, image_base64: str, prompt: str, negative_prompt: str, index: int,
                                         owner_id: str) -> str:
        image_bytes = base64.b64decode(image_base64)
        form_data = aiohttp.FormData()
        form_data.add_field('image',
                            image_bytes,
                            filename='image.jpg',
                            content_type='image/jpeg')
        form_data.add_field('prompt', prompt)
        form_data.add_field('negative_prompt', negative_prompt)
        form_data.add_field('fidelity', '1.0')
        form_data.add_field('control_strength', '1.0')
        form_data.add_field('output_format', 'webp')

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    self.stability_api_url,
                    headers={
                        "Authorization": f"Bearer {self.stability_api_key}",
                        "accept": "image/*"
                    },
                    data=form_data
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    content_base64 = base64.b64encode(content).decode('utf-8')
                    response = await self._upload_to_s3(content_base64, index, owner_id)
                    return response.s3_url
                else:
                    raise Exception(f"Error {response.status}: {await response.text()}")

    async def generate_variation_images(self, request: VariationImageRequest, owner_id: str):
        original_image_response = await self._upload_to_s3(request.file, 0, owner_id)

        message_request = MessageRequest(
            query="Attached is the product image.",
            agent_id=AGENT_IMAGE_VARIATIONS,
            conversation_id="",
            files=[{
                "type": "image",
                "url": original_image_response.s3_url,
                "content": request.file
            }]
        )

        response = await self.message_service.handle_message(message_request)
        prompt = response["text"]
        negative_prompt = "text, letters, brand logos, brand names, symbols"
        tasks = [
            self._generate_single_variation(request.file, prompt, negative_prompt, i, owner_id)
            for i in range(request.num_variations)
        ]
        generated_urls = await asyncio.gather(*tasks)

        return GenerateImageResponse(generated_urls=generated_urls, original_url=original_image_response.s3_url,
                                     generated_prompt=prompt)
