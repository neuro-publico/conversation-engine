from typing import Any, Optional

from app.models.ad import AdVideo
from app.requests.generate_video_request import GenerateAdScenesRequest


def map_request_to_ad_video(request: GenerateAdScenesRequest, owner_id: str, scenes: Optional[list[dict[str, Any]]] = None) -> AdVideo:
	model = AdVideo(
		owner_id=owner_id,
		funnel_id=request.funnel_id,
	)
	if scenes is not None:
		model.scenes = scenes
	return model 