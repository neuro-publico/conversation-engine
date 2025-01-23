from fastapi import APIRouter, Depends

from app.requests.message_request import MessageRequest
from app.services.message_service_interface import MessageServiceInterface

router = APIRouter(
    prefix="/api/ms/conversational-agent",
    tags=["conversational-agent"]
)


@router.post("/handle-message")
async def handle_message(
    request: MessageRequest, 
    message_service: MessageServiceInterface = Depends()
):
    response = await message_service.handle_message(request)
    return response
