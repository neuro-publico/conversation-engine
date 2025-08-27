from fastapi import APIRouter, Depends, Request, HTTPException
from app.requests.message_request import MessageRequest
from app.services.message_service_interface import MessageServiceInterface

from app.services.generate_video_service_interface import GenerateVideoServiceInterface
from app.services.generate_video_service import GenerateVideoService
from app.requests.generate_video_request import GenerateAdScenesRequest
from uuid import uuid4
import os
from arq.connections import ArqRedis, RedisSettings
from arq import create_pool
from app.middlewares.auth_middleware import require_auth
# from app.models import AdVideoJob

router = APIRouter(
    prefix="/api/ms/conversational-engine/ads",
    tags=["conversational-agent"]
)

async def get_redis() -> ArqRedis:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    settings = RedisSettings.from_dsn(redis_url)
    return await create_pool(settings)

@router.post("/generate-video", status_code=202)
@require_auth
async def generate_video_controller(
        request: Request,
        generate_ad_scenes_request: GenerateAdScenesRequest,
        generate_video_service: GenerateVideoServiceInterface = Depends(GenerateVideoService),
):
    user_info = getattr(request.state, "user_info", {}) or {}
    owner_id = (user_info.get("data") or {}).get("id") or user_info.get("id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    generate_ad_video_result = await generate_video_service.generate_ad_video(
        generate_ad_scenes_request,
        owner_id
    )
    
    return generate_ad_video_result

