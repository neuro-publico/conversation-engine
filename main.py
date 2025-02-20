from fastapi import FastAPI

from app.controllers.handle_controller import router
from app.managers.conversation_manager import ConversationManager
from app.managers.conversation_manager_interface import ConversationManagerInterface
from app.services.image_service import ImageService
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service import MessageService
from app.services.message_service_interface import MessageServiceInterface

app = FastAPI(
    title="Conversational Agent API",
    description="API for agent ai",
    version="1.0.0"
)
app.include_router(router)
app.dependency_overrides[MessageServiceInterface] = MessageService
app.dependency_overrides[ConversationManagerInterface] = ConversationManager
app.dependency_overrides[ImageServiceInterface] = ImageService

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
