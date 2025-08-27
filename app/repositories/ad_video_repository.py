from typing import Any, Optional
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.ad_video_repository_interface import AdVideoRepositoryInterface
from app.requests.generate_video_request import GenerateAdScenesRequest
from app.models.ad import AdVideo, AdVideoStatus
from app.db import AsyncSessionLocal


class AdVideoRepository(AdVideoRepositoryInterface):
	def __init__(self):
		pass

	async def create_ad_video(self, model: AdVideo) -> dict[str, Any]:
		async with AsyncSessionLocal() as session:
			session.add(model)
			try:
				await session.commit()
				await session.refresh(model)
			except SQLAlchemyError:
				await session.rollback()
				raise
		return self._to_dict(model)

	async def list_ad_videos(self, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
		async with AsyncSessionLocal() as session:
			stmt = select(AdVideo)
			if owner_id:
				stmt = stmt.where(AdVideo.owner_id == owner_id)
			result = await session.execute(stmt)
			rows = result.scalars().all()
			return [self._to_dict(r) for r in rows]

	async def get_ad_video(self, ad_video_id: int) -> Optional[dict[str, Any]]:
		async with AsyncSessionLocal() as session:
			stmt = select(AdVideo).where(AdVideo.id == ad_video_id)
			result = await session.execute(stmt)
			row = result.scalar_one_or_none()
			return self._to_dict(row) if row else None

	async def update_ad_video(self, ad_video_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
		async with AsyncSessionLocal() as session:
			stmt = select(AdVideo).where(AdVideo.id == ad_video_id)
			result = await session.execute(stmt)
			ad_video = result.scalar_one_or_none()
			if not ad_video:
				return None
			for key, value in data.items():
				if hasattr(ad_video, key):
					setattr(ad_video, key, value)
			try:
				await session.commit()
				await session.refresh(ad_video)
			except SQLAlchemyError:
				await session.rollback()
				raise
			return self._to_dict(ad_video)

	def _to_dict(self, model: AdVideo) -> dict[str, Any]:
		return {
			"id": model.id,
			"owner_id": model.owner_id,
			"funnel_id": model.funnel_id,
			"status": model.status,
			"scenes": model.scenes,
			"progress": model.progress,
			"result_url": model.result_url,
			"error": model.error,
			"created_at": model.created_at.isoformat() if model.created_at else None,
			"updated_at": model.updated_at.isoformat() if model.updated_at else None,
		}