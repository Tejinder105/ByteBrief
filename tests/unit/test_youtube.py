from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest

from app.scrapers.youtube import (
    YouTubeInputError,
    channel_feed_url,
    fetch_recent_videos,
    fetch_transcript,
    normalize_channel_id,
    parse_feed,
    resolve_channel_id,
)
from app.services.transcript import get_transcript

CHANNEL_ID = "UC1234567890123456789012"


def test_normalize_channel_id_accepts_id_and_channel_url() -> None:
    assert normalize_channel_id(CHANNEL_ID) == CHANNEL_ID
    assert (
        normalize_channel_id(f"https://www.youtube.com/channel/{CHANNEL_ID}")
        == CHANNEL_ID
    )
    assert channel_feed_url(CHANNEL_ID).endswith(f"?channel_id={CHANNEL_ID}")


def test_resolve_channel_id_accepts_handle_url() -> None:
    html = '<meta itemprop="channelId" content="UC1234567890123456789012">'
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=html)
    )

    with httpx.Client(transport=transport) as client:
        assert (
            resolve_channel_id("https://www.youtube.com/@daveebbelaar", client)
            == CHANNEL_ID
        )


def test_resolve_channel_id_accepts_current_youtube_page_data() -> None:
    html = (
        '"externalId":"UC1234567890123456789012","keywords":"Python"'
        '"browseId":"UC1234567890123456789012"'
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=html)
    )

    with httpx.Client(transport=transport) as client:
        assert (
            resolve_channel_id("https://www.youtube.com/@daveebbelaar", client)
            == CHANNEL_ID
        )


def test_normalize_channel_id_rejects_handles() -> None:
    with pytest.raises(YouTubeInputError, match="canonical YouTube channel ID"):
        normalize_channel_id("https://www.youtube.com/@some-channel")


def test_parse_feed_extracts_video_metadata() -> None:
    content = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:yt="http://www.youtube.com/xml/schemas/2015">
      <entry>
        <id>yt:video:video-123</id>
        <yt:videoId>video-123</yt:videoId>
        <title>New episode</title>
        <link rel="alternate" href="https://www.youtube.com/watch?v=video-123"/>
        <published>2026-10-24T10:00:00+00:00</published>
        <summary>Episode description</summary>
      </entry>
    </feed>"""

    videos = parse_feed(content, CHANNEL_ID)

    assert len(videos) == 1
    assert videos[0].video_id == "video-123"
    assert videos[0].title == "New episode"
    assert videos[0].description == "Episode description"
    assert videos[0].published_at == datetime(
        2026, 10, 24, 10, tzinfo=UTC
    )


def test_fetch_recent_videos_filters_old_entries_and_deduplicates() -> None:
    now = datetime(2026, 10, 25, 12, tzinfo=UTC)
    feed = """<feed xmlns="http://www.w3.org/2005/Atom"
        xmlns:yt="http://www.youtube.com/xml/schemas/2015">
      <entry><yt:videoId>new</yt:videoId><title>New</title>
        <published>2026-10-25T10:00:00+00:00</published></entry>
      <entry><yt:videoId>old</yt:videoId><title>Old</title>
        <published>2026-10-23T10:00:00+00:00</published></entry>
    </feed>"""
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=feed))

    with httpx.Client(transport=transport) as client:
        videos = fetch_recent_videos(
            [CHANNEL_ID, f"https://www.youtube.com/channel/{CHANNEL_ID}"],
            since=now - timedelta(hours=24),
            client=client,
        )

    assert [video.video_id for video in videos] == ["new"]


def test_fetch_transcript_flattens_snippets() -> None:
    transcript = [SimpleNamespace(text=" Hello "), SimpleNamespace(text="world")]
    api = Mock()
    api.fetch.return_value = transcript

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=api):
        result = fetch_transcript("video-123")

    assert result == "Hello world"
    api.fetch.assert_called_once_with("video-123", languages=("en",))


def test_fetch_transcript_falls_back_to_available_language() -> None:
    from youtube_transcript_api._errors import NoTranscriptFound

    fallback = Mock()
    fallback.fetch.return_value = [
        SimpleNamespace(text=" Hindi transcript ")
    ]
    api = Mock()
    api.fetch.side_effect = NoTranscriptFound("video-123", ("en",), Mock())
    api.list.return_value = [fallback]

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=api):
        result = fetch_transcript("video-123")

    assert result == "Hindi transcript"
    api.list.assert_called_once_with("video-123")


def test_fetch_transcript_returns_none_when_youtube_blocks_request() -> None:
    from youtube_transcript_api._errors import IpBlocked

    api = Mock()
    api.fetch.side_effect = IpBlocked("video-123")

    with patch("app.services.transcript.YouTubeTranscriptApi", return_value=api):
        result = fetch_transcript("video-123")

    assert result is None


def test_get_transcript_requires_a_video_id() -> None:
    with pytest.raises(ValueError, match="video_id must not be empty"):
        get_transcript("  ")
