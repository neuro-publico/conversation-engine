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

@router.post("/calculator")
async def calculator(
    request: dict,
    fastapi_request: Request
):
    print("-------------------------")
    print("Datos recibidos en la solicitud:", request)
    print("Headers recibidos:", dict(fastapi_request.headers))
    return {"result": 20000}
