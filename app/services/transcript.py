"""Minimal YouTube transcript retrieval service."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    IpBlocked,
    NoTranscriptFound,
)

logger = logging.getLogger(__name__)


def _flatten_transcript(transcript: Any) -> str:
    return " ".join(
        snippet.text.strip()
        for snippet in transcript
        if snippet.text.strip()
    )


def get_transcript(
    video_id: str,
    languages: Sequence[str] = ("en",),
) -> str | None:
    """Return a video's transcript as plain text.

    The ``video_id`` must be the YouTube ID, not a full video URL. If the
    requested language is unavailable, the first available transcript is used.
    Missing captions and YouTube request blocks return ``None``.
    """

    if not video_id.strip():
        raise ValueError("video_id must not be empty")

    normalized_video_id = video_id.strip()
    api = YouTubeTranscriptApi()
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
