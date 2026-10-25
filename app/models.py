"""Shared Pydantic models used by the ingestion surfaces."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Transcript(BaseModel):
    """Plain-text transcript returned for a video."""

    text: str


class OpenAIArticle(BaseModel):
    """Normalized article returned by the OpenAI News RSS feed."""

    title: str
    description: str
    url: str
    guid: str
    published_at: datetime
    category: str | None = None


class AnthropicArticle(BaseModel):
    """Normalized article returned by an Anthropic RSS feed."""

    title: str
    description: str
    url: str
    guid: str
    published_at: datetime
    category: str | None = None


class ChannelVideo(BaseModel):
    """Normalized video output returned by a configured YouTube channel."""

    title: str
    url: str
    published_at: datetime
    description: str
    video_id: str
    transcript: Optional[str] = None  # noqa: UP045
