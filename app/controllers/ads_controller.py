from fastapi import APIRouter, Depends, Request, HTTPException
from app.services.generate_video_service_interface import GenerateVideoServiceInterface
from app.services.generate_video_service import GenerateVideoService
from app.requests.generate_video_request import GenerateAdScenesRequest
from app.middlewares.auth_middleware import require_auth

router = APIRouter(
    prefix="/api/ms/conversational-engine/ads",
    tags=["conversational-agent"]
)

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

