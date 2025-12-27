import base64
import httpx

from app.requests.brand_context_resolver_request import BrandContextResolverRequest
from app.requests.copy_request import CopyRequest
from app.requests.direct_scrape_request import DirectScrapeRequest
from app.requests.generate_image_request import GenerateImageRequest
from app.requests.generate_pdf_request import GeneratePdfRequest
from app.requests.recommend_product_request import RecommendProductRequest
from app.requests.resolve_funnel_request import ResolveFunnelRequest
from fastapi import APIRouter, Depends, Request, HTTPException
from app.requests.message_request import MessageRequest
from app.requests.variation_image_request import VariationImageRequest
from app.requests.product_scraping_request import ProductScrapingRequest
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service_interface import MessageServiceInterface
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface
from app.middlewares.auth_middleware import require_auth, require_api_key
from pydantic import BaseModel

# Importaciones para Dropi
from app.services.dropi_service_interface import DropiServiceInterface
from app.services.dropi_service import DropiService

router = APIRouter(
    prefix="/api/ms/conversational-engine",
    tags=["conversational-agent"]
)

@router.get("/integration/dropi/departments")
async def get_departments(
    country: str = "co",
    service: DropiServiceInterface = Depends(DropiService)
):
    return await service.get_departments(country)

@router.get("/integration/dropi/departments/{department_id}/cities")
async def get_cities_by_department(
    department_id: int,
    country: str = "co",
    service: DropiServiceInterface = Depends(DropiService)
):
    return await service.get_cities_by_department(department_id, country)

@router.post("/handle-message")
async def handle_message(
        request: MessageRequest,
        message_service: MessageServiceInterface = Depends()
):
    response = await message_service.handle_message(request)
    return response


@router.post("/handle-message-json")
async def handle_message(
        request: MessageRequest,
        message_service: MessageServiceInterface = Depends()
):
    response = await message_service.handle_message_json(request)
    return response


@router.post("/recommend-product")
async def recommend_products(
        request: RecommendProductRequest,
        message_service: MessageServiceInterface = Depends()
):
    response = await message_service.recommend_products(request)
    return response


@router.post("/generate-pdf")
async def generate_pdf(
        request: GeneratePdfRequest,
        message_service: MessageServiceInterface = Depends()
):
    response = await message_service.generate_pdf(request)
    return response


@router.post("/generate-variation-images")
@require_auth
async def generate_variation_images(
        request: Request,
        variation_request: VariationImageRequest,
        service: ImageServiceInterface = Depends()
):
    user_info = request.state.user_info
    response = await service.generate_variation_images(variation_request, user_info.get("data", {}).get("id"))
    return response


@router.post("/generate-images-from")
@require_auth
async def generate_images_from(
        request: Request,
        generate_image_request: GenerateImageRequest,
        service: ImageServiceInterface = Depends()
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
        request: Request,
        generate_image_request: GenerateImageRequest,
        service: ImageServiceInterface = Depends()
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
        request: Request,
        generate_image_request: GenerateImageRequest,
        service: ImageServiceInterface = Depends()
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
async def generate_copies(
        copy_request: CopyRequest,
        message_service: MessageServiceInterface = Depends()
):
    response = await message_service.generate_copies(copy_request)
    return response


@router.post("/scrape-product")
@require_auth
async def scrape_product(
        request: Request,
        scraping_request: ProductScrapingRequest,
        service: ProductScrapingServiceInterface = Depends()
):
    response = await service.scrape_product(scraping_request)
    return response

@router.post("/scrape-direct-html")
@require_auth
async def scrape_product_direct(
        request: Request,
        scraping_request: DirectScrapeRequest,
        service: ProductScrapingServiceInterface = Depends()
):
    response = await service.scrape_direct(scraping_request.html)
    return response


@router.post("/resolve-info-funnel")
async def resolve_funnel(
        request: ResolveFunnelRequest,
        message_service: MessageServiceInterface = Depends()
):
    response = await message_service.resolve_funnel(request)
    return response

@router.post("/store/brand-context-resolver")
@require_auth
async def brand_context_resolver(
        request: Request,
        requestBrand: BrandContextResolverRequest,
        message_service: MessageServiceInterface = Depends()
):
    response = await message_service.resolve_brand_context(requestBrand)
    return response


@router.get("/health")
async def health_check():
    return {"status": "OK"}
