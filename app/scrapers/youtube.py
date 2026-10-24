"""YouTube ingestion facade combining channel scraping and transcript services."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

import httpx

from app.models import ChannelVideo
from app.scrapers.youtube_channel import (
    YouTubeInputError,
    channel_feed_url,
    fetch_recent_videos,
    normalize_channel_id,
    parse_feed,
    resolve_channel_id,
)
from app.services.transcript import get_transcript

fetch_transcript = get_transcript


def fetch_recent_videos_with_transcripts(
    channels: Iterable[str],
    *,
    since: datetime | None = None,
    languages: Sequence[str] = ("en",),
    client: httpx.Client | None = None,
) -> list[ChannelVideo]:
    """Fetch recent channel videos and attach available transcripts."""

    window_start = since or datetime.now(UTC) - timedelta(hours=24)
    videos = fetch_recent_videos(channels, since=window_start, client=client)
    return [
        video.model_copy(
            update={"transcript": fetch_transcript(video.video_id, languages)}
        )
        for video in videos
    ]


__all__ = [
    "YouTubeInputError",
    "channel_feed_url",
    "fetch_recent_videos",
    "fetch_recent_videos_with_transcripts",
    "fetch_transcript",
    "normalize_channel_id",
    "parse_feed",
    "resolve_channel_id",
]
