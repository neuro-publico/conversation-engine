import asyncio
import base64
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.db.audit_logger import log_prompt
from app.middlewares.auth_middleware import require_api_key, require_auth
from app.requests.brand_context_resolver_request import BrandContextResolverRequest
from app.requests.copy_request import CopyRequest
from app.requests.direct_scrape_request import DirectScrapeRequest
from app.requests.generate_audio_request import GenerateAudioRequest
from app.requests.generate_image_request import GenerateImageRequest
from app.requests.generate_pdf_request import GeneratePdfRequest
from app.requests.generate_video_request import GenerateVideoRequest
from app.requests.message_request import MessageRequest
from app.requests.product_scraping_request import ProductScrapingRequest
from app.requests.recommend_product_request import RecommendProductRequest
from app.requests.resolve_funnel_request import ResolveFunnelRequest
from app.requests.edit_section_html_request import ChatMessage, EditSectionHtmlRequest, TemplateGenerateRequest
from app.requests.section_html_request import SectionHtmlRequest
from app.requests.orchestrate_images_request import OrchestrateImagesRequest
from app.requests.sub_image_request import GenerateSubImagesRequest
from app.requests.section_image_request import SectionImageRequest
from app.requests.variation_image_request import VariationImageRequest
from app.requests.video_studio_draft_request import VideoStudioDraftRequest
from app.services.audio_service import AudioService
from app.services.audio_service_interface import AudioServiceInterface
from app.services.dropi_service import DropiService

# Importaciones para Dropi
from app.services.dropi_service_interface import DropiServiceInterface
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service_interface import MessageServiceInterface
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface
from app.services.video_service import VideoService
from app.services.video_service_interface import VideoServiceInterface

router = APIRouter(prefix="/api/ms/conversational-engine", tags=["conversational-agent"])


@router.get("/integration/dropi/departments")
async def get_departments(country: str = "co", service: DropiServiceInterface = Depends(DropiService)):
    return await service.get_departments(country)


@router.get("/integration/dropi/departments/{department_id}/cities")
async def get_cities_by_department(
    department_id: int, country: str = "co", service: DropiServiceInterface = Depends(DropiService)
):
    return await service.get_cities_by_department(department_id, country)


@router.post("/handle-message")
async def handle_message(request: MessageRequest, message_service: MessageServiceInterface = Depends()):
    response = await message_service.handle_message(request)
    if request.agent_id:
        asyncio.create_task(
            log_prompt(
                log_type="agent_call",
                prompt=request.query,
                agent_id=request.agent_id,
                response_text=str(response)[:5000] if response else None,
            )
        )
    return response


@router.post("/handle-message-json")
async def handle_message(request: MessageRequest, message_service: MessageServiceInterface = Depends()):
    response = await message_service.handle_message_json(request)
    if request.agent_id:
        asyncio.create_task(
            log_prompt(
                log_type="agent_call_json",
                prompt=request.query,
                agent_id=request.agent_id,
                response_text=str(response)[:5000] if response else None,
            )
        )
    return response


@router.post("/recommend-product")
async def recommend_products(request: RecommendProductRequest, message_service: MessageServiceInterface = Depends()):
    response = await message_service.recommend_products(request)
    return response


@router.post("/generate-pdf")
async def generate_pdf(request: GeneratePdfRequest, message_service: MessageServiceInterface = Depends()):
    response = await message_service.generate_pdf(request)
    return response


@router.post("/generate-variation-images")
@require_auth
async def generate_variation_images(
    request: Request, variation_request: VariationImageRequest, service: ImageServiceInterface = Depends()
):
    user_info = request.state.user_info
    response = await service.generate_variation_images(variation_request, user_info.get("data", {}).get("id"))
    return response


@router.post("/generate-images-from")
@require_auth
async def generate_images_from(
    request: Request, generate_image_request: GenerateImageRequest, service: ImageServiceInterface = Depends()
):
    if not generate_image_request.file and generate_image_request.file_url:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(generate_image_request.file_url)
                response.raise_for_status()
                generate_image_request.file = base64.b64encode(response.content).decode()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error for get file: {str(e)}")

    user_info = request.state.user_info
    response = await service.generate_images_from(generate_image_request, user_info.get("data", {}).get("id"))
    return response


@router.post("/generate-images-from/api-key")
@require_api_key
async def generate_images_from_api_key(
    request: Request, generate_image_request: GenerateImageRequest, service: ImageServiceInterface = Depends()
):
    if not generate_image_request.file and generate_image_request.file_url:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(generate_image_request.file_url)
                response.raise_for_status()
                generate_image_request.file = base64.b64encode(response.content).decode()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error for get file: {str(e)}")
    response = await service.generate_images_from(generate_image_request, generate_image_request.owner_id)
    return response


@router.post("/generate-images-from-agent/api-key")
@require_api_key
async def generate_images_from_agent_api_key(
    request: Request, generate_image_request: GenerateImageRequest, service: ImageServiceInterface = Depends()
):
    if not generate_image_request.file and generate_image_request.file_url:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(generate_image_request.file_url)
                response.raise_for_status()
                generate_image_request.file = base64.b64encode(response.content).decode()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error for get file: {str(e)}")
    response = await service.generate_images_from_agent(generate_image_request, generate_image_request.owner_id)
    return response


@router.post("/generate-copies")
async def generate_copies(copy_request: CopyRequest, message_service: MessageServiceInterface = Depends()):
    response = await message_service.generate_copies(copy_request)
    return response


@router.post("/scrape-product")
@require_auth
async def scrape_product(
    request: Request, scraping_request: ProductScrapingRequest, service: ProductScrapingServiceInterface = Depends()
):
    response = await service.scrape_product(scraping_request)
    return response


@router.post("/scrape-product/api-key")
@require_api_key
async def scrape_product_api_key(
    request: Request, scraping_request: ProductScrapingRequest, service: ProductScrapingServiceInterface = Depends()
):
    """Misma lógica que scrape-product pero con x-api-key para pruebas en local."""
    response = await service.scrape_product(scraping_request)
    return response


@router.post("/scrape-direct-html")
@require_auth
async def scrape_product_direct(
    request: Request, scraping_request: DirectScrapeRequest, service: ProductScrapingServiceInterface = Depends()
):
    response = await service.scrape_direct(scraping_request.html)
    return response


@router.post("/resolve-info-funnel")
async def resolve_funnel(request: ResolveFunnelRequest, message_service: MessageServiceInterface = Depends()):
    response = await message_service.resolve_funnel(request)
    return response


@router.post("/store/brand-context-resolver")
@require_auth
async def brand_context_resolver(
    request: Request, requestBrand: BrandContextResolverRequest, message_service: MessageServiceInterface = Depends()
):
    response = await message_service.resolve_brand_context(requestBrand)
    return response


@router.post("/generate-video")
async def generate_video(
    request: Request,
    requestGenerateVideo: GenerateVideoRequest,
    video_service: VideoServiceInterface = Depends(VideoService),
):
    return await video_service.generate_video(requestGenerateVideo)


@router.post("/generate-audio")
async def generate_audio(
    request: Request,
    requestGenerateAudio: GenerateAudioRequest,
    audio_service: AudioServiceInterface = Depends(AudioService),
):
    return await audio_service.generate_audio(requestGenerateAudio)


@router.post("/preview-section-image-prompt/api-key")
@require_api_key
async def preview_section_image_prompt(
    request: Request,
    preview_request: dict,
):
    """Preview the full prompt that the AI receives for image generation. Read-only."""
    from app.services.section_image_service import SectionImageService

    service = SectionImageService()
    return await service.preview_image_prompt(
        user_prompt=preview_request.get("user_prompt"),
        image_format=preview_request.get("image_format"),
    )


@router.post("/generate-section-image/api-key")
@require_api_key
async def generate_section_image(
    request: Request,
    section_request: SectionImageRequest,
):
    from app.services.section_image_service import SectionImageService

    service = SectionImageService()
    response = await service.generate_section_image(section_request)
    return response


@router.post("/generate-section-image/async/api-key")
@require_api_key
async def generate_section_image_async(
    request: Request,
    section_request: SectionImageRequest,
):
    from app.services.section_image_service import SectionImageService

    if not section_request.callback_url:
        raise HTTPException(status_code=400, detail="callback_url is required for async generation")

    request_id = str(uuid.uuid4())
    service = SectionImageService()

    asyncio.create_task(
        service.generate_and_callback(
            request=section_request,
            request_id=request_id,
            callback_url=section_request.callback_url,
            callback_metadata=section_request.callback_metadata,
        )
    )

    return JSONResponse(
        status_code=202,
        content={"request_id": request_id, "status": "accepted"},
    )


@router.post("/edit-section-image")
@require_auth
async def edit_section_image(
    request: Request,
    section_request: SectionImageRequest,
):
    from app.services.section_image_service import SectionImageService

    user_info = request.state.user_info
    section_request.owner_id = user_info.get("data", {}).get("id", section_request.owner_id)
    section_request.edit_mode = True
    service = SectionImageService()
    response = await service.generate_section_image(section_request)
    return response


@router.post("/video-studio/draft/api-key")
@require_api_key
async def video_studio_draft_sync(
    request: Request,
    draft_request: VideoStudioDraftRequest,
):
    """Sync endpoint: ejecuta el Director Creativo y devuelve el payload directo.

    Sirve para testing con curl. En producción el frontend usa el endpoint async
    de abajo (con callback al ecommerce).
    """
    from app.services.video_studio_service import VideoStudioError, VideoStudioService

    service = VideoStudioService()
    try:
        payload = await service.run_director(draft_request)
        return {
            "status": "success",
            "reference_id": draft_request.reference_id,
            "director_payload": payload.model_dump(),
        }
    except VideoStudioError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "step": e.step,
                "reference_id": draft_request.reference_id,
            },
        )


@router.post("/video-studio/draft/async/api-key")
@require_api_key
async def video_studio_draft_async(
    request: Request,
    draft_request: VideoStudioDraftRequest,
):
    """Async endpoint: lanza el director en background y responde 202 inmediatamente.

    Cuando el director termina (éxito o fallo), POSTea el resultado al
    `callback_url` provisto en el request. Esta es la forma normal en producción.
    """
    from app.services.video_studio_service import VideoStudioService

    if not draft_request.callback_url:
        raise HTTPException(
            status_code=400,
            detail="callback_url is required for async video studio draft generation",
        )

    service = VideoStudioService()
    asyncio.create_task(service.run_and_callback(draft_request))

    return JSONResponse(
        status_code=202,
        content={
            "reference_id": draft_request.reference_id,
            "status": "directing",
            "message": "Director Creative pipeline started.",
        },
    )


# ------------------------------------------------------------------
# Section HTML (code-based sections) — no LangChain
# ------------------------------------------------------------------


@router.post("/generate-section-html/api-key")
@require_api_key
async def generate_section_html(
    request: Request,
    section_request: SectionHtmlRequest,
):
    """Generate an HTML section from a template + product data. Server-to-server."""
    from app.services.section_html_service import SectionHtmlService

    service = SectionHtmlService()
    response = await service.generate_section_html(section_request)
    return response


@router.post("/preview-section-prompt/api-key")
@require_api_key
async def preview_section_prompt(
    request: Request,
    preview_request: dict,
):
    """Preview the full prompt that the AI will receive. Read-only, no AI call."""
    from app.services.section_html_service import SectionHtmlService

    service = SectionHtmlService()
    return await service.preview_prompt(
        template_html=preview_request.get("template_html"),
        copy_prompt=preview_request.get("copy_prompt"),
        content_rules=preview_request.get("content_rules"),
        template_notes=preview_request.get("template_notes"),
        image_instructions=preview_request.get("image_instructions"),
    )


@router.post("/edit-section-html")
@require_auth
async def edit_section_html(
    request: Request,
    edit_request: EditSectionHtmlRequest,
):
    """Edit an existing HTML section via user chat instruction."""
    from app.services.section_html_service import SectionHtmlService

    edit_request.owner_id = request.state.user_info.get("data", {}).get("id", edit_request.owner_id)
    service = SectionHtmlService()
    response = await service.edit_section_html(edit_request)
    return response


@router.post("/generate-template-html/api-key")
@require_api_key
async def generate_template_html(
    request: Request,
    body: TemplateGenerateRequest,
):
    """Chat with AI to create/iterate template HTML. Internal use (backoffice)."""
    from app.services.section_html_service import SectionHtmlService

    history = None
    if body.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in body.conversation_history]

    service = SectionHtmlService()
    response = await service.generate_template_html(
        instruction=body.instruction,
        conversation_history=history,
    )
    return response


@router.post("/orchestrate-section-images/api-key")
@require_api_key
async def orchestrate_section_images(
    request: Request,
    orch_request: OrchestrateImagesRequest,
):
    """Analyze HTML and generate coherent image prompts for all placeholders."""
    from app.services.section_html_service import SectionHtmlService

    service = SectionHtmlService()
    response = await service.orchestrate_image_prompts(orch_request)
    return response


@router.post("/generate-sub-images/api-key")
@require_api_key
async def generate_sub_images(
    request: Request,
    sub_request: GenerateSubImagesRequest,
):
    """Generate sub-element images for an HTML section. Server-to-server."""
    from app.services.sub_image_service import SubImageService

    service = SubImageService()
    response = await service.generate_sub_images(sub_request)
    return response


@router.get("/health")
async def health_check():
    return {"status": "OK"}
