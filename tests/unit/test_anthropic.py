from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.scrapers.anthropic import AnthropicScraper, parse_feed

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Anthropic News</title>
    <item>
      <title><![CDATA[New safety research]]></title>
      <description><![CDATA[Research description.]]></description>
      <link>https://www.anthropic.com/research/new-safety-research</link>
      <guid>https://www.anthropic.com/research/new-safety-research</guid>
      <category><![CDATA[Research]]></category>
      <pubDate>Sat, 25 Oct 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def test_parse_feed_extracts_anthropic_article_fields() -> None:
    articles = parse_feed(RSS)

    assert len(articles) == 1
    assert articles[0].title == "New safety research"
    assert articles[0].category == "Research"
    assert articles[0].published_at == datetime(2026, 10, 25, 10, tzinfo=UTC)


def test_scraper_combines_feeds_and_deduplicates_articles() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=RSS)

    transport = httpx.MockTransport(handler)
    feed_urls = ("https://example.com/news.xml", "https://example.com/research.xml")
    with AnthropicScraper(
        client=httpx.Client(transport=transport),
        feed_urls=feed_urls,
    ) as scraper:
        articles = scraper.fetch_recent_articles(
            since=datetime(2026, 10, 24, tzinfo=UTC)
        )

    assert len(calls) == 2
    assert len(articles) == 1
    assert articles[0].title == "New safety research"


def test_scraper_requires_timezone_aware_since() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AnthropicScraper().fetch_recent_articles(since=datetime(2026, 10, 25))


def test_save_url_as_markdown_writes_file(tmp_path: Path) -> None:
    with (
        AnthropicScraper(
        ) as scraper,
        pytest.MonkeyPatch.context() as monkeypatch,
    ):
        class Document:
            def export_to_markdown(self) -> str:
                return "# Research"

        class Result:
            document = Document()

        class Converter:
            def convert(self, url: str) -> Result:
                return Result()

        monkeypatch.setattr(
            "docling.document_converter.DocumentConverter",
            Converter,
        )
        output_path = scraper.save_url_as_markdown(
            "https://www.anthropic.com/research/example",
            tmp_path / "article.md",
        )

    assert output_path.read_text(encoding="utf-8") == "# Research"
