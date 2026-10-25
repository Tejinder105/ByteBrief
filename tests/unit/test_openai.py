from datetime import UTC, datetime

import httpx
import pytest

from app.scrapers.openai import (
    OpenAIScraper,
    fetch_recent_articles,
    parse_feed,
    url_to_markdown,
)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenAI News</title>
    <item>
      <title><![CDATA[New API release]]></title>
      <description><![CDATA[Useful API improvements.]]></description>
      <link>https://openai.com/index/new-api-release</link>
      <guid isPermaLink="true">https://openai.com/index/new-api-release</guid>
      <category><![CDATA[Product]]></category>
      <pubDate>Sat, 25 Oct 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Older article</title>
      <description>Old description</description>
      <link>https://openai.com/index/older-article</link>
      <guid>https://openai.com/index/older-article</guid>
      <pubDate>Thu, 23 Oct 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


def test_parse_feed_extracts_openai_article_fields() -> None:
    articles = parse_feed(RSS)

    assert len(articles) == 2
    assert articles[0].title == "New API release"
    assert articles[0].description == "Useful API improvements."
    assert articles[0].url == "https://openai.com/index/new-api-release"
    assert articles[0].guid == articles[0].url
    assert articles[0].category == "Product"
    assert articles[0].published_at == datetime(2026, 10, 25, 10, tzinfo=UTC)


def test_fetch_recent_articles_filters_and_sorts_articles() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=RSS))
    since = datetime(2026, 10, 24, tzinfo=UTC)

    with httpx.Client(transport=transport) as client:
        articles = fetch_recent_articles(since=since, client=client)

    assert [article.title for article in articles] == ["New API release"]


def test_fetch_recent_articles_requires_timezone_aware_since() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        OpenAIScraper().fetch_recent_articles(since=datetime(2026, 10, 25))


def test_get_articles_uses_a_relative_time_window() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=RSS))

    with OpenAIScraper(client=httpx.Client(transport=transport)) as scraper:
        articles = scraper.get_articles(hours=24)

    assert [article.title for article in articles] == ["New API release"]


def test_url_to_markdown_extracts_article_content() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text="<html><article><h1>News</h1><p>Article content.</p></article></html>",
        )
    )

    with (
        httpx.Client(transport=transport) as client,
        pytest.MonkeyPatch.context() as monkeypatch,
    ):
        monkeypatch.setattr(
            "app.scrapers.openai.trafilatura.extract",
            lambda content, **kwargs: "# News\n\nArticle content.",
        )
        result = url_to_markdown("https://openai.com/index/news", client)

    assert result == "# News\n\nArticle content."


def test_url_to_markdown_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="url must not be empty"):
        url_to_markdown("  ")
