"""Enrich stored articles with page content and video transcripts."""

from __future__ import annotations

import logging

from app.database.repository import Repository
from app.scrapers.anthropic import AnthropicScraper
from app.scrapers.youtube import YouTubeScraper

logger = logging.getLogger(__name__)


def process_anthropic_content() -> dict[str, int]:
    """Extract Markdown for stored Anthropic articles missing content."""

    processed = 0
    failed = 0
    with Repository() as repository, AnthropicScraper() as scraper:
        articles = repository.get_articles_without_content("anthropic")
        for article in articles:
            try:
                content = scraper.url_to_markdown(article.url)
                if not content:
                    failed += 1
                    logger.warning("No content extracted for article %s", article.id)
                    continue
                repository.update_content(article, content)
                processed += 1
            except Exception:
                repository.session.rollback()
                failed += 1
                logger.exception("Failed to extract content for article %s", article.id)
    return {"total": len(articles), "processed": processed, "failed": failed}


def process_youtube_transcripts() -> dict[str, int]:
    """Fetch transcripts for stored YouTube videos missing transcripts."""

    processed = 0
    unavailable = 0
    failed = 0
    with Repository() as repository, YouTubeScraper() as scraper:
        articles = repository.get_articles_without_transcript()
        for article in articles:
            try:
                transcript = scraper.get_transcript(article.external_id)
                if not transcript:
                    unavailable += 1
                    logger.warning(
                        "No transcript available for video %s",
                        article.external_id,
                    )
                    continue
                repository.update_transcript(article, transcript)
                processed += 1
            except Exception:
                repository.session.rollback()
                failed += 1
                logger.exception(
                    "Failed to fetch transcript for video %s",
                    article.external_id,
                )
    return {
        "total": len(articles),
        "processed": processed,
        "unavailable": unavailable,
        "failed": failed,
    }


def enrich_articles() -> dict[str, dict[str, int]]:
    """Run both enrichment stages for stored articles."""

    return {
        "anthropic": process_anthropic_content(),
        "youtube": process_youtube_transcripts(),
    }
