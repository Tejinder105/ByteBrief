"""OpenAI News RSS scraper."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Self

import feedparser
import httpx
import trafilatura

from app.models import OpenAIArticle

OPENAI_NEWS_RSS_URL = "https://openai.com/news/rss.xml"


def _entry_datetime(entry: Any) -> datetime:
    published = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if not published:
        raise ValueError("OpenAI RSS entry has no publication timestamp")
    return datetime(*published[:6], tzinfo=UTC)


def _entry_category(entry: Any) -> str | None:
    tags = entry.get("tags", [])
    if not tags:
        return None
    category = tags[0].get("term")
    return str(category).strip() or None if category else None


def parse_feed(feed_content: bytes | str) -> list[OpenAIArticle]:
    """Parse OpenAI News RSS content into normalized article records."""

    parsed = feedparser.parse(feed_content)
    articles: list[OpenAIArticle] = []
    for entry in parsed.entries:
        url = str(entry.get("link", "")).strip()
        guid = str(entry.get("id", "")).strip() or url
        if not url:
            raise ValueError("OpenAI RSS entry has no article URL")
        if not guid:
            raise ValueError("OpenAI RSS entry has no article identifier")

        articles.append(
            OpenAIArticle(
                title=str(entry.get("title", "")).strip(),
                description=str(entry.get("description", "")).strip(),
                url=url,
                guid=guid,
                published_at=_entry_datetime(entry),
                category=_entry_category(entry),
            )
        )
    return articles


class OpenAIScraper:
    """Fetch recent articles from the OpenAI News RSS feed."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        feed_url: str = OPENAI_NEWS_RSS_URL,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._feed_url = feed_url

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

    def fetch_recent_articles(self, *, since: datetime) -> list[OpenAIArticle]:
        """Fetch OpenAI articles published at or after ``since``."""

        if since.tzinfo is None:
            raise ValueError("since must be timezone-aware")
        since_utc = since.astimezone(UTC)
        response = self._http_client().get(self._feed_url)
        response.raise_for_status()

        articles: dict[str, OpenAIArticle] = {}
        for article in parse_feed(response.content):
            if article.published_at >= since_utc:
                articles[article.guid] = article
        return sorted(
            articles.values(),
            key=lambda article: article.published_at,
            reverse=True,
        )

    def get_articles(self, hours: int = 24) -> list[OpenAIArticle]:
        """Return OpenAI articles published within the last ``hours`` hours."""

        if hours < 0:
            raise ValueError("hours must not be negative")
        return self.fetch_recent_articles(
            since=datetime.now(UTC) - timedelta(hours=hours)
        )

    def url_to_markdown(self, url: str) -> str | None:
        """Fetch an article URL and extract its main content as Markdown."""

        if not url.strip():
            raise ValueError("url must not be empty")

        response = self._http_client().get(
            url.strip(),
            headers={"User-Agent": "ByteBrief/0.1"},
        )
        response.raise_for_status()
        return trafilatura.extract(
            response.text,
            output_format="markdown",
            include_comments=False,
            include_tables=True,
        )


def fetch_recent_articles(
    *,
    since: datetime,
    client: httpx.Client | None = None,
) -> list[OpenAIArticle]:
    """Fetch recent OpenAI News articles."""

    with OpenAIScraper(client=client) as scraper:
        return scraper.fetch_recent_articles(since=since)


def url_to_markdown(
    url: str,
    client: httpx.Client | None = None,
) -> str | None:
    """Fetch an article URL and extract its main content as Markdown."""

    with OpenAIScraper(client=client) as scraper:
        return scraper.url_to_markdown(url)


__all__ = [
    "OPENAI_NEWS_RSS_URL",
    "OpenAIScraper",
    "fetch_recent_articles",
    "parse_feed",
    "url_to_markdown",
]
