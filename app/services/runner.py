"""Run all configured news scrapers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import DEFAULT_LOOKBACK_HOURS, YOUTUBE_CHANNELS
from app.database.repository import Repository
from app.models import ChannelVideo
from app.scrapers.anthropic import AnthropicArticle, AnthropicScraper
from app.scrapers.openai import OpenAIArticle, OpenAIScraper
from app.scrapers.youtube import YouTubeScraper
from app.services.enrich import enrich_articles


def run_scrapers(
    hours: float = DEFAULT_LOOKBACK_HOURS,
) -> dict[str, list[ChannelVideo | OpenAIArticle | AnthropicArticle]]:
    """Fetch recent content from YouTube, OpenAI, and Anthropic."""

    if hours < 0:
        raise ValueError("hours must not be negative")
    since = datetime.now(UTC) - timedelta(hours=hours)

    with (
        Repository() as repository,
        YouTubeScraper() as youtube,
        OpenAIScraper() as openai,
        AnthropicScraper() as anthropic,
    ):
        youtube_videos = youtube.fetch_recent_videos_with_transcripts(
            YOUTUBE_CHANNELS,
            since=since,
        )
        openai_articles = openai.fetch_recent_articles(since=since)
        anthropic_articles = anthropic.fetch_recent_articles(since=since)

        repository.save_youtube_videos(youtube_videos)
        repository.save_openai_articles(openai_articles)
        repository.save_anthropic_articles(anthropic_articles)

        return {
            "youtube": youtube_videos,
            "openai": openai_articles,
            "anthropic": anthropic_articles,
        }


def run_pipeline(
    hours: float = DEFAULT_LOOKBACK_HOURS,
) -> dict[str, object]:
    """Run ingestion followed by content and transcript enrichment."""

    scraped = run_scrapers(hours=hours)
    return {
        "scraped": scraped,
        "enriched": enrich_articles(),
    }
