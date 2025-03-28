from app.requests.copy_request import CopyRequest
from app.requests.generate_image_request import GenerateImageRequest
from app.requests.generate_pdf_request import GeneratePdfRequest
from app.requests.recommend_product_request import RecommendProductRequest
from fastapi import APIRouter, Depends, Request
from app.requests.message_request import MessageRequest
from app.requests.variation_image_request import VariationImageRequest
from app.requests.product_scraping_request import ProductScrapingRequest
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service_interface import MessageServiceInterface
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface
from app.middlewares.auth_middleware import require_auth, require_api_key

router = APIRouter(
    prefix="/api/ms/conversational-engine",
    tags=["conversational-agent"]
)


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
    user_info = request.state.user_info
    response = await service.generate_images_from(generate_image_request, user_info.get("data", {}).get("id"))
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


@router.get("/health")
async def health_check():
    return {"status": "OK"}
