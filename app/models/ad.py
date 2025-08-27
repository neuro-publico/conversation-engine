from sqlalchemy import String, Integer, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import JSONB

from app.db import Base


class AdVideoStatus(str, PyEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AdVideo(Base):
    __tablename__ = "ad_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    funnel_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=AdVideoStatus.PENDING.value)
    scenes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    result_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow) 