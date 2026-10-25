"""YouTube scraper surface for channel videos and transcripts."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Self

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    IpBlocked,
    NoTranscriptFound,
)

from app.models import ChannelVideo
from app.scrapers.youtube_channel import (
    YouTubeInputError,
    channel_feed_url,
    fetch_recent_videos,
    normalize_channel_id,
    parse_feed,
    resolve_channel_id,
)

logger = logging.getLogger(__name__)


def _flatten_transcript(transcript: Any) -> str:
    return " ".join(
        snippet.text.strip()
        for snippet in transcript
        if snippet.text.strip()
    )


class YouTubeScraper:
    """Fetch YouTube channel videos and their available transcripts."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        transcript_api: Any | None = None,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._transcript_api = transcript_api

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client when this scraper created it."""

        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def _http_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=20.0, follow_redirects=True)
        return self._client

    def resolve_channel_id(self, channel: str) -> str:
        """Resolve a channel ID or YouTube handle URL."""

        return resolve_channel_id(channel, self._http_client())

    def fetch_recent_videos(
        self,
        channels: Iterable[str],
        *,
        since: datetime,
    ) -> list[ChannelVideo]:
        """Fetch videos published at or after ``since``."""

        return fetch_recent_videos(
            channels,
            since=since,
            client=self._http_client(),
        )

    def get_transcript(
        self,
        video_id: str,
        languages: Sequence[str] = ("en",),
    ) -> str | None:
        """Return a video's transcript as plain text when captions are available."""

        if not video_id.strip():
            raise ValueError("video_id must not be empty")

        normalized_video_id = video_id.strip()
        api = self._transcript_api or YouTubeTranscriptApi()
        try:
            transcript = api.fetch(normalized_video_id, languages=languages)
        except NoTranscriptFound:
            try:
                available_transcripts = list(api.list(normalized_video_id))
            except CouldNotRetrieveTranscript:
                return None
            if not available_transcripts:
                return None
            transcript = available_transcripts[0].fetch()
        except IpBlocked:
            logger.warning(
                "Transcript unavailable for video %s: YouTube blocked the request.",
                normalized_video_id,
            )
            return None
        except CouldNotRetrieveTranscript as error:
            logger.warning(
                "Transcript unavailable for video %s: %s",
                normalized_video_id,
                error,
            )
            return None
        return _flatten_transcript(transcript)

    def fetch_recent_videos_with_transcripts(
        self,
        channels: Iterable[str],
        *,
        since: datetime | None = None,
        languages: Sequence[str] = ("en",),
    ) -> list[ChannelVideo]:
        """Fetch recent videos and attach available transcripts."""

        window_start = since or datetime.now(UTC) - timedelta(hours=24)
        videos = self.fetch_recent_videos(channels, since=window_start)
        return [
            video.model_copy(
                update={"transcript": self.get_transcript(video.video_id, languages)}
            )
            for video in videos
        ]


def fetch_recent_videos_with_transcripts(
    channels: Iterable[str],
    *,
    since: datetime | None = None,
    languages: Sequence[str] = ("en",),
    client: httpx.Client | None = None,
) -> list[ChannelVideo]:
    """Compatibility wrapper for :meth:`YouTubeScraper.fetch_recent_videos_with_transcripts`."""

    with YouTubeScraper(client=client) as scraper:
        return scraper.fetch_recent_videos_with_transcripts(
            channels,
            since=since,
            languages=languages,
        )


def fetch_transcript(
    video_id: str,
    languages: Sequence[str] = ("en",),
) -> str | None:
    """Compatibility wrapper for :meth:`YouTubeScraper.get_transcript`."""

    from app.services.transcript import get_transcript

    return get_transcript(video_id, languages)


__all__ = [
    "YouTubeInputError",
    "YouTubeScraper",
    "channel_feed_url",
    "fetch_recent_videos",
    "fetch_recent_videos_with_transcripts",
    "fetch_transcript",
    "normalize_channel_id",
    "parse_feed",
    "resolve_channel_id",
]
