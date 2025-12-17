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
from app.helpers.image_compression_helper import compress_image_to_target
from fastapi import Depends
import asyncio
import uuid
from dotenv import load_dotenv
from app.externals.google_vision.google_vision_client import analyze_image
from app.externals.images.image_client import google_image, openai_image_edit
from typing import Optional
import base64

load_dotenv()


class ImageService(ImageServiceInterface):
    def __init__(self, message_service: MessageServiceInterface = Depends()):
        self.message_service = message_service

    async def _upload_to_s3(self, image_base64: str, owner_id: str, folder_id: str,
                            prefix_name: str) -> S3UploadResponse:
        unique_id = uuid.uuid4().hex[:8]
        file_name = f"{prefix_name}_{unique_id}"
        original_image_bytes = base64.b64decode(image_base64)
        image_base64_compressed = compress_image_to_target(original_image_bytes, target_kb=120)

        return await upload_file(
            S3UploadRequest(
                file=image_base64_compressed,
                folder=f"{owner_id}/products/variations/{folder_id}",
                filename=file_name
            )
        )


    async def _generate_single_variation(self, url_images: list[str], prompt: str, owner_id: str,
                                         folder_id: str, file: Optional[str] = None, extra_params: Optional[dict] = None, 
                                         provider: Optional[str] = None, model_ai: Optional[str] = None) -> str:

        if provider and provider.lower() == "openai":
            image_content = await openai_image_edit(image_urls=url_images, prompt=prompt, model_ia=model_ai, extra_params=extra_params)
        else:
            image_content = await google_image(image_urls=url_images, prompt=prompt, model_ia=model_ai, extra_params=extra_params)

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
            parameter_prompt={"language": request.language},
            files=[{
                "type": "image",
                "url": original_image_response.s3_url,
                "content": request.file
            }]
        )

        response_data = await self.message_service.handle_message_with_config(message_request)
        agent_config = response_data["agent_config"]
        response = response_data["message"]

        extra_params = None
        if agent_config.preferences.extra_parameters:
            extra_params = agent_config.preferences.extra_parameters

        prompt = response["text"] + " Do not modify any text, letters, brand logos, brand names, or symbols."
        tasks = [
            self._generate_single_variation([original_image_response.s3_url], prompt, owner_id, folder_id,
                                            request.file, extra_params, provider=agent_config.provider_ai, 
                                            model_ai=agent_config.model_ai)
            for i in range(request.num_variations)
        ]
        generated_urls = await asyncio.gather(*tasks)

        return GenerateImageResponse(
            generated_urls=generated_urls, 
            original_url=original_image_response.s3_url,
            original_urls=[original_image_response.s3_url],
            generated_prompt=prompt, 
            vision_analysis=vision_analysis
        )

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
                extra_params=request.extra_parameters,
                provider=request.provider,
                model_ai=request.model_ai
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
        parameter_prompt = request.parameter_prompt or {}
        parameter_prompt["language"] = request.language
        
        data = MessageRequest(
            agent_id=request.agent_id,
            query=request.agent_id,
            parameter_prompt=parameter_prompt,
            conversation_id="",
        )

        response_data = await self.message_service.handle_message_with_config(data)
        agent_config = response_data["agent_config"]
        message = response_data["message"]
        
        request.prompt = message["text"]
        request.provider = agent_config.provider_ai
        request.model_ai = agent_config.model_ai
        
        if agent_config.preferences.extra_parameters:
            request.extra_parameters = agent_config.preferences.extra_parameters

        response = await self.generate_images_from(request, owner_id)

        return response
