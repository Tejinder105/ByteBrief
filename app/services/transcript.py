"""Backward-compatible transcript retrieval entry point."""

from __future__ import annotations

from collections.abc import Sequence

from youtube_transcript_api import YouTubeTranscriptApi

from app.scrapers.youtube import YouTubeScraper


def get_transcript(
    video_id: str,
    languages: Sequence[str] = ("en",),
) -> str | None:
    """Return a video's transcript as plain text."""

    return YouTubeScraper(
        transcript_api=YouTubeTranscriptApi()
    ).get_transcript(video_id, languages)
