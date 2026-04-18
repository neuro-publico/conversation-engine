from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.handle_controller import router
from app.db.audit_logger import init_pool, close_pool
from app.managers.conversation_manager import ConversationManager
from app.managers.conversation_manager_interface import ConversationManagerInterface
from app.services.image_service import ImageService
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service import MessageService
from app.services.message_service_interface import MessageServiceInterface
from app.services.product_scraping_service import ProductScrapingService
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface
from app.services.video_service import VideoService
from app.services.video_service_interface import VideoServiceInterface
from app.services.audio_service import AudioService
from app.services.audio_service_interface import AudioServiceInterface


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Conversational Agent API",
    description="API for agent ai",
    version="1.0.0",
    lifespan=lifespan,
)

# Dev-only CORS: en local el builder llama directo a :8000 para evitar el
# timeout del proxy de Next.js en operaciones largas (generación IA ~30-60s).
if os.getenv("ENVIRONMENT", "dev") != "prod":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:(3000|3001|31\d\d|5173)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)

conversation_manager_singleton = ConversationManager()

app.dependency_overrides[MessageServiceInterface] = MessageService
app.dependency_overrides[ConversationManagerInterface] = lambda: conversation_manager_singleton
app.dependency_overrides[ImageServiceInterface] = ImageService
app.dependency_overrides[ProductScrapingServiceInterface] = ProductScrapingService
app.dependency_overrides[VideoServiceInterface] = VideoService
app.dependency_overrides[AudioServiceInterface] = AudioService

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
