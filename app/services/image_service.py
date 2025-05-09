from app.configurations.config import (
    AGENT_IMAGE_VARIATIONS,
)
from app.externals.agent_config.requests.agent_config_request import AgentConfigRequest
from app.externals.s3_upload.responses.s3_upload_response import S3UploadResponse
from app.requests.generate_image_request import GenerateImageRequest
from app.requests.message_request import MessageRequest
from app.requests.variation_image_request import VariationImageRequest
from app.externals.s3_upload.requests.s3_upload_request import S3UploadRequest
from app.responses.generate_image_response import GenerateImageResponse
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service_interface import MessageServiceInterface
from app.externals.s3_upload.s3_upload_client import upload_file
from fastapi import Depends
import asyncio
import uuid
from dotenv import load_dotenv
from app.externals.google_vision.google_vision_client import analyze_image
from app.externals.images.image_client import openai_image_edit
from typing import Optional
import base64
import io
from PIL import Image

load_dotenv()


class ImageService(ImageServiceInterface):
    def __init__(self, message_service: MessageServiceInterface = Depends()):
        self.message_service = message_service

    async def _upload_to_s3(self, image_base64: str, owner_id: str, folder_id: str,
                            prefix_name: str) -> S3UploadResponse:
        unique_id = uuid.uuid4().hex[:8]
        file_name = f"{prefix_name}_{unique_id}"
        original_image_bytes = base64.b64decode(image_base64)
        image_base64_high, image_base64_low = self._process_image_for_upload(original_image_bytes)

        await upload_file(
            S3UploadRequest(
                file=image_base64_high,
                folder=f"{owner_id}/products/variations/{folder_id}/high",
                filename=file_name
            )
        )

        return await upload_file(
            S3UploadRequest(
                file=image_base64_low,
                folder=f"{owner_id}/products/variations/{folder_id}/low",
                filename=file_name
            )
        )

    def _process_image_for_upload(self, original_image_bytes: bytes) -> tuple[str, str]:
        img = Image.open(io.BytesIO(original_image_bytes))

        if img.mode in ("RGBA", "P"):
            img_converted = img.convert("RGBA")
        else:
            img_converted = img.convert("RGB")

        high_output_buffer = io.BytesIO()
        img_converted.save(high_output_buffer, format='WEBP')
        image_base64_high = base64.b64encode(high_output_buffer.getvalue()).decode('utf-8')

        original_width, original_height = img_converted.size
        new_width = int(original_width * 0.60)
        new_height = int(original_height * 0.60)
        new_width = max(1, new_width)
        new_height = max(1, new_height)

        resized_img = img_converted.resize((new_width, new_height))

        temp_buffer_quality_100 = io.BytesIO()
        resized_img.save(temp_buffer_quality_100, format='WEBP')
        bytes_quality_100 = temp_buffer_quality_100.getvalue()
        size_kb_quality_100 = len(bytes_quality_100) / 1024

        final_low_image_bytes = bytes_quality_100
        if size_kb_quality_100 > 150:
            print("al pelosdasdasdas")
            final_low_buffer_quality_80 = io.BytesIO()
            resized_img.save(final_low_buffer_quality_80, format='WEBP', quality=80)
            final_low_image_bytes = final_low_buffer_quality_80.getvalue()

        image_base64_low = base64.b64encode(final_low_image_bytes).decode('utf-8')

        return image_base64_high, image_base64_low


    async def _generate_single_variation(self, url_images: list[str], prompt: str, owner_id: str,
                                         folder_id: str, file: Optional[str] = None) -> str:

        image_content = await openai_image_edit(image_urls=url_images, prompt=prompt)

        content_base64 = base64.b64encode(image_content).decode('utf-8')
        final_upload = await self._upload_to_s3(
            content_base64,
            owner_id,
            folder_id,
            "variation"
        )
        return final_upload.s3_url

    async def generate_variation_images(self, request: VariationImageRequest, owner_id: str):
        folder_id = uuid.uuid4().hex[:8]
        original_image_response = await self._upload_to_s3(request.file, owner_id, folder_id, "original")
        vision_analysis = await analyze_image(request.file)

        message_request = MessageRequest(
            query=f"Attached is the product image. {vision_analysis.get_analysis_text()}",
            agent_id=AGENT_IMAGE_VARIATIONS,
            conversation_id="",
            files=[{
                "type": "image",
                "url": original_image_response.s3_url,
                "content": request.file
            }]
        )

        response = await self.message_service.handle_message(message_request)
        prompt = response["text"] + " Do not modify any text, letters, brand logos, brand names, or symbols."
        tasks = [
            self._generate_single_variation([original_image_response.s3_url], prompt, owner_id, folder_id, request.file)
            for i in range(request.num_variations)
        ]
        generated_urls = await asyncio.gather(*tasks)

        return GenerateImageResponse(generated_urls=generated_urls, original_url=original_image_response.s3_url,
                                     generated_prompt=prompt, vision_analysis=vision_analysis)

    async def generate_images_from(self, request: GenerateImageRequest, owner_id: str):
        folder_id = uuid.uuid4().hex[:8]
        urls = request.file_urls or []
        original_url = request.file_url

        if request.file:
            original_image_response = await self._upload_to_s3(request.file, owner_id, folder_id, "original")
            original_url = original_image_response.s3_url

        if len(urls) == 0 and original_url:
            urls.append(request.file_url)

        tasks = [
            self._generate_single_variation(
                urls,
                request.prompt,
                owner_id,
                folder_id,
                request.file,
            )
            for i in range(request.num_variations)
        ]
        generated_urls = await asyncio.gather(*tasks)

        return GenerateImageResponse(
            original_urls=urls,
            generated_urls=generated_urls,
            original_url=original_url,
            generated_prompt=request.prompt
        )

    async def generate_images_from_agent(self, request: GenerateImageRequest, owner_id: str):
        data = MessageRequest(
            agent_id=request.agent_id,
            query=request.agent_id,
            parameter_prompt=request.parameter_prompt,
            conversation_id="",
        )

        message = await self.message_service.handle_message(data)
        request.prompt = message["text"]
        response = await self.generate_images_from(request, owner_id)

        return response
