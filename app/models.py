"""Shared Pydantic models used by the ingestion surfaces."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChannelVideo(BaseModel):
    """Normalized video output returned by a configured YouTube channel."""

    title: str
    url: str
    published_at: datetime
    description: str
    video_id: str
    transcript: Optional[str] = None  # noqa: UP045
