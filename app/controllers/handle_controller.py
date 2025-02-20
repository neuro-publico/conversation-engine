from app.requests.generate_pdf_request import GeneratePdfRequest
from app.requests.recommend_product_request import RecommendProductRequest
from fastapi import APIRouter, Depends, Request
from app.requests.message_request import MessageRequest
from app.requests.variation_image_request import VariationImageRequest
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service_interface import MessageServiceInterface
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
    response = await service.generate_variation_images(variation_request, user_info.get("data", {}).get("_id"))
    return response


@router.get("/health")
async def health_check():
    return {"status": "OK"}
