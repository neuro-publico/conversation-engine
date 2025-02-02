from app.requests.recommend_product_request import RecommendProductRequest
from fastapi import APIRouter, Depends, Request

from app.requests.message_request import MessageRequest
from app.services.message_service_interface import MessageServiceInterface

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


@router.get("/health")
async def health_check():
    return {"status": "OK"}
