"""YouTube channel resolution, Atom feed fetching, and feed parsing."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import feedparser
import httpx

from app.models import ChannelVideo

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml"
_CHANNEL_ID_PATTERN = re.compile(r"^UC[\w-]{22}$")
_CHANNEL_ID_HTML_PATTERNS = (
    re.compile(
        r'<meta[^>]+itemprop=["\']channelId["\'][^>]+content=["\'](UC[\w-]{22})["\']'
    ),
    re.compile(r'"channelId"\s*:\s*"(UC[\w-]{22})"'),
    re.compile(r'"externalId"\s*:\s*"(UC[\w-]{22})"'),
    re.compile(r'"browseId"\s*:\s*"(UC[\w-]{22})"'),
)


class YouTubeInputError(ValueError):
    """Raised when a configured channel cannot be used with the RSS feed."""


def normalize_channel_id(value: str) -> str:
    """Extract and validate a canonical YouTube channel ID from a value."""

    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0].lower() == "channel":
            candidate = path_parts[1]
        else:
            channel_id = parse_qs(parsed.query).get("channel_id", [None])[0]
            if channel_id:
                candidate = channel_id

    if not _CHANNEL_ID_PATTERN.fullmatch(candidate):
        raise YouTubeInputError(
            f"{value!r} is not a canonical YouTube channel ID. "
            "Use a UC... channel ID or a YouTube channel URL."
        )
    return candidate


def _is_handle_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    path_parts = [part for part in parsed.path.split("/") if part]
    return (
        parsed.netloc.lower().endswith("youtube.com")
        and len(path_parts) == 1
        and path_parts[0].startswith("@")
    )


def resolve_channel_id(channel: str, client: httpx.Client) -> str:
    """Resolve a channel ID or YouTube handle URL to a canonical channel ID."""

    try:
        return normalize_channel_id(channel)
    except YouTubeInputError:
        if not _is_handle_url(channel):
            raise

    response = client.get(channel.strip())
    response.raise_for_status()
    for pattern in _CHANNEL_ID_HTML_PATTERNS:
        match = pattern.search(response.text)
        if match:
            return match.group(1)
    raise YouTubeInputError(
        f"Could not find a canonical channel ID in YouTube handle URL {channel!r}."
    )


def channel_feed_url(channel: str) -> str:
    """Return the YouTube Atom feed URL for a channel."""

    return f"{YOUTUBE_FEED_URL}?channel_id={normalize_channel_id(channel)}"


def _entry_datetime(entry: Any) -> datetime:
    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if published:
        try:
            parsed = datetime.fromisoformat(published)
        except ValueError:
            parsed = parsedate_to_datetime(published)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    published_struct = getattr(entry, "published_parsed", None)
    if published_struct:
        return datetime(*published_struct[:6], tzinfo=UTC)
    raise ValueError("YouTube feed entry has no publication timestamp")


def _video_id(entry: Any) -> str:
    video_id = getattr(entry, "yt_videoid", None)
    if video_id:
        return str(video_id)

    link = str(getattr(entry, "link", ""))
    query_video_id = parse_qs(urlparse(link).query).get("v", [None])[0]
    if query_video_id:
        return query_video_id
    raise ValueError("YouTube feed entry has no video ID")


def _is_short(entry: Any) -> bool:
    links = getattr(entry, "links", [])
    urls = [str(getattr(link, "href", "")) for link in links]
    urls.append(str(getattr(entry, "link", "")))
    return any("/shorts/" in url.lower() for url in urls)


def parse_feed(
    feed_content: bytes | str,
    channel_id: str | None = None,
) -> list[ChannelVideo]:
    """Parse a YouTube Atom response into normalized video records."""

    del channel_id
    parsed = feedparser.parse(feed_content)
    videos: list[ChannelVideo] = []
    for entry in parsed.entries:
        if _is_short(entry):
            continue
        video_id = _video_id(entry)
        videos.append(
            ChannelVideo(
                title=str(getattr(entry, "title", "")).strip(),
                url=f"https://www.youtube.com/watch?v={video_id}",
                published_at=_entry_datetime(entry),
                description=str(getattr(entry, "summary", "")).strip(),
                video_id=video_id,
            )
        )
    return videos


def fetch_recent_videos(
    channels: Iterable[str],
    *,
    since: datetime,
    client: httpx.Client | None = None,
) -> list[ChannelVideo]:
    """Fetch videos published at or after ``since`` from each channel."""

    if since.tzinfo is None:
        raise ValueError("since must be timezone-aware")
    since_utc = since.astimezone(UTC)
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20.0, follow_redirects=True)
    try:
        videos: dict[str, ChannelVideo] = {}
        for channel in channels:
            channel_id = resolve_channel_id(channel, http_client)
            response = http_client.get(channel_feed_url(channel_id))
            response.raise_for_status()
            for video in parse_feed(response.content):
                if video.published_at >= since_utc:
                    videos[video.video_id] = video
        return sorted(
            videos.values(),
            key=lambda video: video.published_at,
            reverse=True,
        )
    finally:
        if owns_client:
            http_client.close()
