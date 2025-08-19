from fastapi import FastAPI

from app.controllers.handle_controller import router
from app.controllers.ads_controller import router as ads_router
from app.managers.conversation_manager import ConversationManager
from app.managers.conversation_manager_interface import ConversationManagerInterface
from app.services.image_service import ImageService
from app.services.image_service_interface import ImageServiceInterface
from app.services.message_service import MessageService
from app.services.message_service_interface import MessageServiceInterface
from app.services.product_scraping_service import ProductScrapingService
from app.services.product_scraping_service_interface import ProductScrapingServiceInterface

import asyncio
from app.managers.process_video_ads import ProcessVideoAds

app = FastAPI(
    title="Conversational Agent API",
    description="API for agent ai",
    version="1.0.0"
)

app.include_router(router)
app.include_router(ads_router)

conversation_manager_singleton = ConversationManager()

app.dependency_overrides[MessageServiceInterface] = MessageService
app.dependency_overrides[ConversationManagerInterface] = lambda: conversation_manager_singleton
app.dependency_overrides[ImageServiceInterface] = ImageService
app.dependency_overrides[ProductScrapingServiceInterface] = ProductScrapingService


@app.on_event("startup")
async def start_listeners():
    manager = ProcessVideoAds()
    app.state.sqs_manager = manager
    # Run SQS listener in background
    app.state.sqs_listener_task = asyncio.create_task(manager.listen_forever())


@app.on_event("shutdown")
async def stop_listeners():
    task = getattr(app.state, "sqs_listener_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
