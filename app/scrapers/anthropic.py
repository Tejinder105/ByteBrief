"""Anthropic News RSS scraper."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Self

import feedparser
import httpx

from app.models import AnthropicArticle

ANTHROPIC_NEWS_RSS_URLS = (
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml",
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
)


def _entry_datetime(entry: Any) -> datetime:
    published = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if not published:
        raise ValueError("Anthropic RSS entry has no publication timestamp")
    return datetime(*published[:6], tzinfo=UTC)


def _entry_category(entry: Any) -> str | None:
    tags = entry.get("tags", [])
    if not tags:
        return None
    category = tags[0].get("term")
    return str(category).strip() or None if category else None


def parse_feed(feed_content: bytes | str) -> list[AnthropicArticle]:
    """Parse one Anthropic RSS feed into normalized article records."""

    parsed = feedparser.parse(feed_content)
    articles: list[AnthropicArticle] = []
    for entry in parsed.entries:
        url = str(entry.get("link", "")).strip()
        guid = str(entry.get("id", "")).strip() or url
        if not url:
            raise ValueError("Anthropic RSS entry has no article URL")
        if not guid:
            raise ValueError("Anthropic RSS entry has no article identifier")

        articles.append(
            AnthropicArticle(
                title=str(entry.get("title", "")).strip(),
                description=str(entry.get("description", "")).strip(),
                url=url,
                guid=guid,
                published_at=_entry_datetime(entry),
                category=_entry_category(entry),
            )
        )
    return articles


class AnthropicScraper:
    """Fetch recent articles from all configured Anthropic RSS feeds."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        feed_urls: Sequence[str] = ANTHROPIC_NEWS_RSS_URLS,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._feed_urls = tuple(feed_urls)

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

    def fetch_recent_articles(self, *, since: datetime) -> list[AnthropicArticle]:
        """Fetch articles from all feeds published at or after ``since``."""

        if since.tzinfo is None:
            raise ValueError("since must be timezone-aware")
        since_utc = since.astimezone(UTC)
        articles: dict[str, AnthropicArticle] = {}

        for feed_url in self._feed_urls:
            response = self._http_client().get(feed_url)
            response.raise_for_status()
            for article in parse_feed(response.content):
                if article.published_at >= since_utc:
                    articles[article.guid] = article

        return sorted(
            articles.values(),
            key=lambda article: article.published_at,
            reverse=True,
        )

    def get_articles(self, hours: int = 24) -> list[AnthropicArticle]:
        """Return Anthropic articles published within the last ``hours`` hours."""

        if hours < 0:
            raise ValueError("hours must not be negative")
        return self.fetch_recent_articles(
            since=datetime.now(UTC) - timedelta(hours=hours)
        )

    def url_to_markdown(self, url: str) -> str | None:
        """Fetch an article URL and extract its main content as Markdown."""

        if not url.strip():
            raise ValueError("url must not be empty")

        from docling.document_converter import DocumentConverter

        result = DocumentConverter().convert(url.strip())
        return result.document.export_to_markdown()

    def save_url_as_markdown(self, url: str, output_path: str | Path) -> Path:
        """Fetch an article URL and save its extracted content as a Markdown file."""

        markdown = self.url_to_markdown(url)
        if not markdown:
            raise ValueError(f"Could not extract Markdown content from {url!r}")

        path = Path(output_path)
        path.write_text(markdown, encoding="utf-8")
        return path


def fetch_recent_articles(
    *,
    since: datetime,
    client: httpx.Client | None = None,
) -> list[AnthropicArticle]:
    """Fetch recent articles from all Anthropic RSS feeds."""

    with AnthropicScraper(client=client) as scraper:
        return scraper.fetch_recent_articles(since=since)


def url_to_markdown(
    url: str,
    client: httpx.Client | None = None,
) -> str | None:
    """Fetch an Anthropic article URL and extract its content as Markdown."""

    with AnthropicScraper(client=client) as scraper:
        return scraper.url_to_markdown(url)


def save_url_as_markdown(
    url: str,
    output_path: str | Path,
    client: httpx.Client | None = None,
) -> Path:
    """Fetch an Anthropic article URL and save it as a Markdown file."""

    with AnthropicScraper(client=client) as scraper:
        return scraper.save_url_as_markdown(url, output_path)


__all__ = [
    "ANTHROPIC_NEWS_RSS_URLS",
    "AnthropicScraper",
    "fetch_recent_articles",
    "parse_feed",
    "save_url_as_markdown",
    "url_to_markdown",
]
